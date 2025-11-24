"""
Create pre-aggregated forecast tables for Lambda
"""
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, text
from config import Config


def create_tables():
    print("=" * 80)
    print("Creating weekly_forecast_metrics & forecast_summaries")
    print("=" * 80)
    
    engine = create_engine(Config.DATABASE_URL if not Config.USE_SQLITE else f"sqlite:///{Config.SQLITE_DB_PATH}")
    is_postgres = 'postgresql' in (Config.DATABASE_URL.lower() if Config.DATABASE_URL else '')
    
    with engine.begin() as conn:
        print("Dropping existing tables (if any)...")
        conn.execute(text("DROP TABLE IF EXISTS weekly_forecast_metrics"))
        conn.execute(text("DROP TABLE IF EXISTS forecast_summaries"))
    
    print("[OK] Old tables removed")
    
    if is_postgres:
        create_sql = """
        CREATE TABLE weekly_forecast_metrics (
            id SERIAL PRIMARY KEY,
            asin VARCHAR(20) NOT NULL,
            week_end DATE NOT NULL,
            units_sold NUMERIC(14,4),
            units_peak_env NUMERIC(14,4),
            units_smooth_env NUMERIC(14,4),
            units_final_curve NUMERIC(14,4),
            units_final_smooth NUMERIC(14,4),
            forecast_baseline NUMERIC(14,4),
            forecast_peak_env NUMERIC(14,4),
            forecast_final_smooth NUMERIC(14,4),
            forecast_base NUMERIC(14,4),
            forecast_adjusted NUMERIC(14,4),
            is_forecast BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(asin, week_end)
        );
        CREATE INDEX idx_weekly_forecast_asin ON weekly_forecast_metrics(asin);
        CREATE INDEX idx_weekly_forecast_is_forecast ON weekly_forecast_metrics(asin, is_forecast);
        
        CREATE TABLE forecast_summaries (
            asin VARCHAR(20) PRIMARY KEY,
            sales_velocity_adj NUMERIC(14,6),
            sv_velocity_adj NUMERIC(14,6),
            sales_velocity_weighted NUMERIC(14,6),
            sv_velocity_weighted NUMERIC(14,6),
            total_adjustment NUMERIC(14,6),
            forecast_weeks INTEGER,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    else:
        create_sql = """
        CREATE TABLE weekly_forecast_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asin TEXT NOT NULL,
            week_end TEXT NOT NULL,
            units_sold REAL,
            units_peak_env REAL,
            units_smooth_env REAL,
            units_final_curve REAL,
            units_final_smooth REAL,
            forecast_baseline REAL,
            forecast_peak_env REAL,
            forecast_final_smooth REAL,
            forecast_base REAL,
            forecast_adjusted REAL,
            is_forecast INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(asin, week_end)
        );
        CREATE INDEX idx_weekly_forecast_asin ON weekly_forecast_metrics(asin);
        CREATE INDEX idx_weekly_forecast_is_forecast ON weekly_forecast_metrics(asin, is_forecast);
        
        CREATE TABLE forecast_summaries (
            asin TEXT PRIMARY KEY,
            sales_velocity_adj REAL,
            sv_velocity_adj REAL,
            sales_velocity_weighted REAL,
            sv_velocity_weighted REAL,
            total_adjustment REAL,
            forecast_weeks INTEGER,
            generated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
    
    with engine.begin() as conn:
        for statement in [s.strip() for s in create_sql.strip().split(';') if s.strip()]:
            conn.execute(text(statement))
    
    print("[OK] Tables created and indexed")
    print("\nNext steps:")
    print("  1. Run: python scripts/update_weekly_forecast_metrics.py --asin B0XXXXX (or without --asin for all)")
    print("  2. Deploy Lambda after data is populated")
    print("=" * 80)


if __name__ == '__main__':
    create_tables()


