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
    WITH hyd AS (
        SELECT asin
        FROM products
        WHERE LOWER(product_name) LIKE '%hydrangea%'
    )
    SELECT asin, MIN(order_date), MAX(order_date), COUNT(*)
    FROM order_items
    WHERE order_date >= '2025-01-01'
      AND asin = 'B0C73TDZCQ'
    GROUP BY asin
    """
)

with engine.connect() as conn:
    print(list(conn.execute(query)))

