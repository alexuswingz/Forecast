"""
Update RDS database with CORRECT units sold data from Excel
ALL PRODUCTS, ALL WEEKS from the Excel file
Excel data is the source of truth from management
"""
import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch
from config import Config
from datetime import datetime, timedelta

print("="*80)
print("UPDATING RDS DATABASE WITH CORRECT EXCEL DATA")
print("="*80)
print("Source: Alexus Units Sold Data Request.xlsx")
print("Scope: ALL PRODUCTS, ALL WEEKS")
print("="*80)

# Read Excel
excel_file = "Alexus Units Sold Data Request.xlsx"
print(f"\nReading {excel_file}...")
df = pd.read_excel(excel_file, sheet_name=0, header=1)

print(f"Excel shape: {df.shape}")

metadata_cols = ['Seller ACT', 'Brand', 'Sku', 'Product', 'Size', 'Formula', 'ASIN']

# Get all ASINs
excel_asins = df['ASIN'].dropna().unique().tolist()
print(f"Total products: {len(excel_asins)}")

# Parse ALL week columns from Excel
# Excel weeks end on Saturday, need to convert to Sunday for RDS
all_weeks = []
for col in df.columns:
    if col not in metadata_cols and isinstance(col, datetime):
        week_date_saturday = col.date()
        # Convert Saturday to Sunday (RDS uses Sunday as week end)
        week_date_sunday = week_date_saturday + timedelta(days=1)
        all_weeks.append({
            'excel_col': col,
            'saturday': week_date_saturday,
            'sunday': week_date_sunday
        })

all_weeks = sorted(all_weeks, key=lambda x: x['sunday'])

if all_weeks:
    print(f"Total weeks: {len(all_weeks)}")
    print(f"Date range: {all_weeks[0]['sunday']} to {all_weeks[-1]['sunday']}")
    print(f"Total comparisons: {len(excel_asins)} products × {len(all_weeks)} weeks = {len(excel_asins) * len(all_weeks):,}")
else:
    print("ERROR: No date columns found in Excel!")
    exit(1)

# Connect to RDS
print(f"\n{'='*80}")
print("Connecting to RDS and fetching current data...")
print(f"{'='*80}")

conn = psycopg2.connect(
    host=Config.DB_HOST,
    port=Config.DB_PORT,
    database=Config.DB_NAME,
    user=Config.DB_USER,
    password=Config.DB_PASSWORD
)
cur = conn.cursor()

# Get ALL RDS data for these ASINs
min_date = all_weeks[0]['sunday'] - timedelta(days=6)  # Week start
max_date = all_weeks[-1]['sunday']

print(f"Fetching RDS data from {min_date} to {max_date}...")

cur.execute("""
    SELECT 
        asin,
        DATE_TRUNC('week', date)::date + 6 as week_end,
        SUM(units_sold) as total_units_sold
    FROM daily_product_metrics
    WHERE asin = ANY(%s)
    AND date >= %s
    AND date <= %s
    GROUP BY asin, DATE_TRUNC('week', date)
""", (excel_asins, min_date, max_date))

rds_data = cur.fetchall()
rds_dict = {(row[0], row[1]): float(row[2] or 0) for row in rds_data}
print(f"✓ Loaded {len(rds_data)} weekly records from RDS")

# Prepare updates
print(f"\n{'='*80}")
print("Comparing Excel vs RDS and preparing updates...")
print(f"{'='*80}")

updates = []
discrepancies = []
matches = 0

for idx, row in df.iterrows():
    asin = row['ASIN']
    if pd.isna(asin):
        continue
    
    product = row.get('Product', 'Unknown')
    brand = row.get('Brand', 'Unknown')
    
    for week_info in all_weeks:
        excel_col = week_info['excel_col']
        week_end_sunday = week_info['sunday']
        
        # Get Excel value
        excel_units = row[excel_col]
        if pd.isna(excel_units):
            excel_units = 0
        else:
            try:
                excel_units = float(excel_units)
            except (ValueError, TypeError):
                # Skip non-numeric values (headers, text, etc.)
                excel_units = 0
        
        # Get RDS value
        rds_units = rds_dict.get((asin, week_end_sunday), 0.0)
        
        # Check for discrepancy
        if abs(excel_units - rds_units) > 0.1:
            discrepancies.append({
                'asin': asin,
                'product': product,
                'brand': brand,
                'week_end': week_end_sunday,
                'excel': excel_units,
                'rds': rds_units,
                'diff': excel_units - rds_units
            })
            
            # Prepare daily updates (distribute weekly units evenly across 7 days)
            week_start = week_end_sunday - timedelta(days=6)
            daily_units = excel_units / 7.0
            
            for i in range(7):
                date = week_start + timedelta(days=i)
                updates.append((asin, date, round(daily_units, 2)))
        else:
            matches += 1
    
    if (idx + 1) % 50 == 0:
        print(f"Progress: {idx + 1} / {len(df)} products...")

print(f"\n{'='*80}")
print("COMPARISON RESULTS")
print(f"{'='*80}")
print(f"Total comparisons: {len(df) * len(all_weeks):,}")
print(f"Matches (correct): {matches:,}")
print(f"Discrepancies found: {len(discrepancies):,}")
print(f"Daily records to update: {len(updates):,}")

if discrepancies:
    # Save detailed report
    disc_df = pd.DataFrame(discrepancies)
    disc_df.to_csv("ALL_discrepancies_report.csv", index=False)
    print(f"\n✓ Full report saved to: ALL_discrepancies_report.csv")
    
    # Statistics
    print(f"\n{'='*80}")
    print("DISCREPANCY STATISTICS")
    print(f"{'='*80}")
    print(f"Average difference per week: {disc_df['diff'].mean():.1f} units")
    print(f"Total units difference: {disc_df['diff'].sum():.0f} units")
    print(f"Excel < RDS (over-counted): {len(disc_df[disc_df['diff'] < 0]):,} weeks")
    print(f"Excel > RDS (under-counted): {len(disc_df[disc_df['diff'] > 0]):,} weeks")
    print(f"Excel = 0, RDS > 0 (missing): {len(disc_df[(disc_df['excel'] == 0) & (disc_df['rds'] > 0)]):,} weeks")
    
    # Top products affected
    print(f"\nTop 20 products with largest total discrepancies:")
    top_products = disc_df.groupby(['asin', 'product']).agg({
        'diff': 'sum'
    }).sort_values('diff', key=abs, ascending=False).head(20)
    
    print(f"{'ASIN':<15} {'Product':<40} {'Total Diff':>12}")
    print("-" * 70)
    for (asin, product), data in top_products.iterrows():
        product_short = product[:37] + "..." if len(str(product)) > 40 else product
        print(f"{asin:<15} {str(product_short):<40} {data['diff']:>12,.0f}")
    
    # Confirm update
    print(f"\n{'='*80}")
    print("READY TO UPDATE DATABASE")
    print(f"{'='*80}")
    print(f"⚠️  This will update {len(updates):,} daily records")
    print(f"⚠️  This covers {len(set(d['asin'] for d in discrepancies))} products")
    print(f"⚠️  Date range: {all_weeks[0]['sunday']} to {all_weeks[-1]['sunday']}")
    print(f"✓  Forecast will be recalculated based on corrected data")
    
    response = input("\nProceed with database update? Type 'yes' to confirm: ")
    
    if response.lower() == 'yes':
        print(f"\n{'='*80}")
        print("UPDATING DATABASE...")
        print(f"{'='*80}")
        
        # Batch update for efficiency
        batch_size = 1000
        total = len(updates)
        
        for i in range(0, total, batch_size):
            batch = updates[i:i+batch_size]
            
            execute_batch(cur, """
                INSERT INTO daily_product_metrics (asin, date, units_sold)
                VALUES (%s, %s, %s)
                ON CONFLICT (asin, date) 
                DO UPDATE SET 
                    units_sold = EXCLUDED.units_sold, 
                    updated_at = CURRENT_TIMESTAMP
            """, batch, page_size=500)
            
            progress = min(i + batch_size, total)
            pct = 100 * progress // total
            print(f"Progress: {progress:,} / {total:,} ({pct}%)")
        
        conn.commit()
        
        print(f"\n{'='*80}")
        print("✅ DATABASE UPDATE COMPLETE!")
        print(f"{'='*80}")
        print(f"✓ Updated {len(updates):,} daily records")
        print(f"✓ Corrected {len(discrepancies):,} weekly discrepancies")
        print(f"✓ Affected {len(set(d['asin'] for d in discrepancies))} products")
        print(f"✓ Date range: {all_weeks[0]['sunday']} to {all_weeks[-1]['sunday']}")
        
        print(f"\n🎉 Success! The database now has correct units sold data from Excel.")
        print(f"🎯 Your forecasts will now be accurate!")
        
    else:
        print("\n❌ Update cancelled. Database not modified.")
else:
    print(f"\n✅ Amazing! No discrepancies found.")
    print(f"✅ All {len(df) * len(all_weeks):,} data points match perfectly!")
    print(f"✅ Database is already correct.")

cur.close()
conn.close()

print(f"\n{'='*80}")
print("DONE")
print(f"{'='*80}")

