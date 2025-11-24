"""
Add status column to products table and set all existing products to 'Launched'
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, text
from config import Config

def add_status_column():
    """Add status column and update all products to Launched"""
    
    print("=" * 80)
    print("Adding Product Status Column")
    print("=" * 80)
    
    engine = create_engine(Config.DATABASE_URL)
    
    is_postgres = 'postgresql' in Config.DATABASE_URL
    db_type = "PostgreSQL (RDS)" if is_postgres else "SQLite (local)"
    print(f"\nDatabase: {db_type}")
    
    with engine.connect() as conn:
        # Check if column already exists
        if is_postgres:
            check_sql = """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'products' 
                AND column_name = 'status'
            """
        else:
            check_sql = """
                SELECT COUNT(*) as cnt
                FROM pragma_table_info('products')
                WHERE name = 'status'
            """
        
        result = conn.execute(text(check_sql))
        exists = result.fetchone()
        
        if is_postgres:
            column_exists = exists is not None
        else:
            column_exists = exists[0] > 0 if exists else False
        
        if column_exists:
            print("\n[INFO] Status column already exists")
        else:
            print("\n[STEP 1] Adding 'status' column to products table...")
            
            if is_postgres:
                add_column_sql = """
                    ALTER TABLE products 
                    ADD COLUMN status VARCHAR(50) DEFAULT 'Launched'
                """
            else:
                add_column_sql = """
                    ALTER TABLE products 
                    ADD COLUMN status TEXT DEFAULT 'Launched'
                """
            
            conn.execute(text(add_column_sql))
            conn.commit()
            print("[OK] Column added")
        
        # Update all existing products to 'Launched'
        print("\n[STEP 2] Setting all products to 'Launched' status...")
        
        update_sql = """
            UPDATE products 
            SET status = 'Launched'
            WHERE status IS NULL OR status = ''
        """
        
        result = conn.execute(text(update_sql))
        conn.commit()
        
        updated_count = result.rowcount
        print(f"[OK] Updated {updated_count} products to 'Launched'")
        
        # Get total count
        count_sql = "SELECT COUNT(*) as total FROM products"
        result = conn.execute(text(count_sql))
        total = result.fetchone()[0]
        
        print(f"\n[INFO] Total products in database: {total}")
        
        # Show status breakdown
        status_sql = """
            SELECT 
                COALESCE(status, 'NULL') as status,
                COUNT(*) as count
            FROM products
            GROUP BY status
            ORDER BY count DESC
        """
        
        result = conn.execute(text(status_sql))
        print("\n[INFO] Status breakdown:")
        for row in result:
            print(f"  - {row[0]}: {row[1]} products")
    
    print("\n" + "=" * 80)
    print("SUCCESS! All products are now set to 'Launched'")
    print("=" * 80)
    print("\nNew products added in the future will:")
    print("  - Default to 'Launched' status automatically")
    print("  - Can be changed manually if needed (e.g., 'Draft', 'Discontinued')")
    print()

if __name__ == '__main__':
    add_status_column()


