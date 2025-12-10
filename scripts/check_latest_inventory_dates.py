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
print("LATEST INVENTORY DATES BY FULFILLMENT PROGRAM")
print("=" * 80)

cur.execute("""
    SELECT 
        fulfillment_program,
        MAX(snapshot_date) as max_date,
        COUNT(*) as record_count
    FROM inventory_snapshots
    GROUP BY fulfillment_program
    ORDER BY fulfillment_program
""")

for r in cur.fetchall():
    print(f"{r['fulfillment_program']:3s}: {r['max_date']} ({r['record_count']:,} records)")

# Check AWD specifically for Monstera
print("\n" + "=" * 80)
print("MONSTERA (B0BRTK1P8Z) - AWD INVENTORY OVER TIME")
print("=" * 80)

cur.execute("""
    SELECT snapshot_date, total_quantity, available_quantity, sku
    FROM inventory_snapshots
    WHERE asin = 'B0BRTK1P8Z'
    AND fulfillment_program = 'AWD'
    ORDER BY snapshot_date DESC
    LIMIT 20
""")

rows = cur.fetchall()
if rows:
    for r in rows:
        print(f"  {r['snapshot_date']}: Total={r['total_quantity']:5.0f} | Avail={r['available_quantity']:5.0f} | SKU: {r['sku']}")
else:
    print("  No AWD data for Monstera!")

cur.close()
conn.close()




