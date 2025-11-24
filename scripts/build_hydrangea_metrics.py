import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import Config

# SQLite vs PostgreSQL date grouping
if Config.USE_SQLITE:
    WEEK_START_EXPR = "date(order_date, 'weekday 0', '-6 days')"
    TRAFFIC_WEEK_START_EXPR = "date(date, 'weekday 0', '-6 days')"
    AD_WEEK_START_EXPR = "date(report_date, 'weekday 0', '-6 days')"
    INV_WEEK_START_EXPR = "date(snapshot_date, 'weekday 0', '-6 days')"
else:
    WEEK_START_EXPR = "date_trunc('week', (order_date)::timestamptz)::date"
    TRAFFIC_WEEK_START_EXPR = "date_trunc('week', date)::date"
    AD_WEEK_START_EXPR = "date_trunc('week', report_date)::date"
    INV_WEEK_START_EXPR = "date_trunc('week', snapshot_date)::date"

QUERY = text(
    f"""
    WITH hyd AS (
        SELECT DISTINCT asin, UPPER(TRIM(sku)) AS sku
        FROM product_cogs
        WHERE LOWER(product_name) LIKE '%hydrangea%'
        UNION
        SELECT DISTINCT asin, UPPER(TRIM(sku)) AS sku
        FROM products
        WHERE LOWER(product_name) LIKE '%hydrangea%'
    ), orders AS (
        SELECT
            {WEEK_START_EXPR} AS week_start,
            SUM(quantity) AS units,
            SUM(item_price) AS sales
        FROM order_items
        WHERE order_date IS NOT NULL
          AND (
                asin IN (SELECT asin FROM hyd WHERE asin IS NOT NULL)
                OR UPPER(sku) IN (SELECT sku FROM hyd WHERE sku IS NOT NULL)
              )
        GROUP BY 1
    ), traffic AS (
        SELECT
            {TRAFFIC_WEEK_START_EXPR} AS week_start,
            SUM(sessions) AS sessions,
            SUM(units_ordered) AS traffic_units,
            AVG(CASE WHEN conversion_rate IS NOT NULL THEN conversion_rate ELSE NULL END) AS avg_organic_conversion_rate
        FROM child_traffic_metrics
        WHERE child_asin IN (SELECT asin FROM hyd WHERE asin IS NOT NULL)
        GROUP BY 1
    ), ads AS (
        SELECT
            {AD_WEEK_START_EXPR} AS week_start,
            SUM(impressions) AS impressions,
            SUM(clicks) AS clicks,
            SUM(spend) AS ad_spend,
            SUM(COALESCE(sales_14d, 0)) AS ad_sales,
            SUM(COALESCE(orders_14d, 0)) AS ad_orders,
            SUM(COALESCE(units_14d, 0)) AS ad_units,
            AVG(CASE WHEN conversion_rate IS NOT NULL THEN conversion_rate ELSE NULL END) AS avg_conversion_rate
        FROM ad_product_performance
        WHERE (
                advertised_asin IN (SELECT asin FROM hyd WHERE asin IS NOT NULL)
                OR UPPER(sku) IN (SELECT sku FROM hyd WHERE sku IS NOT NULL)
              )
        GROUP BY 1
    ), inv AS (
        SELECT
            {INV_WEEK_START_EXPR} AS week_start,
            SUM(COALESCE(total_quantity, 0)) AS total_inventory,
            SUM(COALESCE(available_quantity, 0)) AS available_inventory,
            SUM(COALESCE(reserved_quantity, 0)) AS reserved_inventory,
            SUM(COALESCE(inbound_working_quantity, 0)) AS inbound_working,
            SUM(COALESCE(inbound_shipped_quantity, 0)) AS inbound_shipped,
            SUM(COALESCE(inbound_receiving_quantity, 0)) AS inbound_receiving,
            SUM(COALESCE(research_quantity, 0)) AS research_inventory,
            SUM(CASE WHEN fulfillment_program = 'FBA' THEN COALESCE(total_quantity, 0) ELSE 0 END) AS fba_inventory,
            SUM(CASE WHEN fulfillment_program = 'AWD' THEN COALESCE(total_quantity, 0) ELSE 0 END) AS awd_inventory
        FROM inventory_snapshots
        WHERE (
                asin IN (SELECT asin FROM hyd WHERE asin IS NOT NULL)
                OR UPPER(sku) IN (SELECT sku FROM hyd WHERE sku IS NOT NULL)
              )
        GROUP BY 1
    )
    SELECT
        o.week_start,
        o.units,
        o.sales,
        t.sessions,
        t.avg_organic_conversion_rate,
        a.impressions,
        a.clicks,
        a.ad_spend,
        a.ad_sales,
        a.ad_orders,
        a.ad_units,
        a.avg_conversion_rate AS ad_conversion_rate,
        i.total_inventory,
        i.available_inventory,
        i.reserved_inventory,
        i.inbound_working,
        i.inbound_shipped,
        i.inbound_receiving,
        i.research_inventory,
        i.fba_inventory,
        i.awd_inventory
    FROM orders o
    LEFT JOIN traffic t ON t.week_start = o.week_start
    LEFT JOIN ads a ON a.week_start = o.week_start
    LEFT JOIN inv i ON i.week_start = o.week_start
    ORDER BY o.week_start
    """
)


def main():
    engine = create_engine(Config.DATABASE_URL)
    with engine.connect() as conn:
        rows = conn.execute(QUERY).fetchall()
    df = pd.DataFrame(
        rows,
        columns=[
            "week_start",
            "units",
            "sales",
            "sessions",
            "organic_conversion_rate",
            "ad_impressions",
            "ad_clicks",
            "ad_spend",
            "ad_sales",
            "ad_orders",
            "ad_units",
            "ad_conversion_rate",
            "total_inventory",
            "available_inventory",
            "reserved_inventory",
            "inbound_working",
            "inbound_shipped",
            "inbound_receiving",
            "research_inventory",
            "fba_inventory",
            "awd_inventory",
        ],
    )
    df["ad_cpc"] = df["ad_spend"] / df["ad_clicks"]
    df.loc[df["ad_clicks"] == 0, "ad_cpc"] = None
    df["tacos"] = df["ad_spend"] / df["sales"]
    df.loc[df["sales"] == 0, "tacos"] = None
    df["organic_sales_pct"] = (df["sales"] - df["ad_sales"]) / df["sales"]
    df.loc[df["sales"] == 0, "organic_sales_pct"] = None

    output = Path("hydrangea_weekly_metrics_with_conversion.csv")
    df.to_csv(output, index=False)
    print(f"Saved {len(df)} rows to {output}")


if __name__ == "__main__":
    main()

