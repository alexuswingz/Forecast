import argparse
import sys
from pathlib import Path

import pandas as pd
import psycopg2
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models import Base


TABLES = [
    "products",
    "product_cogs",
    "order_items",
    "inventory_snapshots",
    "child_traffic_metrics",
    "ad_product_performance",
    "kpi_metrics",
    "metric_definitions",
]


def ensure_database(host, port, user, password, database):
    conn = psycopg2.connect(
        host=host, port=port, user=user, password=password, dbname="postgres"
    )
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (database,))
    exists = cur.fetchone()
    if not exists:
        cur.execute(f'CREATE DATABASE "{database}"')
        print(f"[INFO] Created database {database}")
    else:
        print(f"[INFO] Database {database} already exists")
    cur.close()
    conn.close()


def transfer_table(table, sqlite_engine, pg_engine):
    print(f"[INFO] Copying table {table}")
    df = pd.read_sql_table(table, sqlite_engine)
    if df.empty:
        print(f"[WARN] {table} is empty; skipping insert")
        return
    df.to_sql(table, pg_engine, if_exists="append", index=False, method="multi")
    if "id" in df.columns:
        with pg_engine.begin() as conn:
            conn.execute(
                text(
                    """
                    SELECT setval(pg_get_serial_sequence(:table, 'id'),
                                   (SELECT MAX(id) FROM {}), true)
                    """.format(table)
                ),
                {"table": table},
            )


def main():
    parser = argparse.ArgumentParser(description="Copy SQLite DB into Postgres")
    parser.add_argument("--sqlite", default="kpi_metrics.db")
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--database", default="kpi_metrics")
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--password", default="postgres")
    args = parser.parse_args()

    ensure_database(args.host, args.port, args.user, args.password, args.database)

    sqlite_engine = create_engine(f"sqlite:///{args.sqlite}")
    pg_engine = create_engine(
        f"postgresql+psycopg2://{args.user}:{args.password}@{args.host}:{args.port}/{args.database}"
    )

    Base.metadata.create_all(bind=pg_engine)

    for table in TABLES:
        transfer_table(table, sqlite_engine, pg_engine)

    print("[SUCCESS] Migration complete.")


if __name__ == "__main__":
    main()

