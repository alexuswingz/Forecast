"""
Load product master data and COGS into SQLite.

Sources:
- Data Bing Bong KPIs_Metrics (2).xlsx -> sheet "ChildProductNames"
- Data Bing Bong KPIs_Metrics - COGS.csv
"""

import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = "kpi_metrics.db"
PRODUCTS_SHEET = "Data Bing Bong KPIs_Metrics (2).xlsx"
COGS_CSV = r"C:\Users\User\OneDrive\Desktop\ETO NA\data\Data Bing Bong KPIs_Metrics - COGS.csv"


def clean_currency(value):
    if value in (None, "", " ", "nan", "NaN"):
        return None
    if isinstance(value, str):
        value = value.replace("$", "").replace(",", "")
    try:
        return float(value)
    except Exception:
        return None


def load_products(conn: sqlite3.Connection):
    print("[INFO] Loading ChildProductNames sheet...")
    df = pd.read_excel(PRODUCTS_SHEET, sheet_name="ChildProductNames", header=1)
    df = df.dropna(subset=["Child ASIN"])

    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            asin TEXT PRIMARY KEY,
            parent_asin TEXT,
            sku TEXT,
            brand TEXT,
            category TEXT,
            product_name TEXT,
            size TEXT
        )
        """
    )

    rows = []
    for _, row in df.iterrows():
        asin = str(row["Child ASIN"]).strip()
        if not asin or asin.lower() == "nan":
            continue
        parent = str(row.get("Parent ASIN") or "").strip() or None
        rows.append(
            (
                asin,
                parent,
                None,
                row.get("Brand"),
                row.get("Category"),
                row.get("Product Name"),
                row.get("Size"),
            )
        )

    cur.executemany(
        """
        INSERT INTO products (asin, parent_asin, sku, brand, category, product_name, size)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(asin) DO UPDATE SET
            parent_asin=excluded.parent_asin,
            sku=coalesce(products.sku, excluded.sku),
            brand=excluded.brand,
            category=excluded.category,
            product_name=excluded.product_name,
            size=excluded.size
        """,
        rows,
    )
    conn.commit()
    print(f"[SUCCESS] Upserted {len(rows)} product records")


def load_cogs(conn: sqlite3.Connection):
    csv_path = Path(COGS_CSV)
    if not csv_path.exists():
        print(f"[WARN] COGS CSV not found: {csv_path}")
        return
    print(f"[INFO] Loading COGS from {csv_path}")
    df = pd.read_csv(csv_path)
    df = df.dropna(subset=["ASIN"])

    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS product_cogs (
            asin TEXT PRIMARY KEY,
            sku TEXT,
            brand TEXT,
            category TEXT,
            product_name TEXT,
            size TEXT,
            cogs_amount REAL,
            currency TEXT,
            source TEXT
        )
        """
    )

    records = []
    for _, row in df.iterrows():
        asin = str(row["ASIN"]).strip()
        if not asin or asin.lower() == "nan":
            continue
        amount = clean_currency(row.get("Prep") or row.get("COGS") or row.get("Amount"))
        records.append(
            (
                asin,
                row.get("Sku"),
                row.get("Brand"),
                row.get("Category"),
                row.get("Product"),
                row.get("Size"),
                amount,
                "USD",
                row.get("Stats"),
            )
        )

    cur.executemany(
        """
        INSERT INTO product_cogs (
            asin, sku, brand, category, product_name, size,
            cogs_amount, currency, source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(asin) DO UPDATE SET
            sku=excluded.sku,
            brand=excluded.brand,
            category=excluded.category,
            product_name=excluded.product_name,
            size=excluded.size,
            cogs_amount=excluded.cogs_amount,
            currency=excluded.currency,
            source=excluded.source
        """,
        records,
    )
    conn.commit()
    print(f"[SUCCESS] Upserted {len(records)} COGS records")


def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        load_products(conn)
        load_cogs(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()

