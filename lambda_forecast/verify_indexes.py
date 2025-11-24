"""
Verify indexes exist on RDS PostgreSQL
"""
import os
import sys
from pathlib import Path

# Add parent directory to path to import config
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import psycopg2
from config import Config

def verify_indexes():
    """Check what indexes exist"""
    
    print("=" * 60)
    print("Verifying Database Indexes")
    print("=" * 60)
    
    try:
        print(f"\nConnecting to: {Config.DB_HOST}")
        print(f"Database: {Config.DB_NAME}\n")
        
        conn = psycopg2.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            database=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            connect_timeout=10
        )
        
        cur = conn.cursor()
        
        # Check for our performance indexes
        cur.execute("""
            SELECT 
                tablename,
                indexname,
                indexdef
            FROM pg_indexes
            WHERE tablename IN ('order_items', 'inventory_snapshots', 'products')
            AND indexname LIKE 'idx_%'
            ORDER BY tablename, indexname
        """)
        
        results = cur.fetchall()
        
        if results:
            print("EXISTING PERFORMANCE INDEXES:")
            print("=" * 80)
            for row in results:
                print(f"  [+] {row[0]:25s} -> {row[1]}")
            print("=" * 80)
        else:
            print("[!] NO PERFORMANCE INDEXES FOUND - Need to create them!\n")
            
        # Check table sizes
        cur.execute("""
            SELECT 
                relname as table_name,
                pg_size_pretty(pg_total_relation_size(relid)) as total_size,
                n_live_tup as row_count
            FROM pg_stat_user_tables
            WHERE relname IN ('order_items', 'inventory_snapshots', 'products')
            ORDER BY relname
        """)
        
        print("\nTABLE SIZES:")
        print("=" * 80)
        for row in cur.fetchall():
            print(f"  {row[0]:25s} | Size: {row[1]:10s} | Rows: {row[2]:,}")
        print("=" * 80)
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    verify_indexes()


