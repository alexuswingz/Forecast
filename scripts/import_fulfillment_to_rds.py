"""
Import Fulfillment Report to PostgreSQL RDS
"""
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import os
from dotenv import load_dotenv
import sys

load_dotenv()

def safe_float(value):
    if pd.isna(value) or value in (None, "", "nan", "NaN"):
        return 0.0
    try:
        return float(str(value).replace(",", "").replace("$", ""))
    except:
        return 0.0

def safe_int(value):
    try:
        return int(safe_float(value))
    except:
        return 0

def safe_date(value):
    if pd.isna(value):
        return None
    try:
        return pd.to_datetime(value).date()
    except:
        return None

print("=" * 80)
print("IMPORTING FULFILLMENT REPORT TO RDS")
print("=" * 80)

if len(sys.argv) < 2:
    print("\nUsage: python import_fulfillment_to_rds.py <fulfillment_report.csv>")
    exit(1)

file_path = sys.argv[1]
print(f"\nReading: {file_path}")

# Read CSV
df = pd.read_csv(file_path, encoding='utf-8-sig')
print(f"Total rows: {len(df)}")
print(f"Columns: {list(df.columns)[:5]}...")

# Normalize column names
df.columns = df.columns.str.strip().str.replace('\ufeff', '')

# Connect to RDS
conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    database=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    port=int(os.getenv('DB_PORT', 5432))
)
cur = conn.cursor()

# First, get SKU to ASIN mapping from multiple sources
print("\nGetting SKU to ASIN mapping from RDS...")

# Try child_traffic_metrics
cur.execute("SELECT DISTINCT sku, child_asin FROM child_traffic_metrics WHERE sku IS NOT NULL AND child_asin IS NOT NULL")
sku_to_asin = {row[0]: row[1] for row in cur.fetchall()}

# Try catalog table if it exists  
try:
    cur.execute("SELECT DISTINCT sku, child_asin FROM catalog WHERE sku IS NOT NULL AND child_asin IS NOT NULL")
    for row in cur.fetchall():
        if row[0] not in sku_to_asin:
            sku_to_asin[row[0]] = row[1]
except:
    pass

# Try products table
try:
    cur.execute("SELECT DISTINCT sku, asin FROM products WHERE sku IS NOT NULL AND asin IS NOT NULL")
    for row in cur.fetchall():
        if row[0] not in sku_to_asin:
            sku_to_asin[row[0]] = row[1]
except:
    pass

print(f"  Loaded {len(sku_to_asin)} SKU mappings")

# Map common Amazon fulfillment report columns
records = []
skipped_no_asin = 0

for _, row in df.iterrows():
    # Try different date column names
    order_date = safe_date(
        row.get('purchase-date') or 
        row.get('Purchase Date') or
        row.get('order-date') or 
        row.get('Shipment Date')
    )
    
    if not order_date:
        continue
    
    # Import ALL November data (Nov 1-29)
    if order_date < pd.to_datetime('2025-11-01').date() or order_date > pd.to_datetime('2025-11-29').date():
        continue
    
    # Get SKU and look up ASIN
    sku = str(row.get('Merchant SKU') or row.get('sku') or row.get('SKU') or row.get('seller-sku') or '').strip()
    if not sku or sku == 'nan':
        continue
    
    # Look up ASIN from SKU mapping
    asin = sku_to_asin.get(sku)
    if not asin:
        # Try using SKU as ASIN if it looks like an ASIN (starts with B0)
        if sku.startswith('B0') and len(sku) == 10:
            asin = sku
        else:
            skipped_no_asin += 1
            continue
    
    # Get order details
    order_id = str(row.get('Amazon Order Id') or row.get('amazon-order-id') or '').strip()
    quantity = safe_int(row.get('Shipped Quantity') or row.get('quantity-purchased') or row.get('Quantity') or 0)
    
    # Get pricing
    item_price = safe_float(row.get('Item Price') or row.get('item-price') or 0)
    
    if quantity == 0:
        continue
    
    record = (
        order_id,
        order_date,
        asin,
        sku,
        quantity,
        item_price
    )
    records.append(record)

if skipped_no_asin > 0:
    print(f"\n[INFO] Skipped {skipped_no_asin} rows with no ASIN mapping")

print(f"\nFiltered to Nov 1-29: {len(records)} records")

if len(records) == 0:
    print("[WARNING] No data to import for Nov 1-29!")
    print("\nAvailable columns in file:")
    print(list(df.columns))
    exit(0)

# Delete existing data for this date range
print(f"\nDeleting existing order data for Nov 1-29...")
cur.execute("DELETE FROM order_items WHERE order_date::date >= '2025-11-01' AND order_date::date <= '2025-11-29'")
deleted = cur.rowcount
conn.commit()
print(f"  Deleted {deleted} existing rows")

# Bulk insert
print(f"\nInserting {len(records)} records...")
insert_sql = """
    INSERT INTO order_items (
        order_id, order_date, asin, sku, quantity, item_price
    ) VALUES %s
"""

execute_values(cur, insert_sql, records, page_size=500)
conn.commit()

print(f"✅ Inserted {len(records)} records")

# Verify
cur.execute("""
    SELECT 
        COUNT(*) as total_rows,
        MIN(order_date::date) as earliest,
        MAX(order_date::date) as latest,
        COUNT(DISTINCT asin) as unique_asins,
        SUM(quantity) as total_units,
        SUM(item_price * quantity) as total_sales
    FROM order_items
    WHERE order_date::date >= '2025-11-01' AND order_date::date <= '2025-11-29'
""")

result = cur.fetchone()
print(f"\nVerification:")
print(f"  Rows: {result[0]:,}")
print(f"  Date range: {result[1]} to {result[2]}")
print(f"  Unique ASINs: {result[3]}")
print(f"  Total units: {result[4]:,}")
print(f"  Total sales: ${result[5]:,.2f}")

cur.close()
conn.close()

print("\n" + "=" * 80)
print("✅ FULFILLMENT REPORT IMPORTED SUCCESSFULLY")
print("=" * 80)

