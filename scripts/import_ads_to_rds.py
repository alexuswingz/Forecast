"""
Import Ads Report to PostgreSQL RDS
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
print("IMPORTING ADS REPORT TO RDS")
print("=" * 80)

if len(sys.argv) < 2:
    print("\nUsage: python import_ads_to_rds.py <ads_report.xlsx>")
    exit(1)

file_path = sys.argv[1]
print(f"\nReading: {file_path}")

# Read Excel file
df = pd.read_excel(file_path)
print(f"Total rows: {len(df)}")
print(f"Columns: {list(df.columns)[:5]}...")

# Normalize column names
df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_").str.replace("[^a-z0-9_]", "", regex=True)

# Connect to RDS
conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    database=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    port=int(os.getenv('DB_PORT', 5432))
)
cur = conn.cursor()

# Map columns (common Amazon Ads report column names)
column_map = {
    'date': 'report_date',
    'start_date': 'report_date',
    'advertised_asin': 'advertised_asin',
    'advertised_sku': 'advertised_sku',
    'campaign_name': 'campaign_name',
    'ad_group_name': 'ad_group_name',
    'impressions': 'impressions',
    'clicks': 'clicks',
    'spend': 'spend',
    '7_day_total_sales': 'sales_7d',
    '14_day_total_sales': 'sales_14d',
    '7_day_total_orders': 'orders_7d',
    '14_day_total_orders': 'orders_14d',
    '7_day_total_units': 'units_7d',
    '14_day_total_units': 'units_14d',
}

# Prepare records
records = []
for _, row in df.iterrows():
    report_date = safe_date(row.get('date') or row.get('start_date'))
    if not report_date:
        continue
    
    # Filter to Nov 1-29 only
    if report_date < pd.to_datetime('2025-11-01').date() or report_date > pd.to_datetime('2025-11-29').date():
        continue
    
    advertised_asin = str(row.get('advertised_asin', '')).strip()
    if not advertised_asin or advertised_asin == 'nan':
        continue
    
    record = (
        report_date,
        advertised_asin,
        str(row.get('advertised_sku', '') or row.get('sku', '')).strip() or None,
        str(row.get('campaign_name', '')).strip() or None,
        str(row.get('ad_group_name', '')).strip() or None,
        safe_int(row.get('impressions', 0)),
        safe_int(row.get('clicks', 0)),
        safe_float(row.get('spend', 0)),
        safe_float(row.get('14_day_total_sales', 0)),
        safe_int(row.get('14_day_total_orders', 0)),
        safe_int(row.get('14_day_total_units', 0))
    )
    records.append(record)

print(f"\nFiltered to Nov 1-29: {len(records)} records")

if len(records) == 0:
    print("[WARNING] No data to import for Nov 1-29!")
    exit(0)

# Delete existing data for this date range
print(f"\nDeleting existing ads data for Nov 1-29...")
cur.execute("DELETE FROM ad_product_performance WHERE report_date >= '2025-11-01' AND report_date <= '2025-11-29'")
deleted = cur.rowcount
conn.commit()
print(f"  Deleted {deleted} existing rows")

# Bulk insert
print(f"\nInserting {len(records)} records...")
insert_sql = """
    INSERT INTO ad_product_performance (
        report_date, advertised_asin, sku,
        campaign_name, ad_group_name,
        impressions, clicks, spend,
        sales_14d, orders_14d, units_14d
    ) VALUES %s
"""

execute_values(cur, insert_sql, records, page_size=500)
conn.commit()

print(f"✅ Inserted {len(records)} records")

# Verify
cur.execute("""
    SELECT 
        COUNT(*) as total_rows,
        MIN(report_date) as earliest,
        MAX(report_date) as latest,
        COUNT(DISTINCT advertised_asin) as unique_asins,
        SUM(spend) as total_spend,
        SUM(sales_14d) as total_sales
    FROM ad_product_performance
    WHERE report_date >= '2025-11-01' AND report_date <= '2025-11-29'
""")

result = cur.fetchone()
print(f"\nVerification:")
print(f"  Rows: {result[0]:,}")
print(f"  Date range: {result[1]} to {result[2]}")
print(f"  Unique ASINs: {result[3]}")
print(f"  Total spend: ${result[4]:,.2f}")
print(f"  Total sales (14d): ${result[5]:,.2f}")

cur.close()
conn.close()

print("\n" + "=" * 80)
print("✅ ADS REPORT IMPORTED SUCCESSFULLY")
print("=" * 80)

