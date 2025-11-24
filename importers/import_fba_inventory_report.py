import argparse
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import pandas as pd

DB_PATH = "kpi_metrics.db"
REPORT_TYPE = "FBA_INVENTORY_REPORT"


def normalize_column(name: str) -> str:
    slug = re.sub(r"[^0-9a-z]+", "_", name.strip().lower())
    return slug.strip("_")


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [normalize_column(col) for col in df.columns]
    return df


def parse_float(value) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, float) and not pd.isna(value):
        return value
    try:
        text = str(value).strip()
        if not text:
            return None
        text = text.replace(",", "")
        return float(text)
    except (ValueError, TypeError):
        return None


def parse_date(value) -> Optional[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return datetime.fromisoformat(str(value).strip()).date().isoformat()
    except ValueError:
        try:
            return pd.to_datetime(value).date().isoformat()
        except Exception:
            return None


def compute_total_quantity(row: dict, available: Optional[float], reserved: Optional[float]) -> Optional[float]:
    direct_total = parse_float(row.get("inventory_supply_at_fba"))
    if direct_total is not None:
        return direct_total
    inbound_total = parse_float(row.get("inbound_quantity"))
    parts = [available, reserved, inbound_total]
    if any(part is not None for part in parts):
        return sum(part or 0 for part in parts)
    return None


def prepare_records(df: pd.DataFrame) -> List[Tuple]:
    records: List[Tuple] = []
    for row in df.to_dict(orient="records"):
        snapshot_date = parse_date(row.get("snapshot_date"))
        sku = row.get("sku")
        if not snapshot_date or not sku:
            continue
        sku_clean = str(sku).strip()
        if not sku_clean:
            continue
        asin = (row.get("asin") or "").strip() or None
        fnsku = (row.get("fnsku") or "").strip() or None
        available = parse_float(row.get("available"))
        reserved = parse_float(row.get("total_reserved_quantity"))
        inbound_working = parse_float(row.get("inbound_working"))
        inbound_shipped = parse_float(row.get("inbound_shipped"))
        inbound_receiving = parse_float(row.get("inbound_received"))
        research_qty = parse_float(row.get("unfulfillable_quantity"))
        total_quantity = compute_total_quantity(row, available, reserved)
        records.append(
            (
                snapshot_date,
                asin,
                sku_clean,
                fnsku,
                total_quantity,
                available,
                reserved,
                inbound_working,
                inbound_shipped,
                inbound_receiving,
                research_qty,
            )
        )
    return records


UPSERT_SQL = """
INSERT INTO inventory_snapshots (
    snapshot_date,
    asin,
    sku,
    fnsku,
    fulfillment_program,
    total_quantity,
    available_quantity,
    reserved_quantity,
    inbound_working_quantity,
    inbound_shipped_quantity,
    inbound_receiving_quantity,
    research_quantity,
    fulfillment_center_id,
    source_report_type
) VALUES (
    ?, ?, ?, ?, 'FBA', ?, ?, ?, ?, ?, ?, ?, NULL, ?
)
ON CONFLICT(snapshot_date, sku, fulfillment_program)
DO UPDATE SET
    asin = excluded.asin,
    fnsku = excluded.fnsku,
    total_quantity = excluded.total_quantity,
    available_quantity = excluded.available_quantity,
    reserved_quantity = excluded.reserved_quantity,
    inbound_working_quantity = excluded.inbound_working_quantity,
    inbound_shipped_quantity = excluded.inbound_shipped_quantity,
    inbound_receiving_quantity = excluded.inbound_receiving_quantity,
    research_quantity = excluded.research_quantity,
    source_report_type = excluded.source_report_type
"""


def import_report(path: Path, chunk_size: int = 10000):
    if not path.exists():
        raise FileNotFoundError(f"{path} not found")
    conn = sqlite3.connect(DB_PATH)
    inserted = 0
    try:
        reader = pd.read_csv(path, sep="\t", chunksize=chunk_size, dtype=str)
        for chunk in reader:
            chunk = normalize_columns(chunk)
            records = prepare_records(chunk)
            if not records:
                continue
            conn.executemany(UPSERT_SQL, [(*record, REPORT_TYPE) for record in records])
            conn.commit()
            inserted += len(records)
            print(f"[INFO] Upserted {len(records)} rows (running total: {inserted})")
    finally:
        conn.close()
    print(f"[SUCCESS] Finished importing {inserted} inventory rows from {path.name}")


def main():
    parser = argparse.ArgumentParser(description="Import FBA Inventory Health report")
    parser.add_argument("--file", default="fba.txt", help="Path to the FBA Inventory report (.txt/.tsv)")
    parser.add_argument("--chunk-size", type=int, default=10000, help="Rows per pandas chunk")
    args = parser.parse_args()
    import_report(Path(args.file), chunk_size=args.chunk_size)


if __name__ == "__main__":
    main()

