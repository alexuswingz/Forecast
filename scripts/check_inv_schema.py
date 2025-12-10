import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    database=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    port=int(os.getenv('DB_PORT', 5432))
)
cur = conn.cursor(cursor_factory=RealDictCursor)

# Check if table exists
cur.execute("""
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_name = 'inventory_snapshots'
    )
""")
exists = cur.fetchone()['exists']

if exists:
    cur.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'inventory_snapshots' 
        ORDER BY ordinal_position
    """)
    cols = cur.fetchall()
    print('Columns in inventory_snapshots:')
    for c in cols:
        print(f"  {c['column_name']:30s} {c['data_type']}")
    
    # Check row count
    cur.execute("SELECT COUNT(*) as count FROM inventory_snapshots")
    count = cur.fetchone()['count']
    print(f"\nTotal rows: {count:,}")
    
    if count > 0:
        cur.execute("SELECT MIN(snapshot_date) as min_date, MAX(snapshot_date) as max_date FROM inventory_snapshots")
        dates = cur.fetchone()
        print(f"Date range: {dates['min_date']} to {dates['max_date']}")
else:
    print("Table 'inventory_snapshots' does not exist!")

cur.close()
conn.close()




