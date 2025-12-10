import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    database=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD')
)
cur = conn.cursor()

print("=" * 80)
print("IMPORTING AWD INVENTORY LEDGER (FIXED)")
print("=" * 80)

# Reset the sequence first
cur.execute("""
    SELECT setval(
        pg_get_serial_sequence('inventory_snapshots', 'id'),
        (SELECT MAX(id) FROM inventory_snapshots) + 1
    )
""")
conn.commit()
print("\n✅ Reset ID sequence")

# Read CSV
csv_file = sys.argv[1] if len(sys.argv) > 1 else "AWD Invetorr Ledger.csv"
print(f"\nReading: {csv_file}")

df = pd.read_csv(csv_file)
print(f"Total rows: {len(df)}")

# Normalize column names
df.columns = df.columns.str.strip()

# Parse date
df['Date'] = pd.to_datetime(df['Date']).dt.date
df = df[df['Date'].notna()]
print(f"Rows with valid dates: {len(df)}")
print(f"Date range: {df['Date'].min()} to {df['Date'].max()}")

# Get existing dates
cur.execute("""
    SELECT DISTINCT snapshot_date 
    FROM inventory_snapshots 
    WHERE fulfillment_program = 'AWD'
    ORDER BY snapshot_date
""")
existing_dates = [r[0] for r in cur.fetchall()]
print(f"\nDates already in DB: {existing_dates}")

# Filter to only new dates (Nov 12+)
df_new = df[df['Date'] >= pd.Timestamp('2025-11-12').date()].copy()
print(f"Rows for Nov 12+: {len(df_new)}")

if len(df_new) == 0:
    print("\n❌ No new data to import!")
    sys.exit(0)

# Group by (Date, MSKU) and sum quantities to deduplicate
df_grouped = df_new.groupby(['Date', 'MSKU'], as_index=False).agg({
    'ASIN': 'first',
    'FNSKU': 'first',
    'Total Units': 'sum',
    'Facility ID': 'first'
})

print(f"\nAfter deduplication: {len(df_grouped)} unique (date, sku) combinations")

# Prepare records
records = []
for _, row in df_grouped.iterrows():
    total_units = float(row.get('Total Units', 0) or 0)
    records.append((
        row['Date'],
        row.get('ASIN'),
        row.get('MSKU'),  # SKU column name
        row.get('FNSKU'),
        'AWD',
        total_units,  # total_quantity
        total_units,  # available_quantity
        None,  # reserved_quantity
        None,  # inbound_working_quantity
        None,  # inbound_shipped_quantity
        None,  # inbound_receiving_quantity
        None,  # research_quantity
        row.get('Facility ID'),  # fulfillment_center_id
        'AWD Inventory Ledger'  # source_report_type
    ))

print(f"Prepared {len(records)} records")

# Use ON CONFLICT to handle duplicates
UPSERT_SQL = """
    INSERT INTO inventory_snapshots (
        snapshot_date, asin, sku, fnsku, fulfillment_program,
        total_quantity, available_quantity, reserved_quantity,
        inbound_working_quantity, inbound_shipped_quantity,
        inbound_receiving_quantity, research_quantity,
        fulfillment_center_id, source_report_type
    ) VALUES %s
    ON CONFLICT (snapshot_date, sku, fulfillment_program) 
    DO UPDATE SET
        asin = EXCLUDED.asin,
        total_quantity = EXCLUDED.total_quantity,
        available_quantity = EXCLUDED.available_quantity
"""

print("\nInserting/updating records...")
execute_values(cur, UPSERT_SQL, records, page_size=500)
conn.commit()

print(f"\n✅ Successfully imported {len(records)} AWD records!")

# Verify
cur.execute("""
    SELECT 
        snapshot_date,
        COUNT(*) as count
    FROM inventory_snapshots
    WHERE fulfillment_program = 'AWD'
    AND snapshot_date >= '2025-11-12'
    GROUP BY snapshot_date
    ORDER BY snapshot_date
""")

print("\nVerification - AWD inventory by date:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]} records")

cur.close()
conn.close()

print("\n" + "=" * 80)
print("✅ IMPORT COMPLETE!")
print("=" * 80)

