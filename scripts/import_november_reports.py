"""
Import November reports with automatic duplicate filtering
Skips dates already in database (Nov 1-14) and imports only new data (Nov 15-29)
"""
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from datetime import datetime, date
import os
from dotenv import load_dotenv
import sys

load_dotenv()

# Database connection
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        port=int(os.getenv('DB_PORT', 5432))
    )

def safe_float(value):
    """Convert value to float, handling various formats"""
    if pd.isna(value) or value in (None, "", "-", "NaN", "N/A"):
        return 0.0
    try:
        if isinstance(value, str):
            # Remove currency symbols, commas, percentages
            value = value.replace('$', '').replace(',', '').replace('%', '').strip()
        return float(value)
    except (ValueError, TypeError):
        return 0.0

def safe_int(value):
    """Convert value to int, handling various formats"""
    try:
        return int(safe_float(value))
    except (ValueError, TypeError):
        return 0

def safe_date(value):
    """Convert value to date"""
    if pd.isna(value):
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return pd.to_datetime(value).date()
    except:
        return None

def get_existing_dates(conn, table_name, date_column='date'):
    """Get set of dates that already exist in the database"""
    cur = conn.cursor()
    cur.execute(f"""
        SELECT DISTINCT {date_column} 
        FROM {table_name} 
        WHERE {date_column} >= '2025-11-01' AND {date_column} <= '2025-11-30'
    """)
    existing = {row[0] for row in cur.fetchall()}
    cur.close()
    return existing

def import_business_report(file_path, conn):
    """Import Business Report (Sales & Traffic data)"""
    print("\n" + "="*80)
    print("IMPORTING BUSINESS REPORT (Sales & Traffic)")
    print("="*80)
    
    # Read the CSV
    print(f"\nReading: {file_path}")
    df = pd.read_excel(file_path) if file_path.endswith('.xlsx') else pd.read_csv(file_path, encoding='utf-8-sig')
    
    print(f"Total rows in file: {len(df)}")
    print(f"Columns found: {list(df.columns)}")
    
    # Normalize column names (remove BOM, strip spaces)
    df.columns = df.columns.str.strip().str.replace('\ufeff', '')
    
    # Convert date column
    date_col = None
    for col in ['Date', 'date', 'Day', '(Day)']:
        if col in df.columns:
            date_col = col
            break
    
    if not date_col:
        print("[ERROR] Could not find date column!")
        print("Available columns:", list(df.columns))
        print("\n[INFO] This appears to be a summary report without daily dates.")
        print("You need the 'Detail Page Sales and Traffic by Child Item' report")
        print("with DAILY data, not a summary report.")
        return 0
    
    df['date'] = df[date_col].apply(safe_date)
    df = df[df['date'].notna()]
    
    print(f"Rows with valid dates: {len(df)}")
    print(f"Date range in file: {df['date'].min()} to {df['date'].max()}")
    
    # Get existing dates to avoid duplicates
    existing_dates = get_existing_dates(conn, 'child_traffic_metrics')
    print(f"\nDates already in database: {sorted(existing_dates)}")
    
    # Filter out existing dates
    df = df[~df['date'].isin(existing_dates)]
    print(f"Rows after filtering duplicates: {len(df)}")
    
    if len(df) == 0:
        print("[INFO] No new data to import (all dates already exist)")
        return 0
    
    # Map columns to database fields
    column_mapping = {
        'Child ASIN': 'child_asin',
        '(Child) ASIN': 'child_asin',
        'ASIN': 'child_asin',
        'SKU': 'sku',
        'Parent ASIN': 'parent_asin',
        'Sessions': 'sessions',
        'Page Views': 'page_views',
        'Units Ordered': 'units_ordered',
        'Units Sold': 'units_ordered',
        'Ordered Product Sales': 'ordered_product_sales',
        'Total Order Items': 'total_order_items',
        'Unit Session Percentage': 'conversion_rate',
        'Buy Box Percentage': 'buy_box_percentage',
        'Session Percentage': 'session_percentage',
        'Page Views Percentage': 'page_views_percentage',
    }
    
    # Prepare records for insertion
    records = []
    for _, row in df.iterrows():
        child_asin = None
        for col in ['Child ASIN', '(Child) ASIN', 'ASIN']:
            if col in row and pd.notna(row[col]):
                child_asin = str(row[col]).strip()
                break
        
        if not child_asin:
            continue
        
        sku = str(row.get('SKU', child_asin)).strip() if 'SKU' in row else child_asin
        
        record = (
            row['date'],
            child_asin,
            sku,
            str(row.get('Parent ASIN', '')).strip() if 'Parent ASIN' in row else None,
            safe_float(row.get('Sessions', 0)),
            safe_float(row.get('Session Percentage', 0)),
            safe_float(row.get('Page Views', 0)),
            safe_float(row.get('Page Views Percentage', 0)),
            safe_float(row.get('Buy Box Percentage', 0)),
            safe_int(row.get('Units Ordered', 0)),
            safe_int(row.get('Units Ordered - B2B', 0)),
            safe_float(row.get('Ordered Product Sales', 0)),
            safe_float(row.get('Ordered Product Sales - B2B', 0)),
            safe_int(row.get('Total Order Items', 0)),
            safe_float(row.get('Unit Session Percentage', 0)),
        )
        records.append(record)
    
    # Bulk insert with UPSERT
    cur = conn.cursor()
    insert_sql = """
        INSERT INTO child_traffic_metrics (
            date, child_asin, sku, parent_asin,
            sessions, session_percentage, page_views, page_views_percentage,
            buy_box_percentage, units_ordered, units_ordered_b2b,
            ordered_product_sales, ordered_product_sales_b2b,
            total_order_items, conversion_rate
        ) VALUES %s
        ON CONFLICT (date, child_asin, sku) DO UPDATE SET
            parent_asin = EXCLUDED.parent_asin,
            sessions = EXCLUDED.sessions,
            session_percentage = EXCLUDED.session_percentage,
            page_views = EXCLUDED.page_views,
            page_views_percentage = EXCLUDED.page_views_percentage,
            buy_box_percentage = EXCLUDED.buy_box_percentage,
            units_ordered = EXCLUDED.units_ordered,
            units_ordered_b2b = EXCLUDED.units_ordered_b2b,
            ordered_product_sales = EXCLUDED.ordered_product_sales,
            ordered_product_sales_b2b = EXCLUDED.ordered_product_sales_b2b,
            total_order_items = EXCLUDED.total_order_items,
            conversion_rate = EXCLUDED.conversion_rate
    """
    
    execute_values(cur, insert_sql, records)
    conn.commit()
    cur.close()
    
    print(f"\n[SUCCESS] Imported {len(records)} rows from Business Report")
    return len(records)

def import_awd_inventory(file_path, conn):
    """Import AWD Inventory Ledger"""
    print("\n" + "="*80)
    print("IMPORTING AWD INVENTORY LEDGER")
    print("="*80)
    
    print(f"\nReading: {file_path}")
    df = pd.read_excel(file_path) if file_path.endswith('.xlsx') else pd.read_csv(file_path, encoding='utf-8-sig')
    
    print(f"Total rows in file: {len(df)}")
    print(f"Columns found: {list(df.columns)}")
    
    # Normalize column names
    df.columns = df.columns.str.strip().str.replace('\ufeff', '')
    
    # Map columns (handle different AWD report formats)
    column_mapping = {
        'Date': 'date',
        'MSKU': 'sku',
        'FNSKU': 'fnsku',
        'ASIN': 'asin',
        'Package Quantity': 'package_qty',
        'Ending Warehouse Balance (cartons)': 'ending_cartons',
        'Number of Cartons': 'ending_cartons',  # Alternative column name
        'Total Units': 'total_units',  # Sometimes AWD has total units directly
        'Facility ID': 'facility_id',
    }
    
    # Rename columns
    df = df.rename(columns=column_mapping)
    
    # Convert date
    df['date'] = df['date'].apply(safe_date)
    df = df[df['date'].notna()]
    
    print(f"Rows with valid dates: {len(df)}")
    print(f"Date range in file: {df['date'].min()} to {df['date'].max()}")
    
    # Get existing dates
    existing_dates = get_existing_dates(conn, 'inventory_snapshots', 'snapshot_date')
    print(f"\nDates already in database: {sorted(existing_dates)}")
    
    # Filter out existing dates
    df = df[~df['date'].isin(existing_dates)]
    print(f"Rows after filtering duplicates: {len(df)}")
    
    if len(df) == 0:
        print("[INFO] No new data to import (all dates already exist)")
        return 0
    
    # Calculate units (package_qty * ending_cartons OR use total_units directly)
    if 'total_units' in df.columns and df['total_units'].notna().any():
        # AWD Inventory Ledger format - has Total Units column
        df['units'] = df['total_units'].apply(safe_float)
    elif 'package_qty' in df.columns and 'ending_cartons' in df.columns:
        # AWD Balance Report format - calculate from package_qty * ending_cartons
        df['package_qty'] = df['package_qty'].apply(safe_float)
        df['ending_cartons'] = df['ending_cartons'].apply(safe_float)
        df['units'] = df['package_qty'] * df['ending_cartons']
    else:
        print("[ERROR] Cannot determine units - missing required columns")
        print(f"Available columns: {list(df.columns)}")
        return 0
    
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
            'AWD',  # fulfillment_program
            units,  # total_quantity
            units,  # available_quantity
            0.0,    # reserved_quantity
            0.0,    # inbound_working_quantity
            0.0,    # inbound_shipped_quantity
            0.0,    # inbound_receiving_quantity
            0.0,    # research_quantity
            row.get('facility_id'),
            'AWD_INVENTORY_LEDGER'
        )
        records.append(record)
    
    # Bulk insert
    cur = conn.cursor()
    insert_sql = """
        INSERT INTO inventory_snapshots (
            snapshot_date, asin, sku, fnsku, fulfillment_program,
            total_quantity, available_quantity, reserved_quantity,
            inbound_working_quantity, inbound_shipped_quantity,
            inbound_receiving_quantity, research_quantity,
            fulfillment_center_id, source_report_type
        ) VALUES %s
        ON CONFLICT (snapshot_date, sku, fulfillment_program) DO UPDATE SET
            asin = EXCLUDED.asin,
            fnsku = EXCLUDED.fnsku,
            total_quantity = EXCLUDED.total_quantity,
            available_quantity = EXCLUDED.available_quantity,
            reserved_quantity = EXCLUDED.reserved_quantity,
            inbound_working_quantity = EXCLUDED.inbound_working_quantity,
            inbound_shipped_quantity = EXCLUDED.inbound_shipped_quantity,
            inbound_receiving_quantity = EXCLUDED.inbound_receiving_quantity,
            research_quantity = EXCLUDED.research_quantity,
            fulfillment_center_id = EXCLUDED.fulfillment_center_id,
            source_report_type = EXCLUDED.source_report_type
    """
    
    execute_values(cur, insert_sql, records)
    conn.commit()
    cur.close()
    
    print(f"\n[SUCCESS] Imported {len(records)} AWD inventory records")
    return len(records)

def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/import_november_reports.py <BusinessReport.xlsx> <AWDInventory.xlsx>")
        print("\nExample:")
        print('  python scripts/import_november_reports.py "BusinessReport-11-29-25.xlsx" "AWD Inventorr Ledger.xlsx"')
        sys.exit(1)
    
    business_report_path = sys.argv[1]
    awd_inventory_path = sys.argv[2]
    
    # Verify files exist
    if not os.path.exists(business_report_path):
        print(f"[ERROR] File not found: {business_report_path}")
        sys.exit(1)
    
    if not os.path.exists(awd_inventory_path):
        print(f"[ERROR] File not found: {awd_inventory_path}")
        sys.exit(1)
    
    print("=" * 80)
    print("NOVEMBER REPORTS IMPORT - AUTOMATIC DUPLICATE FILTERING")
    print("=" * 80)
    print(f"\nBusiness Report: {business_report_path}")
    print(f"AWD Inventory:   {awd_inventory_path}")
    print(f"\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Connect to database
    conn = get_db_connection()
    
    try:
        # Import both reports
        business_count = import_business_report(business_report_path, conn)
        awd_count = import_awd_inventory(awd_inventory_path, conn)
        
        print("\n" + "=" * 80)
        print("IMPORT COMPLETE")
        print("=" * 80)
        print(f"Business Report rows imported: {business_count}")
        print(f"AWD Inventory rows imported:   {awd_count}")
        print(f"Total records imported:        {business_count + awd_count}")
        print("\n[NEXT STEP] Run aggregation:")
        print("  python scripts/update_daily_metrics.py")
        
    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] Import failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == '__main__':
    main()

