"""
Import child traffic metrics from SP-API directly to PostgreSQL RDS
"""
import psycopg2
from psycopg2.extras import execute_values
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from integrations.amazon_sp_api import AmazonSPAPIClient

load_dotenv()

def safe_float(value):
    if value in (None, "", "-", "NaN"):
        return None
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None

def import_traffic_data(start_date_str, end_date_str):
    """Import traffic data from SP-API to RDS"""
    
    print("=" * 80)
    print("IMPORTING CHILD TRAFFIC METRICS FROM SP-API TO RDS")
    print("=" * 80)
    
    # Connect to PostgreSQL RDS
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        port=int(os.getenv('DB_PORT', 5432))
    )
    
    # Initialize SP-API client
    client = AmazonSPAPIClient()
    
    start_date = datetime.fromisoformat(start_date_str).date()
    end_date = datetime.fromisoformat(end_date_str).date()
    
    print(f"\nFetching data from {start_date} to {end_date}")
    print(f"This will import day-by-day from Amazon SP-API...")
    print()
    
    current_date = start_date
    total_imported = 0
    
    while current_date <= end_date:
        print(f"Processing {current_date}...")
        
        try:
            # Fetch data from SP-API
            rows, _ = client.fetch_child_traffic_metrics(
                current_date.isoformat(),
                current_date.isoformat()
            )
            
            if not rows:
                print(f"  [WARN] No data returned for {current_date}")
                current_date += timedelta(days=1)
                continue
            
            # Prepare records for insertion
            records = []
            for row in rows:
                child_asin = row.get("childAsin") or row.get("child-asin") or row.get("asin")
                if not child_asin:
                    continue
                
                sku = row.get("sku") or row.get("sellerSku") or row.get("merchantSku") or child_asin
                parent_asin = row.get("parentAsin") or row.get("parent-asin")
                
                record = (
                    current_date,
                    child_asin,
                    sku,
                    parent_asin,
                    safe_float(row.get("sessions")),
                    safe_float(row.get("sessionPercentage")),
                    safe_float(row.get("pageViews")),
                    safe_float(row.get("pageViewsPercentage")),
                    safe_float(row.get("buyBoxPercentage")),
                    safe_float(row.get("unitsOrdered")),
                    safe_float(row.get("unitsOrderedB2B")),
                    safe_float(row.get("orderedProductSales")),
                    safe_float(row.get("orderedProductSalesB2B")),
                    safe_float(row.get("totalOrderItems")),
                    safe_float(row.get("unitSessionPercentage"))
                )
                records.append(record)
            
            # Bulk insert with UPSERT
            cur = conn.cursor()
            
            insert_sql = """
                INSERT INTO child_traffic_metrics (
                    date, child_asin, sku, parent_asin,
                    sessions, session_percentage, page_views, page_views_percentage,
                    buy_box_percentage, units_ordered, units_ordered_b2b,
                    ordered_product_sales, ordered_product_sales_b2b,
                    total_order_items, conversion_rate
                ) VALUES %s
                ON CONFLICT (date, child_asin, sku) DO UPDATE SET
                    parent_asin = EXCLUDED.parent_asin,
                    sessions = EXCLUDED.sessions,
                    session_percentage = EXCLUDED.session_percentage,
                    page_views = EXCLUDED.page_views,
                    page_views_percentage = EXCLUDED.page_views_percentage,
                    buy_box_percentage = EXCLUDED.buy_box_percentage,
                    units_ordered = EXCLUDED.units_ordered,
                    units_ordered_b2b = EXCLUDED.units_ordered_b2b,
                    ordered_product_sales = EXCLUDED.ordered_product_sales,
                    ordered_product_sales_b2b = EXCLUDED.ordered_product_sales_b2b,
                    total_order_items = EXCLUDED.total_order_items,
                    conversion_rate = EXCLUDED.conversion_rate,
                    updated_at = CURRENT_TIMESTAMP
            """
            
            execute_values(cur, insert_sql, records)
            conn.commit()
            cur.close()
            
            print(f"  [OK] Imported {len(records)} rows")
            total_imported += len(records)
            
        except Exception as e:
            print(f"  [ERROR] Failed: {e}")
            conn.rollback()
        
        current_date += timedelta(days=1)
    
    conn.close()
    
    print()
    print("=" * 80)
    print(f"[SUCCESS] Total imported: {total_imported} rows")
    print("=" * 80)
    return total_imported

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python import_traffic_from_sp_api_to_rds.py START_DATE END_DATE")
        print("Example: python import_traffic_from_sp_api_to_rds.py 2025-11-15 2025-11-28")
        sys.exit(1)
    
    start = sys.argv[1]
    end = sys.argv[2]
    import_traffic_data(start, end)







