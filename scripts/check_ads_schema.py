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

cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'ad_product_performance' 
    ORDER BY ordinal_position
""")

print("ad_product_performance columns:")
for r in cur.fetchall():
    print(f"  {r['column_name']:30s} {r['data_type']}")

cur.close()
conn.close()




