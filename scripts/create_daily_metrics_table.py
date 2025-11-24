"""
Create daily_product_metrics table for fast dashboard queries
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, text
from config import Config

def create_table():
    """Create the daily_product_metrics table"""
    
    print("=" * 80)
    print("Creating daily_product_metrics Table")
    print("=" * 80)
    
    engine = create_engine(Config.DATABASE_URL)
    
    is_postgres = 'postgresql' in Config.DATABASE_URL
    db_type = "PostgreSQL (RDS)" if is_postgres else "SQLite (local)"
    print(f"\nDatabase: {db_type}")
    
    # Drop existing table if it exists
    print("Dropping existing table if it exists...")
    with engine.connect() as conn:
        if 'postgresql' in Config.DATABASE_URL:
            conn.execute(text("DROP TABLE IF EXISTS daily_product_metrics CASCADE"))
        else:
            conn.execute(text("DROP TABLE IF EXISTS daily_product_metrics"))
        conn.commit()
    
    print("[OK] Dropped")
    
    # Create new table
    print("Creating daily_product_metrics table...")
    
    if is_postgres:
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
    else:
        create_sql = """
        CREATE TABLE daily_product_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asin TEXT NOT NULL,
            date TEXT NOT NULL,
            units_sold INTEGER DEFAULT 0,
            sales_amount REAL DEFAULT 0.0,
            orders_count INTEGER DEFAULT 0,
            sessions INTEGER DEFAULT 0,
            page_views INTEGER DEFAULT 0,
            conversion_rate REAL DEFAULT 0.0,
            ad_spend REAL DEFAULT 0.0,
            ad_sales REAL DEFAULT 0.0,
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
    print("SUCCESS! daily_product_metrics table is ready")
    print("=" * 80)
    print("\nNext steps:")
    print("  1. Run: python scripts/backfill_daily_metrics.py")
    print("  2. Setup daily cron: python scripts/update_daily_metrics.py")
    print()

if __name__ == '__main__':
    create_table()

