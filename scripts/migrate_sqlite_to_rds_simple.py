"""
Simple migration: Delete Nov 15-28 data from RDS, then insert fresh from SQLite
"""
import sqlite3
import psycopg2
from psycopg2.extras import execute_values
import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 80)
print("MIGRATING DATA FROM SQLITE TO RDS")
print("=" * 80)

# Connect
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

print(f"✅ Connected")

# First, delete any existing Nov 15-28 data from RDS
print(f"\nCleaning RDS (deleting any existing Nov 15-28 data)...")
pg_cur.execute("DELETE FROM child_traffic_metrics WHERE date >= '2025-11-15' AND date <= '2025-11-28'")
deleted = pg_cur.rowcount
pg_conn.commit()
print(f"  Deleted {deleted} existing rows")

# Fetch from SQLite
print(f"\nFetching from SQLite...")
sqlite_cur.execute("""
    SELECT 
        date, child_asin, sku, parent_asin,
        sessions, session_percentage, page_views, page_views_percentage,
        buy_box_percentage, units_ordered, units_ordered_b2b,
        ordered_product_sales, ordered_product_sales_b2b,
        total_order_items, conversion_rate
    FROM child_traffic_metrics
    WHERE date >= '2025-11-15' AND date <= '2025-11-28'
""")

records = sqlite_cur.fetchall()
print(f"✅ Fetched {len(records):,} records")

if len(records) == 0:
    print("[WARNING] No data to migrate!")
    exit(0)

# Bulk insert
print(f"\nInserting into RDS...")
insert_sql = """
    INSERT INTO child_traffic_metrics (
        date, child_asin, sku, parent_asin,
        sessions, session_percentage, page_views, page_views_percentage,
        buy_box_percentage, units_ordered, units_ordered_b2b,
        ordered_product_sales, ordered_product_sales_b2b,
        total_order_items, conversion_rate
    ) VALUES %s
"""

execute_values(pg_cur, insert_sql, records, page_size=500)
pg_conn.commit()

print(f"✅ Inserted {len(records):,} records")

# Verify
pg_cur.execute("""
    SELECT COUNT(*), MIN(date), MAX(date), COUNT(DISTINCT child_asin)
    FROM child_traffic_metrics
    WHERE date >= '2025-11-15' AND date <= '2025-11-28'
""")

result = pg_cur.fetchone()
print(f"\nVerification:")
print(f"  Total rows: {result[0]:,}")
print(f"  Date range: {result[1]} to {result[2]}")
print(f"  Unique ASINs: {result[3]}")

# Sample
pg_cur.execute("""
    SELECT date, sessions, units_ordered, ordered_product_sales
    FROM child_traffic_metrics
    WHERE child_asin = 'B0BRTK1P8Z' AND date >= '2025-11-15'
    ORDER BY date
    LIMIT 5
""")

print(f"\nSample (B0BRTK1P8Z):")
for row in pg_cur.fetchall():
    print(f"  {row[0]}: Sessions={row[1]}, Units={row[2]}, Sales=${row[3]:.2f}")

sqlite_cur.close()
sqlite_conn.close()
pg_cur.close()
pg_conn.close()

print("\n" + "=" * 80)
print("✅ SUCCESS! Data migrated to RDS")
print("=" * 80)
print("\nNext: python scripts/update_daily_metrics_rds.py 30")










