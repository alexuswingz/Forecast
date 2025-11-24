"""
Ensure every dataset links back to child/parent ASINs by:
1. Maintaining a sku_aliases table for multi-SKU mappings.
2. Backfilling missing ASINs in order_items and inventory_snapshots.
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import Config

ASIN_PATTERN = re.compile(r"\bB[0-9A-Z]{9}\b")

DEFAULT_MAPPINGS = [
    {
        "sku": "HYDRANGEA1G-FBA-UPC-0523",
        "asin": "B0C73TDZCQ",
        "notes": "Hydrangea gallon pack (manual)",
    },
]

TARGET_TABLES: List[Tuple[str, str, str]] = [
    ("order_items", "sku", "asin"),
    ("inventory_snapshots", "sku", "asin"),
    ("ad_product_performance", "sku", "advertised_asin"),
]


def ensure_alias_table(conn):
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS sku_aliases (
                sku TEXT PRIMARY KEY,
                asin TEXT NOT NULL,
                parent_asin TEXT,
                notes TEXT,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )


def upsert_default_aliases(conn):
    for entry in DEFAULT_MAPPINGS:
        sku = entry["sku"].strip().upper()
        asin = entry["asin"].strip().upper()

        upsert_alias(conn, sku, asin, entry.get("notes"), entry.get("source", "script"))


def upsert_alias(conn, sku: str, asin: str, notes: str = None, source: str = None):
    parent = conn.execute(
        text("SELECT parent_asin FROM products WHERE asin = :asin"),
        {"asin": asin},
    ).scalar()

    conn.execute(
        text(
            """
            INSERT INTO sku_aliases (sku, asin, parent_asin, notes, source, updated_at)
            VALUES (:sku, :asin, :parent_asin, :notes, :source, CURRENT_TIMESTAMP)
            ON CONFLICT (sku) DO UPDATE SET
                asin = excluded.asin,
                parent_asin = COALESCE(excluded.parent_asin, sku_aliases.parent_asin),
                notes = COALESCE(excluded.notes, sku_aliases.notes),
                source = COALESCE(excluded.source, sku_aliases.source),
                updated_at = CURRENT_TIMESTAMP
            """
        ),
        {
            "sku": sku,
            "asin": asin,
            "parent_asin": parent,
            "notes": notes,
            "source": source or "script",
        },
    )


def harvest_aliases(conn):
    queries = [
        ("order_items", "sku", "asin"),
        ("inventory_snapshots", "sku", "asin"),
        ("ad_product_performance", "sku", "advertised_asin"),
    ]
    for table, sku_col, asin_col in queries:
        try:
            rows = conn.execute(
                text(
                    f"""
                    SELECT DISTINCT UPPER({sku_col}) AS sku_key, UPPER({asin_col}) AS asin_key
                    FROM {table}
                    WHERE {sku_col} IS NOT NULL AND {sku_col} <> ''
                      AND {asin_col} IS NOT NULL AND {asin_col} <> ''
                    """
                )
            ).fetchall()
        except Exception:
            continue
        for sku_key, asin_key in rows:
            if sku_key and asin_key:
                upsert_alias(conn, sku_key, asin_key, source=f"harvest:{table}")


def load_sku_mapping(conn) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    rows = conn.execute(
        text(
            "SELECT sku, asin FROM product_cogs WHERE sku IS NOT NULL AND asin IS NOT NULL"
        )
    ).fetchall()
    for sku, asin in rows:
        sku_norm = str(sku).strip().upper()
        asin_norm = str(asin).strip().upper()
        if sku_norm and asin_norm:
            mapping[sku_norm] = asin_norm

    alias_rows = conn.execute(
        text("SELECT sku, asin FROM sku_aliases WHERE sku IS NOT NULL AND asin IS NOT NULL")
    ).fetchall()
    for sku, asin in alias_rows:
        sku_norm = str(sku).strip().upper()
        asin_norm = str(asin).strip().upper()
        if sku_norm and asin_norm:
            mapping[sku_norm] = asin_norm
    return mapping


def backfill_table(conn, table: str, sku_col: str, asin_col: str, mapping: Dict[str, str]):
    total_updates = 0
    for sku_norm, asin in mapping.items():
        result = conn.execute(
            text(
                f"""
                UPDATE {table}
                SET {asin_col} = :asin
                WHERE ({asin_col} IS NULL OR {asin_col} = '')
                  AND UPPER({sku_col}) = :sku
                """
            ),
            {"asin": asin, "sku": sku_norm},
        )
        total_updates += result.rowcount or 0
    if total_updates:
        print(f"[INFO] Updated {total_updates} rows in {table}")
    else:
        print(f"[INFO] No changes needed for {table}")


def ensure_product_rows(conn, mapping: Dict[str, str]):
    for asin in set(mapping.values()):
        exists = conn.execute(
            text("SELECT 1 FROM products WHERE asin = :asin LIMIT 1"),
            {"asin": asin},
        ).scalar()
        if exists:
            continue
        conn.execute(
            text("INSERT INTO products (asin, product_name) VALUES (:asin, :name)"),
            {"asin": asin, "name": "Auto-imported child"},
        )


def extract_asin_from_text(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    match = ASIN_PATTERN.search(value.upper())
    if match:
        return match.group(0)
    return None


def backfill_ads_from_campaign(conn):
    rows = conn.execute(
        text(
            """
            SELECT id, campaign_name
            FROM ad_product_performance
            WHERE advertised_asin IS NULL OR advertised_asin = ''
            """
        )
    ).mappings().all()
    updates = 0
    for row in rows:
        asin = extract_asin_from_text(row["campaign_name"])
        if not asin:
            continue
        conn.execute(
            text(
                "UPDATE ad_product_performance SET advertised_asin = :asin WHERE id = :id"
            ),
            {"asin": asin, "id": row["id"]},
        )
        updates += 1
    if updates:
        print(f"[INFO] Backfilled {updates} ad rows using campaign names")


def main():
    engine = create_engine(Config.DATABASE_URL)
    with engine.begin() as conn:
        ensure_alias_table(conn)
        upsert_default_aliases(conn)
        harvest_aliases(conn)
        backfill_ads_from_campaign(conn)
        mapping = load_sku_mapping(conn)
        ensure_product_rows(conn, mapping)
        for table, sku_col, asin_col in TARGET_TABLES:
            try:
                backfill_table(conn, table, sku_col, asin_col, mapping)
            except Exception as exc:
                print(f"[WARN] Skipping {table}: {exc}")

    print("[DONE] ASIN linkage ensured")


if __name__ == "__main__":
    main()

