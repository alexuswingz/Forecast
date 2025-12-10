"""
Migrate child_traffic_metrics data from SQLite to PostgreSQL RDS
"""
import sqlite3
import psycopg2
from psycopg2.extras import execute_values
import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 80)
print("MIGRATING DATA FROM SQLITE TO POSTGRESQL RDS")
print("=" * 80)

# Connect to SQLite
sqlite_db = 'kpi_metrics.db'
if not os.path.exists(sqlite_db):
    print(f"\n[ERROR] SQLite database not found: {sqlite_db}")
    exit(1)

sqlite_conn = sqlite3.connect(sqlite_db)
sqlite_cur = sqlite_conn.cursor()

# Connect to PostgreSQL RDS
pg_conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    database=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    port=int(os.getenv('DB_PORT', 5432))
)
pg_cur = pg_conn.cursor()

print(f"\n✅ Connected to SQLite: {sqlite_db}")
print(f"✅ Connected to PostgreSQL RDS: {os.getenv('DB_HOST')}")

# Check what data exists in SQLite for Nov 15-28
sqlite_cur.execute("""
    SELECT COUNT(*) as count, MIN(date) as min_date, MAX(date) as max_date
    FROM child_traffic_metrics
    WHERE date >= '2025-11-15' AND date <= '2025-11-28'
""")

result = sqlite_cur.fetchone()
count, min_date, max_date = result

print(f"\nSQLite data for Nov 15-28:")
print(f"  Rows: {count:,}")
print(f"  Date range: {min_date} to {max_date}")

if count == 0:
    print("\n[WARNING] No data found in SQLite for Nov 15-28!")
    print("The SP-API import might still be running or failed.")
    exit(0)

# Fetch all records from SQLite
print(f"\nFetching {count:,} records from SQLite...")
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

# Insert into PostgreSQL one by one to handle conflicts
print(f"\nInserting into PostgreSQL RDS...")

insert_sql = """
    INSERT INTO child_traffic_metrics (
        date, child_asin, sku, parent_asin,
        sessions, session_percentage, page_views, page_views_percentage,
        buy_box_percentage, units_ordered, units_ordered_b2b,
        ordered_product_sales, ordered_product_sales_b2b,
        total_order_items, conversion_rate
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

update_sql = """
    UPDATE child_traffic_metrics SET
        parent_asin = %s,
        sessions = %s,
        session_percentage = %s,
        page_views = %s,
        page_views_percentage = %s,
        buy_box_percentage = %s,
        units_ordered = %s,
        units_ordered_b2b = %s,
        ordered_product_sales = %s,
        ordered_product_sales_b2b = %s,
        total_order_items = %s,
        conversion_rate = %s,
        updated_at = CURRENT_TIMESTAMP
    WHERE date = %s AND child_asin = %s AND sku = %s
"""

total_inserted = 0
total_updated = 0

for i, record in enumerate(records):
    try:
        pg_cur.execute(insert_sql, record)
        total_inserted += 1
    except psycopg2.errors.UniqueViolation:
        pg_conn.rollback()
        # Update instead
        update_values = record[3:] + record[:3]  # reorder for UPDATE
        pg_cur.execute(update_sql, update_values)
        total_updated += 1
    
    if (i + 1) % 500 == 0:
        pg_conn.commit()
        print(f"  Progress: {i+1:,}/{len(records):,} ({(i+1)/len(records)*100:.0f}%) - Inserted: {total_inserted}, Updated: {total_updated}")

pg_conn.commit()  # Final commit
print(f"\n✅ Successfully migrated to RDS:")
print(f"   Inserted: {total_inserted:,} new records")
print(f"   Updated: {total_updated:,} existing records")
print(f"   Total: {total_inserted + total_updated:,} records")

# Verify in RDS
pg_cur.execute("""
    SELECT COUNT(*) as count, MIN(date) as min_date, MAX(date) as max_date
    FROM child_traffic_metrics
    WHERE date >= '2025-11-15' AND date <= '2025-11-28'
""")

result = pg_cur.fetchone()
print(f"\nVerification - RDS now has:")
print(f"  Rows for Nov 15-28: {result[0]:,}")
print(f"  Date range: {result[1]} to {result[2]}")

# Check sample ASIN
pg_cur.execute("""
    SELECT date, sessions, units_ordered, ordered_product_sales
    FROM child_traffic_metrics
    WHERE child_asin = 'B0BRTK1P8Z'
    AND date >= '2025-11-15'
    ORDER BY date DESC
    LIMIT 5
""")

print(f"\nSample ASIN (B0BRTK1P8Z) in RDS:")
for row in pg_cur.fetchall():
    print(f"  {row[0]}: Sessions={row[1]}, Units={row[2]}, Sales=${row[3]:.2f}")

sqlite_cur.close()
sqlite_conn.close()
pg_cur.close()
pg_conn.close()

print("\n" + "=" * 80)
print("MIGRATION COMPLETE!")
print("=" * 80)
print("\nNext steps:")
print("  1. Run aggregation: python scripts/update_daily_metrics_rds.py 30")
print("  2. Verify: python scripts/check_data_status.py")

