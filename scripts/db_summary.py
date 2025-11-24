import sqlite3

conn = sqlite3.connect("kpi_metrics.db")
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = sorted(row[0] for row in cur.fetchall())
for table in tables:
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    count = cur.fetchone()[0]
    print(f"{table}: {count}")
conn.close()



