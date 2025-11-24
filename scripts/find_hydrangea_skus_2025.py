import csv
import glob
from pathlib import Path

folder = Path("Fulfillment reports")
files = sorted(folder.glob("*.csv"))

hyd_rows = []
for path in files:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        headers = [h.strip() for h in reader.fieldnames or []]
        if "SKU" not in [h.upper() for h in headers] and "merchant sku" not in " ".join(
            headers
        ).lower():
            continue
        for row in reader:
            sku = (row.get("Merchant SKU") or row.get("merchant_sku") or "").upper()
            title = (row.get("Title") or row.get("title") or "").lower()
            asin = (row.get("ASIN") or row.get("asin") or "").strip()
            if "hydrangea" in title or "HYDR" in sku:
                hyd_rows.append((path.name, sku, asin, row.get("Item Price")))
                if len(hyd_rows) >= 5:
                    break
    if hyd_rows:
        break

for row in hyd_rows:
    print(row)
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import Config

engine = create_engine(Config.DATABASE_URL)
query = text(
    """
    SELECT DISTINCT sku
    FROM order_items
    WHERE order_date >= '2025-01-01'
      AND UPPER(sku) LIKE '%HYDR%'
    LIMIT 50
    """
)

with engine.connect() as conn:
    for row in conn.execute(query):
        print(row[0])

