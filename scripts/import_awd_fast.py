"""
Fast AWD Import with batch processing
"""
import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv
import sys

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    database=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD')
)

print("="*80)
print("IMPORTING AWD INVENTORY - FAST MODE")
print("="*80)

file_path = sys.argv[1] if len(sys.argv) > 1 else "AWD Invetorr Ledger.csv"

print(f"\nReading: {file_path}")
df = pd.read_csv(file_path, encoding='utf-8-sig')
df.columns = df.columns.str.strip()

print(f"Total rows: {len(df)}")

# Convert date
df['Date'] = pd.to_datetime(df['Date']).dt.date
df = df[df['Date'].notna()]

print(f"Date range: {df['Date'].min()} to {df['Date'].max()}")

# Filter to only Nov 12-27
df = df[(df['Date'] >= pd.to_datetime('2025-11-12').date()) & 
        (df['Date'] <= pd.to_datetime('2025-11-27').date())]

print(f"Rows for Nov 12-27: {len(df)}")

if len(df) == 0:
    print("No new data to import")
    sys.exit(0)

# Convert units
df['Total Units'] = pd.to_numeric(df['Total Units'], errors='coerce').fillna(0)

# Aggregate by date and SKU
agg = df.groupby(['Date', 'MSKU'], as_index=False).agg({
    'ASIN': 'first',
    'FNSKU': 'first',
    'Total Units': 'sum',
    'Facility ID': lambda x: ','.join(sorted({str(i) for i in x if pd.notna(i)})) or None
})

print(f"Aggregated to: {len(agg)} records")
print("\nInserting into database...")

cur = conn.cursor()
inserted = 0
updated = 0

for i, row in agg.iterrows():
    try:
        cur.execute("""
            INSERT INTO inventory_snapshots (
                snapshot_date, asin, sku, fnsku, fulfillment_program,
                total_quantity, available_quantity, reserved_quantity,
                inbound_working_quantity, inbound_shipped_quantity,
                inbound_receiving_quantity, research_quantity,
                fulfillment_center_id, source_report_type
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, 0, 0, 0, 0, 0, %s, %s)
        """, (
            row['Date'], row['ASIN'], row['MSKU'], row['FNSKU'], 'AWD',
            float(row['Total Units']), float(row['Total Units']),
            row['Facility ID'], 'AWD_INVENTORY_LEDGER'
        ))
        inserted += 1
    except psycopg2.IntegrityError:
        conn.rollback()
        cur.execute("""
            UPDATE inventory_snapshots 
            SET total_quantity = %s, available_quantity = %s, asin = %s, fnsku = %s
            WHERE snapshot_date = %s AND sku = %s AND fulfillment_program = %s
        """, (float(row['Total Units']), float(row['Total Units']), row['ASIN'], row['FNSKU'],
              row['Date'], row['MSKU'], 'AWD'))
        updated += 1
    
    if (inserted + updated) % 50 == 0:
        conn.commit()
        print(f"  Progress: {inserted + updated}/{len(agg)} ({(inserted+updated)/len(agg)*100:.0f}%)")

conn.commit()
cur.close()
conn.close()

print(f"\n[SUCCESS] Complete!")
print(f"  Inserted: {inserted}")
print(f"  Updated: {updated}")
print(f"  Total: {inserted + updated}")







