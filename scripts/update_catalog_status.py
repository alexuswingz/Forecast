"""
Update status in catalog table (used by /products/selection endpoint)
The status is stored in the JSONB 'notes' field
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, text
from config import Config
import json

def update_catalog_status():
    """Update status in catalog table's notes field"""
    
    print("=" * 80)
    print("Updating Catalog Table Status (for /products/selection endpoint)")
    print("=" * 80)
    
    engine = create_engine(Config.DATABASE_URL)
    
    is_postgres = 'postgresql' in Config.DATABASE_URL
    db_type = "PostgreSQL (RDS)" if is_postgres else "SQLite (local)"
    print(f"\nDatabase: {db_type}")
    
    print("\nValid statuses:")
    print("  - Launched (setting all products to this)")
    print("  - In Progress")
    print("  - Contender")
    print("  - Revisit")
    print("  - Rejected")
    
    with engine.connect() as conn:
        # Check if catalog table exists
        print("\nChecking if 'catalog' table exists...")
        
        if is_postgres:
            check_sql = """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'catalog'
                )
            """
        else:
            check_sql = """
                SELECT COUNT(*) 
                FROM sqlite_master 
                WHERE type='table' AND name='catalog'
            """
        
        result = conn.execute(text(check_sql))
        exists = result.fetchone()[0]
        
        if not exists:
            print("[ERROR] 'catalog' table does not exist!")
            print("This table is used by the /products/selection endpoint.")
            return
        
        print("[OK] 'catalog' table found")
        
        # Get current count
        count_sql = "SELECT COUNT(*) FROM catalog"
        result = conn.execute(text(count_sql))
        total_count = result.fetchone()[0]
        print(f"\nTotal products in catalog: {total_count}")
        
        # Show current status breakdown
        print("\nCurrent status breakdown:")
        status_sql = """
            SELECT 
                COALESCE(notes->>'status', 'NULL') as status,
                COUNT(*) as count
            FROM catalog
            GROUP BY notes->>'status'
            ORDER BY count DESC
        """
        
        result = conn.execute(text(status_sql))
        for row in result:
            print(f"  - {row[0]}: {row[1]} products")
        
        # Update all products to have status = 'Launched' in notes field
        print("\n" + "=" * 80)
        print("Updating all products to 'Launched' status...")
        print("=" * 80)
        
        if is_postgres:
            # PostgreSQL: Use JSONB operations
            update_sql = """
                UPDATE catalog
                SET notes = COALESCE(notes, '{}'::jsonb) || '{"status": "Launched"}'::jsonb,
                    updated_at = NOW()
                WHERE notes->>'status' IS NULL 
                   OR notes->>'status' != 'Launched'
            """
        else:
            # SQLite: Use JSON functions
            update_sql = """
                UPDATE catalog
                SET notes = json_set(
                    COALESCE(notes, '{}'),
                    '$.status',
                    'Launched'
                ),
                updated_at = datetime('now')
                WHERE json_extract(notes, '$.status') IS NULL
                   OR json_extract(notes, '$.status') != 'Launched'
            """
        
        result = conn.execute(text(update_sql))
        conn.commit()
        
        updated_count = result.rowcount
        print(f"[OK] Updated {updated_count} products")
        
        # Show updated status breakdown
        print("\nUpdated status breakdown:")
        result = conn.execute(text(status_sql))
        for row in result:
            print(f"  - {row[0]}: {row[1]} products")
        
        # Show sample products
        print("\nSample products (first 5):")
        sample_sql = """
            SELECT 
                id,
                product_name,
                brand_name,
                notes->>'status' as status,
                notes->>'actionType' as action_type
            FROM catalog
            WHERE product_name IS NOT NULL
            ORDER BY product_name
            LIMIT 5
        """
        
        result = conn.execute(text(sample_sql))
        for row in result:
            print(f"  ID {row[0]}: {row[1]}")
            print(f"    Brand: {row[2]}")
            print(f"    Status: {row[3]}")
            print(f"    Action Type: {row[4]}")
            print()
    
    print("=" * 80)
    print("SUCCESS! All catalog products now have 'Launched' status")
    print("=" * 80)
    print("\nThe /products/selection endpoint should now return status = 'Launched'")
    print("for all products instead of null.")
    print("\nNote: Future products will need status set when created.")
    print()

if __name__ == '__main__':
    update_catalog_status()


