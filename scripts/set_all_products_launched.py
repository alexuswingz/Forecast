"""
Set all products to 'Launched' status
Valid statuses: Launched, In Progress, Contender, Revisit, Rejected
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, text
from config import Config

def set_all_launched():
    """Set all products to Launched status"""
    
    print("=" * 80)
    print("Setting All Products to 'Launched' Status")
    print("=" * 80)
    
    engine = create_engine(Config.DATABASE_URL)
    
    is_postgres = 'postgresql' in Config.DATABASE_URL
    db_type = "PostgreSQL (RDS)" if is_postgres else "SQLite (local)"
    print(f"\nDatabase: {db_type}")
    
    print("\nValid statuses:")
    print("  - Launched (default for existing products)")
    print("  - In Progress")
    print("  - Contender")
    print("  - Revisit")
    print("  - Rejected")
    
    with engine.connect() as conn:
        # Update all products to 'Launched'
        print("\nUpdating all products to 'Launched'...")
        
        update_sql = """
            UPDATE products 
            SET status = 'Launched'
        """
        
        result = conn.execute(text(update_sql))
        conn.commit()
        
        updated_count = result.rowcount
        print(f"[OK] Updated {updated_count} products")
        
        # Get status breakdown
        status_sql = """
            SELECT 
                COALESCE(status, 'NULL') as status,
                COUNT(*) as count
            FROM products
            GROUP BY status
            ORDER BY count DESC
        """
        
        result = conn.execute(text(status_sql))
        print("\nStatus breakdown:")
        for row in result:
            print(f"  - {row[0]}: {row[1]} products")
        
        # Get total
        total_sql = "SELECT COUNT(*) as total FROM products"
        result = conn.execute(text(total_sql))
        total = result.fetchone()[0]
        print(f"\nTotal products: {total}")
    
    print("\n" + "=" * 80)
    print("SUCCESS! All products are now 'Launched'")
    print("=" * 80)
    print("\nNote: New products added in the future will default to 'Launched'")
    print("You can manually change status to: In Progress, Contender, Revisit, or Rejected")
    print()

if __name__ == '__main__':
    set_all_launched()

