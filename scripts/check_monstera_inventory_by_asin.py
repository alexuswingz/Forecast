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

asin = 'B0BRTK1P8Z'

print("=" * 80)
print(f"INVENTORY FOR {asin} (Monstera)")
print("=" * 80)

# Check by ASIN
cur.execute("""
    SELECT snapshot_date, asin, sku, fulfillment_program, 
           total_quantity, available_quantity, reserved_quantity
    FROM inventory_snapshots
    WHERE asin = %s
    ORDER BY snapshot_date DESC
    LIMIT 10
""", (asin,))

rows = cur.fetchall()
if rows:
    print(f"\nFound {len(rows)} records for ASIN {asin}:")
    for r in rows:
        print(f"  {r['snapshot_date']} | {r['fulfillment_program']:3s} | SKU: {r['sku']:30s} | Total={r['total_quantity']:4.0f} | Avail={r['available_quantity']:4.0f}")
else:
    print(f"\nNO INVENTORY FOUND for ASIN {asin}!")
    
    # Try to find by SKU pattern
    print("\nLooking for similar SKUs...")
    cur.execute("""
        SELECT DISTINCT sku, asin, fulfillment_program
        FROM inventory_snapshots
        WHERE sku LIKE '%MONST%'
        ORDER BY sku
    """)
    
    similar = cur.fetchall()
    if similar:
        print(f"Found {len(similar)} SKUs with 'MONST':")
        for s in similar:
            print(f"  SKU: {s['sku']:30s} | ASIN: {s['asin'] or 'NULL':13s} | Program: {s['fulfillment_program']}")
    else:
        print("No similar SKUs found!")

cur.close()
conn.close()







