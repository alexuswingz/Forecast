"""
Generate and persist weekly forecast metrics for all ASINs
"""
import argparse
from datetime import datetime
from pathlib import Path
import sys

import pandas as pd
from sqlalchemy import create_engine, text

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from config import Config
from forecasting.generate_forecast import ForecastGenerator


def get_engine():
    if Config.USE_SQLITE:
        return create_engine(f"sqlite:///{Config.SQLITE_DB_PATH}")
    return create_engine(Config.DATABASE_URL)


def safe_number(value):
    if value is None:
        return None
    if isinstance(value, float) and (value != value):  # NaN
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    try:
        import math
        if math.isnan(value):
            return None
    except Exception:
        pass
    return float(value)


def to_date(value):
    if value is None:
        return None
    if isinstance(value, pd.Timestamp):
        return value.date()
    return value


def persist_forecast(asin, generator, engine):
    hist = generator.historical_df.copy()
    forecast = generator.forecast_df.copy()
    velocity = generator.velocity_adjustments or {}
    timestamp = datetime.utcnow()
    
    records = []
    
    for _, row in hist.iterrows():
        records.append({
            'asin': asin,
            'week_end': to_date(row['week_end']),
            'units_sold': safe_number(row.get('units_sold')),
            'units_peak_env': safe_number(row.get('units_peak_env')),
            'units_smooth_env': safe_number(row.get('units_smooth_env')),
            'units_final_curve': safe_number(row.get('units_final_curve')),
            'units_final_smooth': safe_number(row.get('units_final_smooth')),
            'forecast_baseline': safe_number(row.get('forecast_baseline')),
            'forecast_peak_env': safe_number(row.get('forecast_peak_env')),
            'forecast_final_smooth': safe_number(row.get('forecast_final_smooth')),
            'forecast_base': None,
            'forecast_adjusted': None,
            'is_forecast': False,
            'created_at': timestamp,
            'updated_at': timestamp
        })
    
    for _, row in forecast.iterrows():
        records.append({
            'asin': asin,
            'week_end': to_date(row['week_end']),
            'units_sold': None,
            'units_peak_env': None,
            'units_smooth_env': None,
            'units_final_curve': None,
            'units_final_smooth': None,
            'forecast_baseline': None,
            'forecast_peak_env': None,
            'forecast_final_smooth': None,
            'forecast_base': safe_number(row.get('forecast_base')),
            'forecast_adjusted': safe_number(row.get('forecast_adjusted')),
            'is_forecast': True,
            'created_at': timestamp,
            'updated_at': timestamp
        })
    
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM weekly_forecast_metrics WHERE asin = :asin"), {'asin': asin})
        if records:
            insert_sql = text("""
                INSERT INTO weekly_forecast_metrics (
                    asin, week_end, units_sold, units_peak_env, units_smooth_env,
                    units_final_curve, units_final_smooth, forecast_baseline,
                    forecast_peak_env, forecast_final_smooth, forecast_base,
                    forecast_adjusted, is_forecast, created_at, updated_at
                )
                VALUES (
                    :asin, :week_end, :units_sold, :units_peak_env, :units_smooth_env,
                    :units_final_curve, :units_final_smooth, :forecast_baseline,
                    :forecast_peak_env, :forecast_final_smooth, :forecast_base,
                    :forecast_adjusted, :is_forecast, :created_at, :updated_at
                )
            """)
            conn.execute(insert_sql, records)
        
        summary_sql = text("""
            INSERT INTO forecast_summaries (
                asin, sales_velocity_adj, sv_velocity_adj,
                sales_velocity_weighted, sv_velocity_weighted,
                total_adjustment, forecast_weeks, generated_at
            )
            VALUES (
                :asin, :sales_velocity_adj, :sv_velocity_adj,
                :sales_velocity_weighted, :sv_velocity_weighted,
                :total_adjustment, :forecast_weeks, :generated_at
            )
            ON CONFLICT (asin) DO UPDATE SET
                sales_velocity_adj = EXCLUDED.sales_velocity_adj,
                sv_velocity_adj = EXCLUDED.sv_velocity_adj,
                sales_velocity_weighted = EXCLUDED.sales_velocity_weighted,
                sv_velocity_weighted = EXCLUDED.sv_velocity_weighted,
                total_adjustment = EXCLUDED.total_adjustment,
                forecast_weeks = EXCLUDED.forecast_weeks,
                generated_at = EXCLUDED.generated_at
        """)
        conn.execute(summary_sql, {
            'asin': asin,
            'sales_velocity_adj': safe_number(velocity.get('sales_velocity_adj')),
            'sv_velocity_adj': safe_number(velocity.get('sv_velocity_adj')),
            'sales_velocity_weighted': safe_number(velocity.get('sales_velocity_weighted')),
            'sv_velocity_weighted': safe_number(velocity.get('sv_velocity_weighted')),
            'total_adjustment': safe_number(velocity.get('total_adjustment')),
            'forecast_weeks': generator.settings.forecast_weeks_ahead,
            'generated_at': timestamp
        })


def get_target_asins(engine, asin=None, limit=None):
    if asin:
        return [asin]
    
    query = """
        SELECT asin
        FROM (
            SELECT asin, COUNT(*) as order_count
            FROM order_items
            WHERE asin IS NOT NULL
            GROUP BY asin
            HAVING COUNT(*) > 0
            ORDER BY order_count DESC
        ) ordered
    """
    
    with engine.connect() as conn:
        rows = conn.execute(text(query)).fetchall()
    
    asins = [row[0] for row in rows if row[0]]
    if limit:
        asins = asins[:limit]
    return asins


def main():
    parser = argparse.ArgumentParser(description="Update weekly forecast metrics")
    parser.add_argument('--asin', help='Process a single ASIN')
    parser.add_argument('--limit', type=int, help='Limit number of ASINs when running for all')
    parser.add_argument('--start-date', help='Optional start date (YYYY-MM-DD)')
    parser.add_argument('--skip-errors', action='store_true', help='Skip ASINs that fail')
    parser.add_argument('--no-export', action='store_true', help='Do not export CSV files')
    args = parser.parse_args()
    
    engine = get_engine()
    asins = get_target_asins(engine, asin=args.asin, limit=args.limit)
    
    if not asins:
        print("No ASINs found to process")
        return
    
    print(f"Processing {len(asins)} ASIN(s)")
    
    for asin in asins:
        print("\n" + "-" * 80)
        print(f"Forecasting ASIN: {asin}")
        print("-" * 80)
        try:
            generator = ForecastGenerator(asin=asin)
            generator.generate(start_date=args.start_date, export_csv=not args.no_export)
            persist_forecast(asin, generator, engine)
            print(f"[OK] Stored forecast metrics for {asin}")
        except Exception as exc:
            print(f"[ERROR] Failed to process {asin}: {exc}")
            if not args.skip_errors:
                raise


if __name__ == '__main__':
    main()


