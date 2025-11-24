"""
Import Amazon Fulfilled Shipments CSV files into SQLite.
Usage:
    python import_fulfillment_shipments.py --folder "Fulfillment reports"
"""

import argparse
from pathlib import Path
from typing import Dict

import pandas as pd
from sqlalchemy import create_engine, text

from config import Config

engine = create_engine(Config.DATABASE_URL)
DIALECT = engine.dialect.name


def parse_float(value) -> float:
    if value in (None, "", " ", "nan", "NaN"):
        return 0.0
    if isinstance(value, str):
        value = value.replace("$", "").replace(",", "")
    try:
        return float(value)
    except Exception:
        return 0.0


def parse_int(value) -> int:
    if value in (None, "", " ", "nan", "NaN"):
        return 0
    try:
        return int(float(value))
    except Exception:
        return 0


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("[^a-z0-9_]", "", regex=True)
    )
    return df


def ensure_table(conn):
    id_column = (
        "INTEGER PRIMARY KEY AUTOINCREMENT"
        if DIALECT == "sqlite"
        else "SERIAL PRIMARY KEY"
    )
    date_type = "TEXT" if DIALECT == "sqlite" else "TIMESTAMPTZ"
    num_type = "REAL" if DIALECT == "sqlite" else "NUMERIC"

    conn.execute(
        text(
            f"""
            CREATE TABLE IF NOT EXISTS order_items (
                id {id_column},
                order_id TEXT,
                order_date {date_type},
                fulfillment_center TEXT,
                asin TEXT,
                sku TEXT,
                quantity INTEGER,
                item_price {num_type},
                item_tax {num_type},
                shipping_fee {num_type},
                shipment_date {date_type},
                report_file TEXT
            )
            """
        )
    )


def load_sku_map(conn) -> Dict[str, str]:
    rows = conn.execute(
        text("SELECT sku, asin FROM product_cogs WHERE sku IS NOT NULL AND asin IS NOT NULL")
    ).fetchall()
    mapping = {}
    for sku, asin in rows:
        sku_key = str(sku).strip().upper()
        if sku_key and asin:
            mapping[sku_key] = asin.strip()
    return mapping


def process_file(conn, path: Path, sku_map: Dict[str, str], chunk_size: int = 50000):
    print(f"[INFO] Importing {path.name}")
    insert_stmt = text(
        """
        INSERT INTO order_items (
            order_id, order_date, fulfillment_center, asin, sku,
            quantity, item_price, item_tax, shipping_fee, shipment_date, report_file
        ) VALUES (
            :order_id, :order_date, :fulfillment_center, :asin, :sku,
            :quantity, :item_price, :item_tax, :shipping_fee, :shipment_date, :report_file
        )
        """
    )
    total_rows = 0
    for chunk in pd.read_csv(path, chunksize=chunk_size):
        chunk = normalize_columns(chunk)
        records = []
        for _, row in chunk.iterrows():
            order_id = row.get("amazon_order_id")
            if not isinstance(order_id, str) or not order_id.strip():
                continue
            sku = row.get("merchant_sku") or row.get("sku")
            sku_norm = str(sku).strip().upper() if isinstance(sku, str) else ""
            asin = sku_map.get(sku_norm)
            quantity = parse_int(row.get("shipped_quantity"))
            
            # Convert pandas NaT/NaN to None for date columns
            order_date = row.get("purchase_date")
            if pd.isna(order_date):
                order_date = None
            shipment_date = row.get("shipment_date")
            if pd.isna(shipment_date):
                shipment_date = None
            
            records.append(
                {
                    "order_id": order_id.strip(),
                    "order_date": order_date,
                    "fulfillment_center": row.get("fc"),
                    "asin": asin,
                    "sku": sku.strip() if isinstance(sku, str) else None,
                    "quantity": quantity,
                    "item_price": parse_float(row.get("item_price")),
                    "item_tax": parse_float(row.get("item_tax")),
                    "shipping_fee": parse_float(row.get("shipping_price")),
                    "shipment_date": shipment_date,
                    "report_file": path.name,
                }
            )
        # Insert in smaller batches to handle high-latency connections
        BATCH_SIZE = 500
        for i in range(0, len(records), BATCH_SIZE):
            batch = records[i:i+BATCH_SIZE]
            if batch:
                conn.execute(insert_stmt, batch)
        total_rows += len(records)
        if records:
            print(f"  - chunk imported: {len(records)} rows")

    print(f"[INFO] Finished {path.name}: {total_rows} rows inserted")


def main():
    parser = argparse.ArgumentParser(description="Import Amazon Fulfilled Shipment reports")
    parser.add_argument("--folder", default="Fulfillment reports", help="Folder containing CSV files")
    parser.add_argument("--chunk-size", type=int, default=50000, help="Chunk size for pandas")
    parser.add_argument("--reset", action="store_true", help="Delete existing order_items before import")
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.exists():
        raise SystemExit(f"Folder not found: {folder}")

    with engine.begin() as conn:
        ensure_table(conn)
        if args.reset:
            conn.execute(text("DELETE FROM order_items"))
            print("[INFO] Cleared existing order_items rows")
        sku_map = load_sku_map(conn)
        if not sku_map:
            print("[WARN] SKU map is empty; ASIN values will be missing")
        csv_files = sorted(folder.glob("*.csv"))
        if not csv_files:
            print("[WARN] No CSV files found in folder")
            return
        for csv_path in csv_files:
            exists = conn.execute(
                text("SELECT 1 FROM order_items WHERE report_file = :name LIMIT 1"),
                {"name": csv_path.name},
            ).fetchone()
            if exists:
                print(f"[SKIP] {csv_path.name} already imported")
                continue
            process_file(conn, csv_path, sku_map, chunk_size=args.chunk_size)

        total = conn.execute(text("SELECT COUNT(*) FROM order_items")).scalar()
        print(f"[SUCCESS] order_items now contains {total} rows")


if __name__ == "__main__":
    main()

