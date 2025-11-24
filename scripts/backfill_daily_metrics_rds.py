"""
Backfill daily_product_metrics table on RDS with historical data
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, text
from config import Config

def backfill_metrics_rds():
    """Backfill historical daily metrics on RDS"""
    
    print("=" * 80)
    print("Backfilling Daily Product Metrics on RDS")
    print("=" * 80)
    
    # Force RDS connection
    rds_url = f"postgresql://{Config.DB_USER}:{Config.DB_PASSWORD}@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}"
    
    print(f"\nConnecting to RDS: {Config.DB_HOST}")
    engine = create_engine(rds_url)
    
    with engine.connect() as conn:
        # Get date range from data
        print("\nFinding date range...")
        result = conn.execute(text("""
            SELECT 
                MIN(order_date::timestamp::date) as min_date,
                MAX(order_date::timestamp::date) as max_date
            FROM order_items
        """))
        row = result.fetchone()
        min_date = row[0]
        max_date = row[1]
        
        print(f"  From: {min_date}")
        print(f"  To: {max_date}")
        
        days = (max_date - min_date).days + 1
        print(f"  Total days: {days:,}")
        
        print("\nAggregating daily metrics...")
        print("This will take several minutes (3-10 min typical)...\n")
        
        # Insert aggregated data
        insert_sql = """
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
        
        print("Executing aggregation query...")
        conn.execute(text(insert_sql))
        conn.commit()
        print("[OK] Data inserted")
        
        # Get row count
        result = conn.execute(text("SELECT COUNT(*) FROM daily_product_metrics"))
        total_rows = result.fetchone()[0]
        
        # Get unique ASINs
        result = conn.execute(text("SELECT COUNT(DISTINCT asin) FROM daily_product_metrics"))
        unique_asins = result.fetchone()[0]
        
        # Get sample data
        result = conn.execute(text("""
            SELECT asin, date, units_sold, sales_amount, sessions, ad_spend
            FROM daily_product_metrics
            WHERE units_sold > 0
            ORDER BY date DESC
            LIMIT 5
        """))
        
        print("\n" + "=" * 80)
        print("BACKFILL COMPLETE!")
        print("=" * 80)
        print(f"\nTotal rows inserted: {total_rows:,}")
        print(f"Unique ASINs: {unique_asins:,}")
        print(f"Date range: {min_date} to {max_date}")
        
        print("\nSample data (recent days with sales):")
        print("=" * 80)
        for row in result:
            print(f"  {row[0]} | {row[1]} | Units: {row[2]:,} | Sales: ${row[3]:,.2f} | Sessions: {row[4]:,} | Ad: ${row[5]:,.2f}")
        
        print("\n" + "=" * 80)
        print("Next steps:")
        print("  1. Deploy updated Lambda (forecast-lambda.zip)")
        print("  2. Test: GET /metrics/B0BRTK1P8Z?days=30")
        print("  3. Expected response time: 0.5-2 seconds!")
        print("=" * 80)
        print()

if __name__ == '__main__':
    backfill_metrics_rds()

