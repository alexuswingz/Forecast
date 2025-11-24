import sys
from pathlib import Path

from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import Config

QUERY = text(
    """
    WITH hyd AS (
        SELECT asin, UPPER(TRIM(sku)) AS sku
        FROM product_cogs
        WHERE LOWER(product_name) LIKE :kw
    ), orders AS (
        SELECT
            (order_date)::timestamptz AS order_ts,
            quantity,
            item_price
        FROM order_items
        WHERE order_date IS NOT NULL
          AND (
                asin IN (SELECT asin FROM hyd WHERE asin IS NOT NULL)
                OR UPPER(sku) IN (SELECT sku FROM hyd WHERE sku IS NOT NULL)
              )
    )
    SELECT
        date_trunc('week', order_ts)::date AS week_start,
        SUM(quantity) AS units,
        SUM(item_price) AS sales
    FROM orders
    GROUP BY 1
    ORDER BY 1
    """
)


def main():
    engine = create_engine(Config.DATABASE_URL)
    with engine.connect() as conn:
        rows = conn.execute(QUERY, {"kw": "%hydrangea%"}).fetchall()
    for week_start, units, sales in rows:
        print(f"{week_start}: units={int(units or 0)}, sales=${sales or 0:,.2f}")


if __name__ == "__main__":
    main()

