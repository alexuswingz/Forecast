"""
Fast migration from SQLite to PostgreSQL RDS using temp table approach
"""
import sqlite3
import psycopg2
from psycopg2.extras import execute_values
import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 80)
print("MIGRATING DATA FROM SQLITE TO RDS (FAST MODE)")
print("=" * 80)

# Connect to databases
sqlite_conn = sqlite3.connect('kpi_metrics.db')
sqlite_cur = sqlite_conn.cursor()

pg_conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    database=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    port=int(os.getenv('DB_PORT', 5432))
)
pg_cur = pg_conn.cursor()

print(f"\n✅ Connected to both databases")

# Fetch all records from SQLite
print(f"\nFetching data from SQLite (Nov 15-28)...")
sqlite_cur.execute("""
    SELECT 
        date, child_asin, sku, parent_asin,
        sessions, session_percentage, page_views, page_views_percentage,
        buy_box_percentage, units_ordered, units_ordered_b2b,
        ordered_product_sales, ordered_product_sales_b2b,
        total_order_items, conversion_rate
    FROM child_traffic_metrics
    WHERE date >= '2025-11-15' AND date <= '2025-11-28'
    ORDER BY date, child_asin
""")

records = sqlite_cur.fetchall()
print(f"✅ Fetched {len(records):,} records")

if len(records) == 0:
    print("\n[WARNING] No data to migrate!")
    exit(0)

# Create temp table
print(f"\nCreating temporary table...")
pg_cur.execute("""
    CREATE TEMP TABLE temp_traffic (
        date DATE,
        child_asin VARCHAR,
        sku VARCHAR,
        parent_asin VARCHAR,
        sessions INTEGER,
        session_percentage FLOAT,
        page_views INTEGER,
        page_views_percentage FLOAT,
        buy_box_percentage FLOAT,
        units_ordered INTEGER,
        units_ordered_b2b INTEGER,
        ordered_product_sales FLOAT,
        ordered_product_sales_b2b FLOAT,
        total_order_items INTEGER,
        conversion_rate FLOAT
    )
""")

# Bulk insert into temp table
print(f"Inserting into temp table...")
insert_sql = "INSERT INTO temp_traffic VALUES %s"
execute_values(pg_cur, insert_sql, records, page_size=1000)
print(f"✅ Inserted {len(records):,} records into temp table")

# Merge from temp table to main table
print(f"\nMerging into child_traffic_metrics...")
pg_cur.execute("""
    INSERT INTO child_traffic_metrics (
        date, child_asin, sku, parent_asin,
        sessions, session_percentage, page_views, page_views_percentage,
        buy_box_percentage, units_ordered, units_ordered_b2b,
        ordered_product_sales, ordered_product_sales_b2b,
        total_order_items, conversion_rate
    )
    SELECT * FROM temp_traffic
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
""")

rows_affected = pg_cur.rowcount
pg_conn.commit()

print(f"✅ Merged {rows_affected:,} records")

# Verify
pg_cur.execute("""
    SELECT COUNT(*), MIN(date), MAX(date)
    FROM child_traffic_metrics
    WHERE date >= '2025-11-15' AND date <= '2025-11-28'
""")

result = pg_cur.fetchone()
print(f"\nVerification - RDS now has:")
print(f"  Rows for Nov 15-28: {result[0]:,}")
print(f"  Date range: {result[1]} to {result[2]}")

# Sample check
pg_cur.execute("""
    SELECT date, sessions, units_ordered, ordered_product_sales
    FROM child_traffic_metrics
    WHERE child_asin = 'B0BRTK1P8Z'
    AND date >= '2025-11-15'
    ORDER BY date
    LIMIT 5
""")

print(f"\nSample ASIN (B0BRTK1P8Z):")
for row in pg_cur.fetchall():
    print(f"  {row[0]}: Sessions={row[1]}, Units={row[2]}, Sales=${row[3]:.2f}")

sqlite_cur.close()
sqlite_conn.close()
pg_cur.close()
pg_conn.close()

print("\n" + "=" * 80)
print("✅ MIGRATION COMPLETE!")
print("=" * 80)
print("\nNext steps:")
print("  1. Run aggregation: python scripts/update_daily_metrics_rds.py 30")
print("  2. Verify: python scripts/check_data_status.py")




