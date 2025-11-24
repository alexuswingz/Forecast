import argparse
import sqlite3
from pathlib import Path
from typing import List, Tuple

import pandas as pd

DB_PATH = "kpi_metrics.db"
FULFILLMENT_PROGRAM = "AWD"

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
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(snapshot_date, sku, fulfillment_program) DO UPDATE SET
    asin = excluded.asin,
    fnsku = excluded.fnsku,
    total_quantity = excluded.total_quantity,
    available_quantity = excluded.available_quantity,
    reserved_quantity = excluded.reserved_quantity,
    inbound_working_quantity = excluded.inbound_working_quantity,
    inbound_shipped_quantity = excluded.inbound_shipped_quantity,
    inbound_receiving_quantity = excluded.inbound_receiving_quantity,
    research_quantity = excluded.research_quantity,
    fulfillment_center_id = excluded.fulfillment_center_id,
    source_report_type = excluded.source_report_type
"""


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "Date": "date",
        "MSKU": "sku",
        "FNSKU": "fnsku",
        "ASIN": "asin",
        "Package Quantity": "package_qty",
        "Ending Warehouse Balance (cartons)": "ending_cartons",
        "Facility ID": "facility_id",
    }
    df = df.rename(columns=rename_map)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["package_qty"] = pd.to_numeric(df["package_qty"], errors="coerce").fillna(0)
    df["ending_cartons"] = pd.to_numeric(df["ending_cartons"], errors="coerce").fillna(0)
    df["units"] = df["package_qty"] * df["ending_cartons"]
    return df


def aggregate_rows(df: pd.DataFrame) -> List[Tuple]:
    aggregated = (
        df.groupby(["date", "sku"], as_index=False)
        .agg(
            {
                "asin": "first",
                "fnsku": "first",
                "units": "sum",
                "facility_id": lambda ids: ",".join(sorted({str(i) for i in ids if pd.notna(i)})) or None,
            }
        )
        .reset_index(drop=True)
    )

    records: List[Tuple] = []
    for _, row in aggregated.iterrows():
        units = float(row["units"])
        records.append(
            (
                row["date"].isoformat(),
                row.get("asin"),
                row["sku"],
                row.get("fnsku"),
                FULFILLMENT_PROGRAM,
                units,
                units,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                row.get("facility_id"),
                "AWD_INVENTORY_LEDGER",
            )
        )
    return records


def import_awd_report(path: Path):
    if not path.exists():
        raise FileNotFoundError(path)

    df = pd.read_csv(path)
    df = normalize_dataframe(df)
    records = aggregate_rows(df)
    if not records:
        print("[WARN] No AWD rows detected")
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executemany(UPSERT_SQL, records)
        conn.commit()
        print(f"[SUCCESS] Upserted {len(records)} AWD inventory records from {path.name}")
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Import AWD Inventory Ledger into inventory_snapshots")
    parser.add_argument("--file", default="3568a9b6-e7ad-41f6-a70b-7b7b58beb6f6.amzn1.tortuga.4.na.csv")
    args = parser.parse_args()
    import_awd_report(Path(args.file))


if __name__ == "__main__":
    main()

