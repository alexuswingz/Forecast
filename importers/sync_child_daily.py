import argparse
from datetime import datetime, timedelta

from sqlalchemy import func

from config import Config
from database import SessionLocal, init_db
from integrations.amazon_sp_api import AmazonSPAPIClient
from models import ChildTrafficMetric


def safe_float(value):
    if value in (None, "", "-", "NaN"):
        return None
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def upsert_day(session, client, target_date, force=False):
    existing_count = (
        session.query(func.count(ChildTrafficMetric.id))
        .filter(ChildTrafficMetric.date == target_date)
        .scalar()
    )
    if existing_count and not force:
        print(f"[SKIP] {target_date.isoformat()} already has {existing_count} rows")
        return 0

    rows, _ = client.fetch_child_traffic_metrics(
        target_date.isoformat(), target_date.isoformat()
    )
    if not rows:
        print(f"[WARN] No rows returned for {target_date}")
        return 0

    upserted = 0
    for row in rows:
        child_asin = row.get("childAsin") or row.get("child-asin") or row.get("asin")
        if not child_asin:
            continue
        sku = row.get("sku") or row.get("sellerSku") or row.get("merchantSku") or child_asin
        parent_asin = row.get("parentAsin") or row.get("parent-asin")

        record = (
            session.query(ChildTrafficMetric)
            .filter(
                ChildTrafficMetric.date == target_date,
                ChildTrafficMetric.child_asin == child_asin,
                ChildTrafficMetric.sku == sku,
            )
            .one_or_none()
        )

        payload = {
            "parent_asin": parent_asin,
            "sessions": safe_float(row.get("sessions")),
            "session_percentage": safe_float(row.get("sessionPercentage")),
            "page_views": safe_float(row.get("pageViews")),
            "page_views_percentage": safe_float(row.get("pageViewsPercentage")),
            "buy_box_percentage": safe_float(row.get("buyBoxPercentage")),
            "units_ordered": safe_float(row.get("unitsOrdered")),
            "units_ordered_b2b": safe_float(row.get("unitsOrderedB2B")),
            "ordered_product_sales": safe_float(row.get("orderedProductSales")),
            "ordered_product_sales_b2b": safe_float(row.get("orderedProductSalesB2B")),
            "total_order_items": safe_float(row.get("totalOrderItems")),
            "conversion_rate": safe_float(row.get("unitSessionPercentage")),
        }

        if record:
            for key, value in payload.items():
                setattr(record, key, value)
        else:
            session.add(
                ChildTrafficMetric(
                    date=target_date,
                    child_asin=child_asin,
                    sku=sku,
                    **payload,
                )
            )
        upserted += 1

    session.commit()
    print(f"[OK] Stored {upserted} rows for {target_date}")
    return upserted


def daterange(start_date, end_date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def determine_start_date(session, cli_start):
    if cli_start:
        return datetime.fromisoformat(cli_start).date()
    max_date = session.query(func.max(ChildTrafficMetric.date)).scalar()
    if max_date:
        return max_date + timedelta(days=1)
    return datetime.fromisoformat(Config.DATA_START_DATE).date()


def determine_end_date(cli_end):
    if cli_end:
        return datetime.fromisoformat(cli_end).date()
    return datetime.utcnow().date()


def main():
    parser = argparse.ArgumentParser(
        description="Pull SP-API child traffic metrics day-by-day without duplicates"
    )
    parser.add_argument("--start-date", help="YYYY-MM-DD (defaults to day after latest entry)")
    parser.add_argument("--end-date", help="YYYY-MM-DD (defaults to today)")
    parser.add_argument("--force", action="store_true", help="Re-fetch even if date already exists")
    args = parser.parse_args()

    init_db()
    client = AmazonSPAPIClient()
    session = SessionLocal()

    try:
        start_date = determine_start_date(session, args.start_date)
        end_date = determine_end_date(args.end_date)
        if start_date > end_date:
            print("[INFO] No new dates to fetch")
            return

        total = 0
        for day in daterange(start_date, end_date):
            total += upsert_day(session, client, day, force=args.force)
        print(f"[DONE] Inserted/updated {total} rows from {start_date} to {end_date}")
    finally:
        session.close()


if __name__ == "__main__":
    main()

