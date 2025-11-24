"""
Import Sponsored Products advertised product reports into SQLite.

Usage:
    python import_ads_report.py --input path/to/report.csv
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from sqlalchemy.dialects.sqlite import insert

from database import init_db, SessionLocal
from models import AdProductPerformance


def read_report(path: Path) -> pd.DataFrame:
    ext = path.suffix.lower()
    if ext in {".csv"}:
        return pd.read_csv(path)
    if ext in {".tsv", ".txt"}:
        return pd.read_csv(path, sep="\t")
    if ext in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    if ext == ".json":
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return pd.DataFrame(data)
    raise ValueError(f"Unsupported file type: {ext}")


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("[^a-z0-9_]", "", regex=True)
    )
    return df


def to_float(value) -> Optional[float]:
    if value in (None, "", " ", "nan", "NaN"):
        return None
    if pd.isna(value):
        return None
    if isinstance(value, str):
        value = value.replace("$", "").replace(",", "")
    try:
        result = float(value)
        # Check if result is nan or inf
        if pd.isna(result) or result == float('inf') or result == float('-inf'):
            return None
        return result
    except Exception:
        return None


def to_int(value) -> Optional[float]:
    v = to_float(value)
    return None if v is None else float(v)


def parse_date(value) -> Optional[datetime.date]:
    if pd.isna(value):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        try:
            return pd.to_datetime(value).date()
        except Exception:
            return None
    return None


def find_column(df: pd.DataFrame, candidates) -> Optional[str]:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def main():
    parser = argparse.ArgumentParser(description="Import Sponsored Products report into SQLite")
    parser.add_argument("--input", required=True, help="Path to CSV/TSV/XLSX/JSON report")
    parser.add_argument("--profile-id", help="Optional profile id to tag rows")
    parser.add_argument("--marketplace", default="US", help="Marketplace code (default US)")
    args = parser.parse_args()

    path = Path(args.input).expanduser().resolve()
    if not path.exists():
        raise SystemExit(f"Input file not found: {path}")

    print(f"[INFO] Loading report: {path}")
    df = read_report(path)
    df = normalize_columns(df)
    print(f"[INFO] Loaded {len(df)} rows with columns: {list(df.columns)[:10]} ...")

    date_col = find_column(df, ["date", "start_date", "reportingdate", "report_date"])
    asin_col = find_column(df, ["advertised_asin", "asin", "asin1"])
    sku_col = find_column(df, ["sku", "advertised_sku", "sku1", "seller_sku"])
    campaign_col = find_column(df, ["campaign_name", "campaign"])
    campaign_id_col = find_column(df, ["campaign_id"])
    ad_group_col = find_column(df, ["ad_group_name", "adgroup_name"])
    ad_group_id_col = find_column(df, ["ad_group_id"])
    targeting_col = find_column(df, ["targeting", "keyword_text", "targetingexpression"])
    placement_col = find_column(df, ["placement", "placement_type"])

    if not date_col or not asin_col:
        raise SystemExit("Report must include date and advertised_asin columns.")

    impressions_col = find_column(df, ["impressions"])
    clicks_col = find_column(df, ["clicks"])
    spend_col = find_column(df, ["spend", "cost"])
    sales_col = find_column(df, ["sales_14d", "14_day_attributed_sales", "7_day_total_sales", "sales"])
    orders_col = find_column(df, ["orders_14d", "14_day_attributed_orders", "7_day_total_orders", "orders"])
    units_col = find_column(df, ["same_sku_units_ordered_14d", "units_sold", "7_day_total_units", "units"])
    cpc_col = find_column(df, ["cpc", "average_cpc", "cost_per_click_cpc"])
    ctr_col = find_column(df, ["ctr", "click_through_rate", "clickthru_rate_ctr"])
    acos_col = find_column(df, ["acos", "advertising_cost_of_sales", "total_advertising_cost_of_sales_acos"])
    roas_col = find_column(df, ["roas", "return_on_ad_spend", "total_return_on_advertising_spend_roas"])
    conv_rate_col = find_column(df, ["conversion_rate", "7_day_conversion_rate"])
    currency_col = find_column(df, ["currency"])

    init_db()
    session = SessionLocal()
    inserted = 0
    skipped = 0

    table = AdProductPerformance.__table__

    try:
        for _, row in df.iterrows():
            report_date = parse_date(row.get(date_col))
            asin = str(row.get(asin_col) or "").strip()
            if not report_date or not asin:
                skipped += 1
                continue

            payload = {
                "report_date": report_date,
                "profile_id": args.profile_id,
                "marketplace": args.marketplace,
                "currency": row.get(currency_col) if currency_col else None,
                "campaign_name": str(row.get(campaign_col) or "Unknown").strip(),
                "campaign_id": str(row.get(campaign_id_col) or "").strip() or None,
                "ad_group_name": str(row.get(ad_group_col) or "").strip() or None,
                "ad_group_id": str(row.get(ad_group_id_col) or "").strip() or None,
                "advertised_asin": asin,
                "sku": str(row.get(sku_col) or "").strip() or None,
                "match_type": str(row.get("match_type") or row.get("matchtype") or "").strip() or None,
                "targeting": str(row.get(targeting_col) or "").strip() or None,
                "placement": str(row.get(placement_col) or "").strip() or None,
                "impressions": to_int(row.get(impressions_col)) or 0,
                "clicks": to_int(row.get(clicks_col)) or 0,
                "spend": to_float(row.get(spend_col)) or 0,
                "sales_14d": to_float(row.get(sales_col)) or 0,
                "orders_14d": to_float(row.get(orders_col)) or 0,
                "units_14d": to_float(row.get(units_col)) or 0,
                "cpc": to_float(row.get(cpc_col)),
                "ctr": to_float(row.get(ctr_col)),
                "acos": to_float(row.get(acos_col)),
                "roas": to_float(row.get(roas_col)),
                "conversion_rate": to_float(row.get(conv_rate_col)),
            }

            stmt = insert(table).values(**payload)
            update_cols = {
                c.key: stmt.excluded[c.key]
                for c in table.columns
                if c.key not in {"id", "created_at"}
            }
            stmt = stmt.on_conflict_do_update(
                index_elements=[
                    table.c.report_date,
                    table.c.campaign_name,
                    table.c.ad_group_name,
                    table.c.advertised_asin,
                    table.c.sku,
                ],
                set_=update_cols,
            )
            session.execute(stmt)
            inserted += 1

            if inserted % 1000 == 0:
                session.commit()
                print(f"[INFO] Imported {inserted} rows...", flush=True)

        session.commit()
        print(f"[SUCCESS] Imported {inserted} rows (skipped {skipped}) into ad_product_performance.")
    finally:
        session.close()


if __name__ == "__main__":
    main()

