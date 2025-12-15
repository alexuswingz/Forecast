import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    database=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD')
)
cur = conn.cursor()

cur.execute("""
    SELECT COUNT(*) 
    FROM inventory_snapshots 
    WHERE fulfillment_program = 'AWD' 
    AND snapshot_date >= '2025-11-12' 
    AND snapshot_date <= '2025-11-27'
""")
count = cur.fetchone()[0]

print(f"AWD records for Nov 12-27: {count}")
print(f"Expected: ~1071 records")
print(f"Progress: {count}/1071 ({count/1071*100:.1f}%)" if count > 0 else "Starting...")

cur.close()
conn.close()










