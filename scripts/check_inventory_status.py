"""
Check inventory snapshot status (FBA, AWD, etc.)
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import date, datetime
import os
from dotenv import load_dotenv

load_dotenv()

def check_inventory_status():
    """Check current inventory snapshot data"""
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        database=os.getenv('DB_NAME', 'postgres'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', ''),
        port=int(os.getenv('DB_PORT', 5432))
    )
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    print("=" * 100)
    print(f"INVENTORY SNAPSHOTS STATUS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 100)
    print()
    print(f"Today's date: {date.today()}")
    print()
    
    # Check if table exists
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'inventory_snapshots'
        )
    """)
    table_exists = cur.fetchone()['exists']
    
    if not table_exists:
        print("[ERROR] 'inventory_snapshots' table does not exist!")
        print()
        print("ACTION: Create the table first using the models.py schema")
        cur.close()
        conn.close()
        return
    
    # Get total count
    cur.execute("SELECT COUNT(*) as count FROM inventory_snapshots")
    total_count = cur.fetchone()['count']
    
    if total_count == 0:
        print("[WARNING] No inventory snapshots found in database!")
        print()
        print("=" * 100)
        print("WHAT YOU NEED TO DOWNLOAD:")
        print("=" * 100)
        print()
        print("1. FBA INVENTORY REPORT")
        print("   Path: Seller Central > Reports > Fulfillment > Manage Inventory Health")
        print("   OR: Seller Central > Reports > Fulfillment > Amazon Fulfilled Inventory")
        print("   Date: Today's snapshot")
        print("   Format: CSV/TSV")
        print("   Import: python importers/import_fba_inventory_report.py <file.csv>")
        print()
        print("2. AWD INVENTORY REPORT (if using Amazon Warehousing & Distribution)")
        print("   Path: Seller Central > Reports > AWD Inventory")
        print("   Date: Today's snapshot")
        print("   Format: CSV")
        print("   Import: python importers/import_awd_inventory_report.py <file.csv>")
        print()
        cur.close()
        conn.close()
        return
    
    # Get latest snapshots by fulfillment program
    print(f"[1] INVENTORY SNAPSHOT SUMMARY")
    print("-" * 100)
    cur.execute("""
        SELECT 
            COALESCE(fulfillment_program, 'Unknown') as program,
            MAX(snapshot_date) as latest_date,
            COUNT(DISTINCT snapshot_date) as snapshot_count,
            COUNT(DISTINCT asin) as unique_asins,
            SUM(available_quantity) as total_available,
            SUM(reserved_quantity) as total_reserved,
            SUM(inbound_working_quantity + inbound_shipped_quantity + inbound_receiving_quantity) as total_inbound,
            SUM(total_quantity) as grand_total
        FROM inventory_snapshots
        GROUP BY fulfillment_program
        ORDER BY fulfillment_program
    """)
    
    summary = cur.fetchall()
    
    latest_date = None
    for row in summary:
        program = row['program']
        print(f"  Program: {program}")
        print(f"  Latest snapshot: {row['latest_date']}")
        print(f"  Unique ASINs: {row['unique_asins']}")
        print(f"  Total Available: {row['total_available']:,}")
        print(f"  Total Reserved: {row['total_reserved']:,}")
        print(f"  Total Inbound: {row['total_inbound']:,}")
        print(f"  Grand Total: {row['grand_total']:,}")
        print(f"  Snapshot count: {row['snapshot_count']}")
        
        if latest_date is None or row['latest_date'] > latest_date:
            latest_date = row['latest_date']
        
        days_behind = (date.today() - row['latest_date']).days
        if days_behind > 7:
            print(f"  Status: [ALERT] {days_behind} DAYS BEHIND")
        elif days_behind > 1:
            print(f"  Status: [WARNING] {days_behind} days behind")
        else:
            print(f"  Status: [OK] Up to date")
        print()
    
    # Get latest snapshot details
    print(f"[2] LATEST SNAPSHOT BREAKDOWN (by ASIN)")
    print("-" * 100)
    cur.execute("""
        SELECT 
            snapshot_date,
            fulfillment_program,
            asin,
            sku,
            fnsku,
            available_quantity,
            reserved_quantity,
            inbound_working_quantity,
            inbound_shipped_quantity,
            inbound_receiving_quantity,
            total_quantity
        FROM inventory_snapshots
        WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM inventory_snapshots)
        ORDER BY total_quantity DESC
        LIMIT 20
    """)
    
    details = cur.fetchall()
    print(f"  Showing top 20 ASINs by total inventory (Latest date: {details[0]['snapshot_date'] if details else 'N/A'})")
    print()
    
    for row in details:
        inbound_total = (row['inbound_working_quantity'] or 0) + \
                       (row['inbound_shipped_quantity'] or 0) + \
                       (row['inbound_receiving_quantity'] or 0)
        
        print(f"  ASIN: {row['asin'] or 'N/A':13s} | "
              f"SKU: {(row['sku'] or 'N/A')[:20]:20s} | "
              f"Available: {int(row['available_quantity'] or 0):4d} | "
              f"Reserved: {int(row['reserved_quantity'] or 0):4d} | "
              f"Inbound: {int(inbound_total):4d} | "
              f"Total: {int(row['total_quantity'] or 0):5d}")
    
    print()
    print("=" * 100)
    print("NEXT STEPS TO UPDATE INVENTORY:")
    print("=" * 100)
    print()
    
    if latest_date:
        days_behind = (date.today() - latest_date).days
        print(f"[ACTION NEEDED] Your inventory data is {days_behind} days behind!")
        print()
    
    print("Download these reports from Amazon Seller Central:")
    print()
    print("1. FBA INVENTORY REPORT")
    print("   Path: Reports > Fulfillment > Amazon Fulfilled Inventory")
    print("   Date: Today")
    print("   Format: CSV/TSV")
    print("   Import: python importers/import_fba_inventory_report.py <file.csv>")
    print()
    print("2. AWD INVENTORY REPORT (if applicable)")
    print("   Path: Reports > AWD Inventory")
    print("   Date: Today")
    print("   Format: CSV")
    print("   Import: python importers/import_awd_inventory_report.py <file.csv>")
    print()
    
    cur.close()
    conn.close()

if __name__ == '__main__':
    check_inventory_status()

