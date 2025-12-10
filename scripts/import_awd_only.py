"""
Import AWD Inventory with duplicate filtering
"""
import pandas as pd
import psycopg2
import psycopg2.errors
from psycopg2.extras import execute_values
from datetime import datetime
import os
from dotenv import load_dotenv
import sys

load_dotenv()

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        port=int(os.getenv('DB_PORT', 5432))
    )

def safe_float(value):
    if pd.isna(value) or value in (None, "", "-", "NaN", "N/A"):
        return 0.0
    try:
        if isinstance(value, str):
            value = value.replace('$', '').replace(',', '').replace('%', '').strip()
        return float(value)
    except (ValueError, TypeError):
        return 0.0

def safe_date(value):
    if pd.isna(value):
        return None
    try:
        return pd.to_datetime(value).date()
    except:
        return None

def get_existing_dates(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT snapshot_date 
        FROM inventory_snapshots 
        WHERE snapshot_date >= '2025-11-01' AND snapshot_date <= '2025-11-30'
        AND fulfillment_program = 'AWD'
    """)
    existing = {row[0] for row in cur.fetchall()}
    cur.close()
    return existing

print("="*80)
print("IMPORTING AWD INVENTORY LEDGER")
print("="*80)

file_path = sys.argv[1] if len(sys.argv) > 1 else "AWD Invetorr Ledger.csv"

print(f"\nReading: {file_path}")
df = pd.read_csv(file_path, encoding='utf-8-sig')

print(f"Total rows in file: {len(df)}")

# Normalize column names
df.columns = df.columns.str.strip().str.replace('\ufeff', '')

# Map columns
column_mapping = {
    'Date': 'date',
    'MSKU': 'sku',
    'FNSKU': 'fnsku',
    'ASIN': 'asin',
    'Package Quantity': 'package_qty',
    'Number of Cartons': 'ending_cartons',
    'Total Units': 'total_units',
    'Facility ID': 'facility_id',
}

df = df.rename(columns=column_mapping)

# Convert date
df['date'] = df['date'].apply(safe_date)
df = df[df['date'].notna()]

print(f"Rows with valid dates: {len(df)}")
print(f"Date range in file: {df['date'].min()} to {df['date'].max()}")

# Get existing dates
conn = get_db_connection()
existing_dates = get_existing_dates(conn)
print(f"\nDates already in database: {sorted(existing_dates)}")

# Filter out existing dates
df = df[~df['date'].isin(existing_dates)]
print(f"Rows after filtering duplicates: {len(df)}")

if len(df) == 0:
    print("[INFO] No new data to import (all dates already exist)")
    conn.close()
    sys.exit(0)

# Calculate units
if 'total_units' in df.columns:
    df['units'] = df['total_units'].apply(safe_float)
else:
    df['package_qty'] = df['package_qty'].apply(safe_float)
    df['ending_cartons'] = df['ending_cartons'].apply(safe_float)
    df['units'] = df['package_qty'] * df['ending_cartons']

# Aggregate by date and SKU
aggregated = df.groupby(['date', 'sku'], as_index=False).agg({
    'asin': 'first',
    'fnsku': 'first',
    'units': 'sum',
    'facility_id': lambda x: ','.join(sorted({str(i) for i in x if pd.notna(i)})) or None
})

# Prepare records
records = []
for _, row in aggregated.iterrows():
    units = safe_float(row['units'])
    record = (
        row['date'],
        str(row.get('asin', '')).strip() or None,
        str(row['sku']).strip(),
        str(row.get('fnsku', '')).strip() or None,
        'AWD',
        units, units, 0.0, 0.0, 0.0, 0.0, 0.0,
        row.get('facility_id'),
        'AWD_INVENTORY_LEDGER'
    )
    records.append(record)

# Bulk insert with proper UPSERT
cur = conn.cursor()

# Insert records one by one to handle conflicts properly
inserted = 0
updated = 0
skipped = 0

for record in records:
    try:
        # Check if record already exists
        cur.execute("""
            SELECT 1 FROM inventory_snapshots 
            WHERE snapshot_date = %s AND sku = %s AND fulfillment_program = %s
        """, (record[0], record[2], record[4]))
        
        exists = cur.fetchone()
        
        if exists:
            # Update existing record
            cur.execute("""
                UPDATE inventory_snapshots SET
                    asin = %s,
                    fnsku = %s,
                    total_quantity = %s,
                    available_quantity = %s,
                    reserved_quantity = %s,
                    inbound_working_quantity = %s,
                    inbound_shipped_quantity = %s,
                    inbound_receiving_quantity = %s,
                    research_quantity = %s,
                    fulfillment_center_id = %s,
                    source_report_type = %s
                WHERE snapshot_date = %s AND sku = %s AND fulfillment_program = %s
            """, (
                record[1], record[3], record[5], record[6], record[7],
                record[8], record[9], record[10], record[11], record[12], record[13],
                record[0], record[2], record[4]
            ))
            updated += 1
        else:
            # Insert new record
            cur.execute("""
                INSERT INTO inventory_snapshots (
                    snapshot_date, asin, sku, fnsku, fulfillment_program,
                    total_quantity, available_quantity, reserved_quantity,
                    inbound_working_quantity, inbound_shipped_quantity,
                    inbound_receiving_quantity, research_quantity,
                    fulfillment_center_id, source_report_type
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, record)
            inserted += 1
        
        # Commit after each successful operation
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        skipped += 1
        if skipped <= 5:
            print(f"  Error: {e}")
    
    if (inserted + updated) % 100 == 0:
        print(f"  Progress: {inserted} inserted, {updated} updated...")

conn.commit()
cur.close()
conn.close()

print(f"\n[SUCCESS] AWD Inventory Import Complete!")
print(f"  Inserted: {inserted} new records")
print(f"  Updated:  {updated} existing records")
print(f"  Total:    {inserted + updated} records processed")
print(f"\nDates imported: {sorted(set(r[0] for r in records))}")

