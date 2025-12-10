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

# Check columns in inventory_snapshots
cur.execute("""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'inventory_snapshots'
    ORDER BY ordinal_position
""")

print("Columns in inventory_snapshots:")
for row in cur.fetchall():
    print(f"  {row['column_name']:30s} | {row['data_type']:20s} | NULL: {row['is_nullable']}")

# Sample data
print("\nSample inventory data:")
cur.execute("SELECT * FROM inventory_snapshots LIMIT 3")
for row in cur.fetchall():
    print(f"  {dict(row)}")

cur.close()
conn.close()




