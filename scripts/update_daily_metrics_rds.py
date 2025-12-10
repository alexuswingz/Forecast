"""
Update daily_product_metrics table in PostgreSQL RDS
Aggregates data from order_items, child_traffic_metrics, and ad_product_performance
"""
import psycopg2
from psycopg2.extras import execute_values
from datetime import date, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

def update_daily_metrics(days_back=30):
    """
    Update daily metrics for the last N days
    """
    print("=" * 80)
    print(f"UPDATING DAILY PRODUCT METRICS (Last {days_back} Days)")
    print("=" * 80)
    
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        port=int(os.getenv('DB_PORT', 5432))
    )
    
    start_date = date.today() - timedelta(days=days_back)
    end_date = date.today()
    
    print(f"\nUpdate period: {start_date} to {end_date}")
    
    cur = conn.cursor()
    
    # Upsert SQL for PostgreSQL
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
                order_date::date as date,
                SUM(quantity) as units_sold,
                SUM(item_price * quantity) as sales_amount,
                COUNT(DISTINCT order_id) as orders_count
            FROM order_items
            WHERE asin IS NOT NULL
            AND order_date::date BETWEEN %s AND %s
            GROUP BY asin, order_date::date
        ),
        traffic_daily AS (
            SELECT 
                child_asin as asin,
                date,
                SUM(sessions) as sessions,
                SUM(page_views) as page_views,
                AVG(conversion_rate) as conversion_rate,
                SUM(units_ordered) as units_ordered,
                SUM(ordered_product_sales) as ordered_product_sales
            FROM child_traffic_metrics
            WHERE child_asin IS NOT NULL
            AND date BETWEEN %s AND %s
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
            AND report_date BETWEEN %s AND %s
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
            COALESCE(s.units_sold, t.units_ordered, 0),
            COALESCE(s.sales_amount, t.ordered_product_sales, 0),
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
    
    print("\nAggregating data from:")
    print("  - order_items (sales data)")
    print("  - child_traffic_metrics (sessions, conversion)")
    print("  - ad_product_performance (ad data)")
    print("\nInserting into daily_product_metrics...")
    
    try:
        cur.execute(upsert_sql, (
            start_date, end_date,
            start_date, end_date,
            start_date, end_date
        ))
        
        rows_affected = cur.rowcount
        conn.commit()
        
        print(f"\n[SUCCESS] Updated {rows_affected} daily metric records")
        
        # Get summary
        cur.execute("""
            SELECT 
                COUNT(DISTINCT asin) as asins,
                COUNT(*) as total_rows,
                MIN(date) as earliest,
                MAX(date) as latest
            FROM daily_product_metrics
        """)
        
        summary = cur.fetchone()
        print(f"\nDaily Metrics Summary:")
        print(f"  Total ASINs: {summary[0]}")
        print(f"  Total rows: {summary[1]:,}")
        print(f"  Date range: {summary[2]} to {summary[3]}")
        
        # Check latest dates
        cur.execute("""
            SELECT date, COUNT(DISTINCT asin) as asins
            FROM daily_product_metrics
            WHERE date >= %s
            ORDER BY date DESC
            LIMIT 10
        """, (date.today() - timedelta(days=10),))
        
        print(f"\nLast 10 days:")
        for row in cur.fetchall():
            print(f"  {row[0]}: {row[1]} ASINs")
            
    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] Failed to update metrics: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    import sys
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    update_daily_metrics(days)

