"""
Daily update script for daily_product_metrics table
Run this as a daily cron job after importing fresh data
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, text
from config import Config
from datetime import date, timedelta

def update_daily_metrics(days_back=7):
    """
    Update daily metrics for the last N days
    
    Args:
        days_back: Number of days to update (default: 7 to catch any late data)
    """
    
    print("=" * 80)
    print(f"Updating Daily Product Metrics (Last {days_back} Days)")
    print("=" * 80)
    
    engine = create_engine(Config.DATABASE_URL)
    
    start_date = date.today() - timedelta(days=days_back)
    end_date = date.today()
    
    print(f"\nUpdate period: {start_date} to {end_date}")
    
    with engine.connect() as conn:
        # Upsert recent data
        upsert_sql = """
        INSERT INTO daily_product_metrics (
            asin, date,
            units_sold, sales_amount, orders_count,
            sessions, page_views, conversion_rate,
            ad_spend, ad_sales, ad_clicks, ad_impressions, ad_orders
        )
        WITH sales_daily AS (
            SELECT 
                asin,
                DATE(order_date::timestamp) as date,
                SUM(quantity) as units_sold,
                SUM(item_price * quantity) as sales_amount,
                COUNT(DISTINCT order_id) as orders_count
            FROM order_items
            WHERE asin IS NOT NULL
            AND DATE(order_date::timestamp) BETWEEN :start_date AND :end_date
            GROUP BY asin, DATE(order_date::timestamp)
        ),
        traffic_daily AS (
            SELECT 
                child_asin as asin,
                date,
                SUM(sessions) as sessions,
                SUM(page_views) as page_views,
                AVG(conversion_rate) as conversion_rate
            FROM child_traffic_metrics
            WHERE child_asin IS NOT NULL
            AND date BETWEEN :start_date AND :end_date
            GROUP BY child_asin, date
        ),
        ads_daily AS (
            SELECT 
                advertised_asin as asin,
                report_date as date,
                SUM(spend) as ad_spend,
                SUM(sales_14d) as ad_sales,
                SUM(clicks) as ad_clicks,
                SUM(impressions) as ad_impressions,
                SUM(orders_14d) as ad_orders
            FROM ad_product_performance
            WHERE advertised_asin IS NOT NULL
            AND report_date BETWEEN :start_date AND :end_date
            GROUP BY advertised_asin, report_date
        ),
        all_dates AS (
            SELECT DISTINCT asin, date FROM sales_daily WHERE date IS NOT NULL
            UNION
            SELECT DISTINCT asin, date FROM traffic_daily WHERE date IS NOT NULL
            UNION
            SELECT DISTINCT asin, date FROM ads_daily WHERE date IS NOT NULL
        )
        SELECT 
            d.asin,
            d.date,
            COALESCE(s.units_sold, 0),
            COALESCE(s.sales_amount, 0),
            COALESCE(s.orders_count, 0),
            COALESCE(t.sessions, 0),
            COALESCE(t.page_views, 0),
            COALESCE(t.conversion_rate, 0),
            COALESCE(a.ad_spend, 0),
            COALESCE(a.ad_sales, 0),
            COALESCE(a.ad_clicks, 0),
            COALESCE(a.ad_impressions, 0),
            COALESCE(a.ad_orders, 0)
        FROM all_dates d
        LEFT JOIN sales_daily s ON s.asin = d.asin AND s.date = d.date
        LEFT JOIN traffic_daily t ON t.asin = d.asin AND t.date = d.date
        LEFT JOIN ads_daily a ON a.asin = d.asin AND a.date = d.date
        ON CONFLICT (asin, date) DO UPDATE SET
            units_sold = EXCLUDED.units_sold,
            sales_amount = EXCLUDED.sales_amount,
            orders_count = EXCLUDED.orders_count,
            sessions = EXCLUDED.sessions,
            page_views = EXCLUDED.page_views,
            conversion_rate = EXCLUDED.conversion_rate,
            ad_spend = EXCLUDED.ad_spend,
            ad_sales = EXCLUDED.ad_sales,
            ad_clicks = EXCLUDED.ad_clicks,
            ad_impressions = EXCLUDED.ad_impressions,
            ad_orders = EXCLUDED.ad_orders,
            updated_at = CURRENT_TIMESTAMP
        """
        
        conn.execute(text(upsert_sql), {'start_date': start_date, 'end_date': end_date})
        conn.commit()
        
        # Get update stats
        result = conn.execute(text("""
            SELECT 
                COUNT(*) as total_rows,
                COUNT(DISTINCT asin) as unique_asins,
                SUM(units_sold) as total_units,
                SUM(sales_amount) as total_sales
            FROM daily_product_metrics
            WHERE date BETWEEN :start_date AND :end_date
        """), {'start_date': start_date, 'end_date': end_date})
        
        stats = result.fetchone()
        
        print("\n" + "=" * 80)
        print("UPDATE COMPLETE!")
        print("=" * 80)
        print(f"\nRows updated: {stats[0]:,}")
        print(f"Unique ASINs: {stats[1]:,}")
        print(f"Total units (period): {stats[2]:,}")
        print(f"Total sales (period): ${stats[3]:,.2f}")
        print("\n" + "=" * 80)
        print()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=7, help='Number of days to update (default: 7)')
    args = parser.parse_args()
    
    update_daily_metrics(args.days)

