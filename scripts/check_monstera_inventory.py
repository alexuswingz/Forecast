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
print(f"INVENTORY CHECK FOR MONSTERA ({asin})")
print("=" * 80)

# Check what SKU this ASIN maps to
print("\n[1] ASIN to SKU Mapping:")
cur.execute("SELECT asin, sku FROM products WHERE asin = %s", (asin,))
product = cur.fetchone()
if product:
    print(f"  ASIN: {product['asin']}")
    print(f"  SKU: {product['sku']}")
    sku = product['sku']
else:
    print(f"  No product found for {asin}")
    sku = None

# Check inventory_snapshots for this SKU
if sku:
    print(f"\n[2] Inventory Snapshots for SKU '{sku}':")
    cur.execute("""
        SELECT snapshot_date, sku, fulfillment_program, 
               total_quantity, available_quantity, reserved_quantity,
               inbound_working_quantity, inbound_shipped_quantity, inbound_receiving_quantity
        FROM inventory_snapshots 
        WHERE sku = %s
        ORDER BY snapshot_date DESC
        LIMIT 10
    """, (sku,))
    
    rows = cur.fetchall()
    if rows:
        for r in rows:
            print(f"  {r['snapshot_date']} | {r['fulfillment_program']:3s} | Total={r['total_quantity']:4d} | Avail={r['available_quantity']:4d} | Reserved={r['reserved_quantity']:4d} | Inbound={r['inbound_working_quantity']:4d}")
    else:
        print(f"  No snapshots found for SKU '{sku}'")

# Check all AWD inventory
print("\n[3] All AWD Inventory (Latest):")
cur.execute("""
    SELECT sku, total_quantity, available_quantity, snapshot_date
    FROM inventory_snapshots 
    WHERE fulfillment_program = 'AWD'
    AND snapshot_date = (SELECT MAX(snapshot_date) FROM inventory_snapshots WHERE fulfillment_program = 'AWD')
    ORDER BY total_quantity DESC
    LIMIT 10
""")

rows = cur.fetchall()
if rows:
    print(f"  Latest AWD snapshot date: {rows[0]['snapshot_date']}")
    for r in rows:
        total = r['total_quantity'] if r['total_quantity'] else 0
        avail = r['available_quantity'] if r['available_quantity'] else 0
        print(f"    {r['sku']:40s} | Total={total:4.0f} | Avail={avail:4.0f}")
else:
    print("  No AWD inventory found!")

# Check all FBA inventory  
print("\n[4] All FBA Inventory (Latest):")
cur.execute("""
    SELECT sku, total_quantity, available_quantity, snapshot_date
    FROM inventory_snapshots 
    WHERE fulfillment_program = 'FBA'
    AND snapshot_date = (SELECT MAX(snapshot_date) FROM inventory_snapshots WHERE fulfillment_program = 'FBA')
    ORDER BY total_quantity DESC
    LIMIT 10
""")

rows = cur.fetchall()
if rows:
    print(f"  Latest FBA snapshot date: {rows[0]['snapshot_date']}")
    for r in rows:
        total = r['total_quantity'] if r['total_quantity'] else 0
        avail = r['available_quantity'] if r['available_quantity'] else 0
        print(f"    {r['sku']:40s} | Total={total:4.0f} | Avail={avail:4.0f}")
else:
    print("  No FBA inventory found!")

cur.close()
conn.close()

