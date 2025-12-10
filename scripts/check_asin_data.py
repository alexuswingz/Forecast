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

asin = 'B0D4JHN9KK'

print("=" * 80)
print(f"DATA CHECK FOR {asin}")
print("=" * 80)

# Check child_traffic_metrics
print("\n[1] CHILD TRAFFIC METRICS (Raw Data):")
cur.execute("""
    SELECT date, sessions, units_ordered, ordered_product_sales 
    FROM child_traffic_metrics 
    WHERE child_asin = %s AND date >= '2025-11-15' AND date <= '2025-11-28'
    ORDER BY date
""", (asin,))

rows = cur.fetchall()
if rows:
    for r in rows:
        print(f"  {r['date']}: Units={r['units_ordered']}, Sales=${r['ordered_product_sales']:.2f}, Sessions={r['sessions']}")
else:
    print("  No data found!")

# Check daily_product_metrics
print("\n[2] DAILY PRODUCT METRICS (Aggregated):")
cur.execute("""
    SELECT date, units_sold, sales_amount, sessions 
    FROM daily_product_metrics 
    WHERE asin = %s AND date >= '2025-11-15' AND date <= '2025-11-28'
    ORDER BY date
""", (asin,))

rows = cur.fetchall()
if rows:
    for r in rows:
        print(f"  {r['date']}: Units={r['units_sold']}, Sales=${r['sales_amount']:.2f}, Sessions={r['sessions']}")
else:
    print("  No data found!")

cur.close()
conn.close()




