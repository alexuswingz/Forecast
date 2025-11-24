import sqlite3

conn = sqlite3.connect("kpi_metrics.db")
cur = conn.cursor()
cur.execute("SELECT asin, product_name, size FROM products WHERE LOWER(product_name) LIKE '%hydrangea%'")
rows = cur.fetchall()
print(rows)
conn.close()

