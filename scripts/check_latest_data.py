"""
Check the latest data dates across all tables
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, text
from config import Config
from datetime import datetime

def check_latest_data():
    """Check latest dates for all data tables"""
    
    print("=" * 80)
    print("CHECKING LATEST DATA IN DATABASE")
    print("=" * 80)
    print(f"Date checked: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    engine = create_engine(Config.DATABASE_URL)
    
    # Tables to check with their date columns
    tables = {
        'order_items': 'order_date',
        'ad_product_performance': 'date',
        'child_traffic': 'date',
        'inventory_snapshots': 'snapshot_date',
        'daily_product_metrics': 'date'
    }
    
    with engine.connect() as conn:
        for table_name, date_col in tables.items():
            try:
                print(f"\n{table_name.upper().replace('_', ' ')}:")
                print("-" * 80)
                
                # Get date range and count
                result = conn.execute(text(f"""
                    SELECT 
                        MIN({date_col}) as earliest_date,
                        MAX({date_col}) as latest_date,
                        COUNT(*) as total_rows,
                        COUNT(DISTINCT {date_col}) as unique_dates
                    FROM {table_name}
                """))
                
                row = result.fetchone()
                
                if row:
                    print(f"  Earliest date:  {row[0]}")
                    print(f"  Latest date:    {row[1]}")
                    print(f"  Total rows:     {row[2]:,}")
                    print(f"  Unique dates:   {row[3]:,}")
                    
                    # Calculate days behind
                    if row[1]:
                        latest = row[1]
                        today = datetime.now().date()
                        if hasattr(latest, 'date'):
                            latest = latest.date()
                        days_behind = (today - latest).days
                        
                        if days_behind == 0:
                            status = "[OK] UP TO DATE"
                        elif days_behind == 1:
                            status = "[WARN] 1 DAY BEHIND"
                        else:
                            status = f"[ALERT] {days_behind} DAYS BEHIND"
                        
                        print(f"  Status:         {status}")
                
            except Exception as e:
                print(f"  [ERROR]: {str(e)}")
    
    # Check specific ASINs for completeness
    print("\n" + "=" * 80)
    print("SAMPLE ASIN CHECK (Monstera B0BRTK1P8Z)")
    print("=" * 80)
    
    with engine.connect() as conn:
        asin = 'B0BRTK1P8Z'
        
        # Check daily_product_metrics for this ASIN
        result = conn.execute(text("""
            SELECT 
                MIN(date) as earliest,
                MAX(date) as latest,
                COUNT(*) as days_of_data
            FROM daily_product_metrics
            WHERE asin = :asin
        """), {'asin': asin})
        
        row = result.fetchone()
        if row:
            print(f"\nDaily Product Metrics:")
            print(f"  Data range: {row[0]} to {row[1]}")
            print(f"  Days of data: {row[2]:,}")
    
    print("\n" + "=" * 80)
    print("RECOMMENDATION:")
    print("=" * 80)
    
    today = datetime.now().date()
    print(f"\nToday's date: {today}")
    print("\nTo align data to today, you need to:")
    print("  1. Pull latest Business Reports (up to yesterday)")
    print("  2. Pull latest Ads data (up to yesterday)")
    print("  3. Pull latest Traffic data (child_traffic)")
    print("  4. Run: python scripts/update_daily_metrics.py")
    print("\nNote: Amazon data typically has 1-2 day delay")
    print()

if __name__ == '__main__':
    check_latest_data()

