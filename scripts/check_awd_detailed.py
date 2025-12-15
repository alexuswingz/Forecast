import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    database=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD')
)
cur = conn.cursor(cursor_factory=RealDictCursor)

print("=" * 80)
print("DETAILED AWD CHECK")
print("=" * 80)

# Check all AWD dates
cur.execute("""
    SELECT 
        snapshot_date,
        COUNT(*) as record_count,
        COUNT(DISTINCT sku) as unique_skus
    FROM inventory_snapshots
    WHERE fulfillment_program = 'AWD'
    GROUP BY snapshot_date
    ORDER BY snapshot_date DESC
    LIMIT 20
""")

print("\nAWD Inventory by Date:")
for r in cur.fetchall():
    print(f"  {r['snapshot_date']}: {r['record_count']:4d} records, {r['unique_skus']:3d} unique SKUs")

# Check if Nov 12-27 data exists for ANY SKU
cur.execute("""
    SELECT snapshot_date, COUNT(*) as count
    FROM inventory_snapshots
    WHERE fulfillment_program = 'AWD'
    AND snapshot_date >= '2025-11-12'
    AND snapshot_date <= '2025-11-27'
    GROUP BY snapshot_date
    ORDER BY snapshot_date
""")

rows = cur.fetchall()
if rows:
    print(f"\nFound AWD data for Nov 12-27:")
    for r in rows:
        print(f"  {r['snapshot_date']}: {r['count']} records")
else:
    print("\nNO AWD DATA FOUND for Nov 12-27!")

# Check Monstera specifically for Nov 12+
print("\n" + "=" * 80)
print("MONSTERA AWD - Nov 12+ Check")
print("=" * 80)

cur.execute("""
    SELECT snapshot_date, sku, total_quantity, available_quantity, fulfillment_program
    FROM inventory_snapshots
    WHERE asin = 'B0BRTK1P8Z'
    AND fulfillment_program = 'AWD'
    AND snapshot_date >= '2025-11-12'
    ORDER BY snapshot_date
""")

monstera_rows = cur.fetchall()
if monstera_rows:
    print(f"Found {len(monstera_rows)} Monstera AWD records for Nov 12+:")
    for r in monstera_rows:
        print(f"  {r['snapshot_date']}: Total={r['total_quantity']:5.0f}, Avail={r['available_quantity']:5.0f}")
else:
    print("NO Monstera AWD data for Nov 12+!")

cur.close()
conn.close()










