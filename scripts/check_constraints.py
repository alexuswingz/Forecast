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
    SELECT constraint_name, constraint_type 
    FROM information_schema.table_constraints 
    WHERE table_name = 'inventory_snapshots'
""")

print("Constraints on inventory_snapshots:")
for r in cur.fetchall():
    print(f"  {r['constraint_name']:40s} {r['constraint_type']}")

cur.close()
conn.close()







