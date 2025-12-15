import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    database=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD')
)
cur = conn.cursor(cursor_factory=RealDictCursor)

print("=" * 80)
print("CHILD TRAFFIC METRICS STATUS")
print("=" * 80)

# Check date range
cur.execute("""
    SELECT 
        MIN(date) as earliest,
        MAX(date) as latest,
        COUNT(*) as total_rows,
        COUNT(DISTINCT child_asin) as unique_asins
    FROM child_traffic_metrics
""")

summary = cur.fetchone()
print(f"\nOverall Summary:")
print(f"  Date range: {summary['earliest']} to {summary['latest']}")
print(f"  Total rows: {summary['total_rows']:,}")
print(f"  Unique ASINs: {summary['unique_asins']}")

# Check Nov 15-28 specifically
cur.execute("""
    SELECT date, COUNT(*) as rows, COUNT(DISTINCT child_asin) as asins
    FROM child_traffic_metrics
    WHERE date >= '2025-11-15' AND date <= '2025-11-28'
    GROUP BY date
    ORDER BY date
""")

print(f"\nNov 15-28 Data (from SP-API):")
rows = cur.fetchall()
if rows:
    for row in rows:
        print(f"  {row['date']}: {row['rows']} rows, {row['asins']} ASINs")
else:
    print("  No data found for Nov 15-28!")

# Check sample ASIN
cur.execute("""
    SELECT date, sessions, units_ordered, ordered_product_sales, conversion_rate
    FROM child_traffic_metrics
    WHERE child_asin = 'B0BRTK1P8Z'
    AND date >= '2025-11-15'
    ORDER BY date DESC
    LIMIT 10
""")

print(f"\nSample ASIN (Monstera B0BRTK1P8Z) - Nov 15+:")
rows = cur.fetchall()
if rows:
    for row in rows:
        print(f"  {row['date']}: Sessions={row['sessions']}, Units={row['units_ordered']}, Sales=${row['ordered_product_sales']:.2f}, Conv={row['conversion_rate']:.2f}%")
else:
    print("  No data found!")

cur.close()
conn.close()










