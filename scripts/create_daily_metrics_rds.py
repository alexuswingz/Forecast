"""
Create daily_product_metrics table on RDS (PostgreSQL) - PRODUCTION
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, text
from config import Config
import os

def create_table_rds():
    """Create the daily_product_metrics table on RDS"""
    
    print("=" * 80)
    print("Creating daily_product_metrics Table on RDS")
    print("=" * 80)
    
    # Force RDS/PostgreSQL connection
    rds_url = f"postgresql://{Config.DB_USER}:{Config.DB_PASSWORD}@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}"
    
    print(f"\nConnecting to RDS:")
    print(f"  Host: {Config.DB_HOST}")
    print(f"  Database: {Config.DB_NAME}")
    print(f"  User: {Config.DB_USER}")
    
    engine = create_engine(rds_url)
    
    # Drop existing table if it exists
    print("\nDropping existing table if it exists...")
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS daily_product_metrics CASCADE"))
        conn.commit()
    
    print("[OK] Dropped")
    
    # Create new table
    print("Creating daily_product_metrics table...")
    
    create_sql = """
    CREATE TABLE daily_product_metrics (
        id SERIAL PRIMARY KEY,
        asin VARCHAR(20) NOT NULL,
        date DATE NOT NULL,
        units_sold INTEGER DEFAULT 0,
        sales_amount NUMERIC(12,2) DEFAULT 0.0,
        orders_count INTEGER DEFAULT 0,
        sessions INTEGER DEFAULT 0,
        page_views INTEGER DEFAULT 0,
        conversion_rate NUMERIC(8,4) DEFAULT 0.0,
        ad_spend NUMERIC(12,2) DEFAULT 0.0,
        ad_sales NUMERIC(12,2) DEFAULT 0.0,
        ad_clicks INTEGER DEFAULT 0,
        ad_impressions INTEGER DEFAULT 0,
        ad_orders INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(asin, date)
    );
    CREATE INDEX idx_daily_metrics_asin ON daily_product_metrics(asin);
    CREATE INDEX idx_daily_metrics_date ON daily_product_metrics(date);
    CREATE INDEX idx_daily_metrics_asin_date ON daily_product_metrics(asin, date);
    """
    
    with engine.connect() as conn:
        for statement in create_sql.strip().split(';'):
            if statement.strip():
                conn.execute(text(statement))
        conn.commit()
    
    print("[OK] Table created with indexes")
    
    print("\n" + "=" * 80)
    print("SUCCESS! daily_product_metrics table is ready on RDS")
    print("=" * 80)
    print("\nNext steps:")
    print("  1. Run: python scripts/backfill_daily_metrics_rds.py")
    print("  2. Deploy updated Lambda function")
    print("  3. Test: GET /metrics/B0BRTK1P8Z?days=30")
    print()

if __name__ == '__main__':
    create_table_rds()


