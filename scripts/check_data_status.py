"""
Quick check of latest data dates
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, text
from config import Config
from datetime import datetime, date

def check_data():
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    # Connect directly with RealDictCursor
    conn = psycopg2.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        database=Config.DB_NAME,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        cursor_factory=RealDictCursor
    )
    cursor = conn.cursor()
    
    today = date.today()
    
    print("="*80)
    print(f"DATA STATUS CHECK - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    print(f"\nToday's date: {today}\n")
    
    try:
        # Check daily_product_metrics (main aggregated table)
        print("[1] DAILY PRODUCT METRICS (Main Dashboard Data)")
        print("-"*80)
        cursor.execute("""
            SELECT 
                MIN(date) as earliest,
                MAX(date) as latest,
                COUNT(DISTINCT date) as days,
                COUNT(DISTINCT asin) as asins,
                COUNT(*) as total_rows
            FROM daily_product_metrics
        """)
        row = cursor.fetchone()
        latest_date = row['latest']
        days_behind = (today - latest_date).days if latest_date else 999
        
        print(f"  Date range:     {row['earliest']} to {row['latest']}")
        print(f"  Days of data:   {row['days']:,}")
        print(f"  Total ASINs:    {row['asins']:,}")
        print(f"  Total rows:     {row['total_rows']:,}")
        print(f"  Days behind:    {days_behind} days")
        print(f"  Status:         {'[OK] UP TO DATE' if days_behind <= 1 else f'[ALERT] {days_behind} DAYS BEHIND'}")
        
        # Check order_items
        print(f"\n[2] ORDER ITEMS (Fulfillment Data)")
        print("-"*80)
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT asin) as asins
            FROM order_items
            WHERE order_date::date >= (CURRENT_DATE - INTERVAL '7 days')
        """)
        row = cursor.fetchone()
        print(f"  Last 7 days:    {row['total']:,} orders")
        print(f"  Unique ASINs:   {row['asins']:,}")
        
        # Check ads data
        print(f"\n[3] AD PERFORMANCE DATA")
        print("-"*80)
        cursor.execute("""
            SELECT 
                MIN(report_date) as earliest,
                MAX(report_date) as latest,
                COUNT(*) as total
            FROM ad_product_performance
        """)
        row = cursor.fetchone()
        if row['latest']:
            ads_behind = (today - row['latest']).days
            print(f"  Date range:     {row['earliest']} to {row['latest']}")
            print(f"  Total rows:     {row['total']:,}")
            print(f"  Days behind:    {ads_behind} days")
        else:
            print(f"  No data")
        
        # Check traffic data
        print(f"\n[4] TRAFFIC DATA (Sessions & Conversion)")
        print("-"*80)
        cursor.execute("""
            SELECT 
                MIN(date) as earliest,
                MAX(date) as latest,
                COUNT(*) as total
            FROM child_traffic_metrics
        """)
        row = cursor.fetchone()
        if row['latest']:
            traffic_behind = (today - row['latest']).days
            print(f"  Date range:     {row['earliest']} to {row['latest']}")
            print(f"  Total rows:     {row['total']:,}")
            print(f"  Days behind:    {traffic_behind} days")
        else:
            print(f"  No data")
        
        # Sample check
        print(f"\n[5] SAMPLE ASIN CHECK (Monstera B0BRTK1P8Z)")
        print("-"*80)
        cursor.execute("""
            SELECT 
                date,
                sales_amount,
                units_sold,
                sessions,
                ad_spend
            FROM daily_product_metrics
            WHERE asin = 'B0BRTK1P8Z'
            ORDER BY date DESC
            LIMIT 5
        """)
        rows = cursor.fetchall()
        if rows:
            print(f"  Last 5 days:")
            for r in rows:
                print(f"    {r['date']}: Sales=${r['sales_amount']:.2f}, Units={r['units_sold']}, Sessions={r['sessions']}, AdSpend=${r['ad_spend']:.2f}")
        else:
            print(f"  No data for this ASIN")
    
    finally:
        cursor.close()
        conn.close()
    
    print("\n" + "="*80)
    print("NEXT STEPS TO UPDATE DATA:")
    print("="*80)
    if days_behind > 1:
        print(f"\n[ACTION NEEDED] Your data is {days_behind} days behind!")
        print("\n1. Import latest data:")
        print("   - Business Reports (fulfillment data)")
        print("   - Ads Reports (ad performance)")
        print("   - Traffic Reports (child traffic)")
        print("\n2. Run aggregation:")
        print("   python scripts/update_daily_metrics.py")
    else:
        print("\n[OK] Your data is up to date!")
        print("Run daily: python scripts/update_daily_metrics.py")
    print()

if __name__ == '__main__':
    check_data()

