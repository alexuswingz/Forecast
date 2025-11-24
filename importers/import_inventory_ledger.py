"""
Import Amazon Inventory Ledger CSV (summary view) into SQLite in chunks.
Usage:
    python import_inventory_ledger.py --input "C:\\Users\\User\\Downloads\\374975020406.csv"
"""

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy.dialects.sqlite import insert

from database import init_db, SessionLocal
from models import InventorySnapshot


def parse_float(value):
    if value in (None, "", " ", "nan", "NaN"):
        return None
    try:
        return float(str(value).replace(",", ""))
    except Exception:
        return None


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("[^a-z0-9_]", "", regex=True)
    )
    return df


def parse_date_str(value: str):
    if value is None or str(value).strip() == "":
        return None
    value = str(value).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(value[:10], fmt).date()
        except Exception:
            continue
    return None


def main():
    parser = argparse.ArgumentParser(description="Import Inventory Ledger CSV into SQLite")
    parser.add_argument("--input", required=True, help="Path to large CSV file")
    parser.add_argument("--chunk-size", type=int, default=50000, help="Rows per chunk")
    parser.add_argument("--program", default="FBA", help="Fulfillment program tag (default FBA)")
    args = parser.parse_args()

    path = Path(args.input).expanduser().resolve()
    if not path.exists():
        raise SystemExit(f"File not found: {path}")

    init_db()
    session = SessionLocal()
    table = InventorySnapshot.__table__

    chunks_processed = 0
    total_rows = 0
    try:
        for chunk in pd.read_csv(path, chunksize=args.chunk_size):
            chunk = normalize_columns(chunk)
            rows = chunk.to_dict(orient="records")

            for row in rows:
                snapshot_date = row.get("date") or row.get("snapshot_date")
                snapshot_date = parse_date_str(snapshot_date)
                if not snapshot_date:
                    continue

                sku = str(row.get("msku") or row.get("merchant_sku") or row.get("sku") or "").strip()
                if not sku:
                    continue

                asin = str(row.get("asin") or "").strip() or None
                fnsku = str(row.get("fnsku") or row.get("fulfillment_network_sku") or "").strip() or None

                ending_balance = parse_float(
                    row.get("ending_warehouse_balance")
                    or row.get("ending_balance")
                    or row.get("ending")
                )
                starting_balance = parse_float(row.get("starting_warehouse_balance"))
                receipts = parse_float(row.get("receipts"))
                customer_shipments = parse_float(row.get("customer_shipments"))
                customer_returns = parse_float(row.get("customer_returns"))
                warehouse_transfer = parse_float(row.get("warehouse_transfer_in_out"))
                disposition = row.get("disposition")
                location = row.get("location")

                payload = {
                    "snapshot_date": snapshot_date,
                    "asin": asin,
                    "sku": sku,
                    "fnsku": fnsku,
                    "fulfillment_program": args.program,
                    "total_quantity": ending_balance,
                    "available_quantity": ending_balance,
                    "reserved_quantity": None,
                    "inbound_working_quantity": receipts,
                    "inbound_shipped_quantity": None,
                    "inbound_receiving_quantity": None,
                    "research_quantity": None,
                    "fulfillment_center_id": location,
                    "source_report_type": "Inventory Ledger Summary",
                }

                stmt = insert(table).values(**payload)
                update_cols = {
                    c.key: stmt.excluded[c.key]
                    for c in table.columns
                    if c.key not in {"id", "created_at"}
                }
                stmt = stmt.on_conflict_do_update(
                    index_elements=[
                        table.c.snapshot_date,
                        table.c.sku,
                        table.c.fulfillment_program,
                    ],
                    set_=update_cols,
                )
                session.execute(stmt)
                total_rows += 1

            session.commit()
            chunks_processed += 1
            print(f"[INFO] Processed chunk {chunks_processed}, total rows imported so far: {total_rows}")

        print(f"[SUCCESS] Imported {total_rows} inventory rows from {path.name}")
    finally:
        session.close()


if __name__ == "__main__":
    main()

