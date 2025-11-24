import argparse
import logging
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from config import Config
from database import SessionLocal, init_db
from integrations.amazon_sp_api import AmazonSPAPIClient
from models import SettlementTransaction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

INSERT_CLS = sqlite_insert if Config.USE_SQLITE else pg_insert


def normalize_keys(row: Dict) -> Dict:
    normalized = {}
    for key, value in row.items():
        if key is None:
            continue
        norm = (
            key.strip()
            .lower()
            .replace(" ", "_")
            .replace("-", "_")
        )
        normalized[norm] = value
    return normalized


def parse_float(value: Optional[str]) -> Optional[float]:
    if value in (None, "", " "):
        return None
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return None


def parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    value = str(value).strip()
    if not value:
        return None
    value = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    return None


def prepare_payload(row: Dict) -> Optional[Dict]:
    data = normalize_keys(row)
    # Some settlement lines are summary rows with no transaction data; skip them.
    if not data.get("transaction_type") and not data.get("amount_type"):
        return None

    posted = parse_datetime(data.get("posted_date_time") or data.get("posted_date"))
    return {
        "settlement_id": data.get("settlement_id"),
        "settlement_start_date": parse_datetime(data.get("settlement_start_date")),
        "settlement_end_date": parse_datetime(data.get("settlement_end_date")),
        "deposit_date": parse_datetime(data.get("deposit_date")),
        "total_amount": parse_float(data.get("total_amount")),
        "currency": data.get("currency"),
        "transaction_type": data.get("transaction_type"),
        "order_id": data.get("order_id"),
        "merchant_order_id": data.get("merchant_order_id"),
        "adjustment_id": data.get("adjustment_id"),
        "shipment_id": data.get("shipment_id"),
        "marketplace_name": data.get("marketplace_name"),
        "fulfillment_id": data.get("fulfillment_id"),
        "posted_date": posted,
        "amount_type": data.get("amount_type"),
        "amount_description": data.get("amount_description"),
        "amount": parse_float(data.get("amount")),
        "quantity": parse_float(
            data.get("quantity") or data.get("quantity_purchased") or data.get("quantity_shipped")
        ),
        "sku": (data.get("sku") or data.get("merchant_sku") or "").strip() or None,
        "asin": data.get("asin"),
        "product_name": data.get("product_name"),
        "store_name": data.get("store_name"),
    }


def upsert_transactions(rows: Iterable[Dict]) -> int:
    session = SessionLocal()
    inserted = 0
    try:
        for raw_row in rows:
            payload = prepare_payload(raw_row)
            if not payload:
                continue
            stmt = INSERT_CLS(SettlementTransaction).values(**payload)
            update_cols = {k: v for k, v in payload.items() if k not in {"created_at"}}
            stmt = stmt.on_conflict_do_update(
                constraint="uq_settlement_transaction",
                set_=update_cols,
            )
            session.execute(stmt)
            inserted += 1
        session.commit()
        return inserted
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def daterange_chunks(start: datetime, end: datetime, chunk_days: int) -> Iterable[tuple]:
    current = start
    delta = timedelta(days=chunk_days - 1)
    while current <= end:
        chunk_end = min(current + delta, end)
        yield current, chunk_end
        current = chunk_end + timedelta(days=1)


def main():
    parser = argparse.ArgumentParser(description="Fetch and store Amazon settlement reports via SP-API.")
    parser.add_argument("--start-date", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="End date (YYYY-MM-DD). Defaults to today.")
    parser.add_argument("--chunk-days", type=int, default=30, help="Days per report request (default 30)")
    args = parser.parse_args()

    start = datetime.fromisoformat(args.start_date).date()
    end = datetime.fromisoformat(args.end_date).date() if args.end_date else datetime.utcnow().date()

    init_db()
    client = AmazonSPAPIClient()

    total_rows = 0
    for chunk_start, chunk_end in daterange_chunks(start, end, args.chunk_days):
        logger.info("Requesting settlement data %s -> %s", chunk_start, chunk_end)
        rows = client.fetch_settlement_transactions(
            chunk_start.isoformat(),
            chunk_end.isoformat(),
        )
        if not rows:
            logger.info("No settlement rows returned for %s -> %s", chunk_start, chunk_end)
            continue
        inserted = upsert_transactions(rows)
        logger.info("Stored %s settlement rows for %s -> %s", inserted, chunk_start, chunk_end)
        total_rows += inserted

    logger.info("Finished. Total settlement rows processed: %s", total_rows)


if __name__ == "__main__":
    main()



