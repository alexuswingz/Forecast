"""
Check data accuracy between daily_product_metrics and raw tables
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, text
from config import Config

def check_data():
    """Compare aggregated data with raw data"""
    
    print("=" * 80)
    print("Data Accuracy Check")
    print("=" * 80)
    
    # Force RDS connection
    rds_url = f"postgresql://{Config.DB_USER}:{Config.DB_PASSWORD}@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}"
    engine = create_engine(rds_url)
    
    with engine.connect() as conn:
        # Test ASIN for comparison
        test_asin = 'B0BRTK1P8Z'
        
        print(f"\nTesting ASIN: {test_asin}")
        print("-" * 80)
        
        # Get last 30 days from RAW order_items
        print("\n1. RAW DATA (order_items) - Last 30 days:")
        result = conn.execute(text("""
            SELECT 
                COUNT(*) as row_count,
                SUM(quantity) as total_units,
                SUM(item_price * quantity) as total_sales
            FROM order_items
            WHERE asin = :asin
            AND order_date::timestamp >= CURRENT_DATE - INTERVAL '30 days'
        """), {'asin': test_asin})
        
        raw = result.fetchone()
        print(f"  Rows: {raw[0]:,}")
        print(f"  Total Units: {raw[1]:,}")
        print(f"  Total Sales: ${raw[2]:,.2f}")
        
        # Get last 30 days from AGGREGATED daily_product_metrics
        print("\n2. AGGREGATED DATA (daily_product_metrics) - Last 30 days:")
        result = conn.execute(text("""
            SELECT 
                COUNT(*) as row_count,
                SUM(units_sold) as total_units,
                SUM(sales_amount) as total_sales
            FROM daily_product_metrics
            WHERE asin = :asin
            AND date >= CURRENT_DATE - INTERVAL '30 days'
        """), {'asin': test_asin})
        
        agg = result.fetchone()
        print(f"  Rows: {agg[0]:,}")
        print(f"  Total Units: {agg[1]:,}")
        print(f"  Total Sales: ${agg[2]:,.2f}")
        
        # Compare
        print("\n3. COMPARISON:")
        if raw[1] and agg[1]:
            units_diff = int(raw[1]) - int(agg[1])
            sales_diff = float(raw[2]) - float(agg[2])
            units_pct = (units_diff / raw[1] * 100) if raw[1] > 0 else 0
            sales_pct = (sales_diff / raw[2] * 100) if raw[2] > 0 else 0
            
            print(f"  Units difference: {units_diff:,} ({units_pct:+.2f}%)")
            print(f"  Sales difference: ${sales_diff:,.2f} ({sales_pct:+.2f}%)")
            
            if abs(units_pct) > 1 or abs(sales_pct) > 1:
                print("\n  [WARNING] Significant difference found!")
            else:
                print("\n  [OK] Data matches within 1%")
        
        # Check sample dates
        print("\n4. SAMPLE DATE COMPARISON:")
        result = conn.execute(text("""
            SELECT 
                DATE(order_date::timestamp) as date,
                SUM(quantity) as units,
                SUM(item_price * quantity) as sales
            FROM order_items
            WHERE asin = :asin
            AND order_date::timestamp >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY DATE(order_date::timestamp)
            ORDER BY date DESC
            LIMIT 5
        """), {'asin': test_asin})
        
        raw_dates = {row[0]: (row[1], row[2]) for row in result.fetchall()}
        
        result = conn.execute(text("""
            SELECT 
                date,
                units_sold,
                sales_amount
            FROM daily_product_metrics
            WHERE asin = :asin
            AND date >= CURRENT_DATE - INTERVAL '7 days'
            ORDER BY date DESC
            LIMIT 5
        """), {'asin': test_asin})
        
        agg_dates = {row[0]: (row[1], row[2]) for row in result.fetchall()}
        
        print("\n  Last 5 days comparison:")
        print("  " + "-" * 76)
        print(f"  {'Date':12s} | {'RAW Units':>10s} | {'AGG Units':>10s} | {'RAW Sales':>12s} | {'AGG Sales':>12s}")
        print("  " + "-" * 76)
        
        all_dates = sorted(set(raw_dates.keys()) | set(agg_dates.keys()), reverse=True)[:5]
        for date in all_dates:
            raw_u, raw_s = raw_dates.get(date, (0, 0))
            agg_u, agg_s = agg_dates.get(date, (0, 0))
            raw_u, raw_s, agg_u, agg_s = int(raw_u), float(raw_s), int(agg_u), float(agg_s)
            match = "OK" if raw_u == agg_u and abs(raw_s - agg_s) < 0.01 else "DIFF"
            print(f"  {str(date):12s} | {raw_u:>10,} | {agg_u:>10,} | ${raw_s:>11,.2f} | ${agg_s:>11,.2f} [{match}]")
        
        # Check for NULL dates in order_items
        print("\n5. DATA QUALITY CHECK:")
        result = conn.execute(text("""
            SELECT COUNT(*) as null_dates
            FROM order_items
            WHERE asin = :asin
            AND (order_date IS NULL OR order_date = '')
        """), {'asin': test_asin})
        
        null_count = result.fetchone()[0]
        if null_count > 0:
            print(f"  [WARNING] Found {null_count:,} rows with NULL/empty order_date")
        else:
            print("  [OK] No NULL order_date values")
        
        # Check overall coverage
        print("\n6. OVERALL COVERAGE:")
        result = conn.execute(text("""
            SELECT 
                COUNT(DISTINCT asin) as asin_count,
                MIN(date) as min_date,
                MAX(date) as max_date,
                COUNT(*) as total_rows,
                SUM(units_sold) as total_units,
                SUM(sales_amount) as total_sales
            FROM daily_product_metrics
        """))
        
        stats = result.fetchone()
        print(f"  ASINs: {stats[0]:,}")
        print(f"  Date range: {stats[1]} to {stats[2]}")
        print(f"  Total rows: {stats[3]:,}")
        print(f"  Total units (all time): {stats[4]:,}")
        print(f"  Total sales (all time): ${stats[5]:,.2f}")
        
    print("\n" + "=" * 80)

if __name__ == '__main__':
    check_data()

