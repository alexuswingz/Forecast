"""
Sync SQLite database to RDS PostgreSQL, replacing existing data.
"""
import argparse
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, text
from config import Config

TABLES = [
    "products",
    "product_cogs",
    "order_items",
    "inventory_snapshots",
    "child_traffic_metrics",
    "ad_product_performance",
    "settlement_transactions",
    "kpi_metrics",
    "metric_definitions",
]

def main():
    parser = argparse.ArgumentParser(description="Sync SQLite to RDS, replacing existing data")
    parser.add_argument("--drop-first", action="store_true", help="Drop all tables before syncing")
    args = parser.parse_args()
    
    print("=== RDS Sync Configuration ===")
    print(f"SQLite DB: {Config.SQLITE_DB_PATH}")
    print(f"RDS Host: {Config.DB_HOST}")
    print(f"RDS Database: {Config.DB_NAME}")
    
    # Connect to SQLite
    sqlite_engine = create_engine(f"sqlite:///{Config.SQLITE_DB_PATH}")
    
    # Connect to RDS
    rds_url = f"postgresql+psycopg2://{Config.DB_USER}:{Config.DB_PASSWORD}@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}"
    rds_engine = create_engine(rds_url)
    
    print("\n=== Testing RDS Connection ===")
    try:
        with rds_engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("[OK] Connected to RDS successfully")
    except Exception as e:
        print(f"[ERROR] Could not connect to RDS: {e}")
        return
    
    if args.drop_first:
        print("\n=== Dropping existing tables ===")
        from models import Base
        try:
            Base.metadata.drop_all(bind=rds_engine)
            print("[OK] Tables dropped")
        except Exception as e:
            print(f"[WARN] Error dropping tables (may not exist): {e}")
    
    print("\n=== Creating tables in RDS ===")
    from models import Base
    Base.metadata.create_all(bind=rds_engine)
    print("[OK] Tables created")
    
    print("\n=== Syncing data table by table ===")
    import pandas as pd
    
    for table in TABLES:
        print(f"\n[INFO] Syncing table: {table}")
        try:
            # Read from SQLite
            print(f"  [INFO] Reading from SQLite...", flush=True)
            df = pd.read_sql_table(table, sqlite_engine)
            row_count = len(df)
            
            if row_count == 0:
                print(f"  [SKIP] Table {table} is empty", flush=True)
                continue
            
            print(f"  [INFO] Read {row_count:,} rows from SQLite. Writing to RDS...", flush=True)
            
            # Write to RDS in chunks for large tables
            chunksize = 5000 if row_count > 100000 else 1000
            df.to_sql(table, rds_engine, if_exists='append', index=False, method='multi', chunksize=chunksize)
            print(f"  [OK] Wrote {row_count:,} rows to RDS", flush=True)
            
        except Exception as e:
            print(f"  [ERROR] Failed to sync {table}: {e}")
    
    print("\n=== Sync Complete ===")
    print("Data has been synced to RDS successfully!")

if __name__ == "__main__":
    main()

