"""
Update status in catalog table - connecting directly to the Lambda's RDS instance
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import json

# Same DB config as the Lambda function
DB_CONFIG = {
    'host': 'bananas-db.cf6s2y8ae04j.ap-southeast-2.rds.amazonaws.com',
    'port': 5432,
    'database': 'postgres',
    'user': 'postgres',
    'password': 'postgres'
}

def update_catalog_status():
    """Update status in catalog table's notes field"""
    
    print("=" * 80)
    print("Updating Catalog Table Status (Lambda RDS Instance)")
    print("=" * 80)
    print(f"\nConnecting to: {DB_CONFIG['host']}")
    print(f"Database: {DB_CONFIG['database']}")
    
    print("\nValid statuses:")
    print("  - Launched (setting all products to this)")
    print("  - In Progress")
    print("  - Contender")
    print("  - Revisit")
    print("  - Rejected")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check if catalog table exists
        print("\nChecking if 'catalog' table exists...")
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'catalog'
            )
        """)
        
        exists = cursor.fetchone()['exists']
        
        if not exists:
            print("[ERROR] 'catalog' table does not exist!")
            print("This table is used by the /products/selection endpoint.")
            cursor.close()
            conn.close()
            return
        
        print("[OK] 'catalog' table found")
        
        # Get current count
        cursor.execute("SELECT COUNT(*) as count FROM catalog")
        total_count = cursor.fetchone()['count']
        print(f"\nTotal products in catalog: {total_count}")
        
        # Show current status breakdown
        print("\nCurrent status breakdown:")
        cursor.execute("""
            SELECT 
                COALESCE(notes->>'status', 'NULL') as status,
                COUNT(*) as count
            FROM catalog
            GROUP BY notes->>'status'
            ORDER BY count DESC
        """)
        
        for row in cursor.fetchall():
            print(f"  - {row['status']}: {row['count']} products")
        
        # Update all products to have status = 'Launched' in notes field
        print("\n" + "=" * 80)
        print("Updating all products to 'Launched' status...")
        print("=" * 80)
        
        cursor.execute("""
            UPDATE catalog
            SET notes = COALESCE(notes, '{}'::jsonb) || '{"status": "Launched"}'::jsonb,
                updated_at = NOW()
        """)
        
        updated_count = cursor.rowcount
        conn.commit()
        
        print(f"[OK] Updated {updated_count} products")
        
        # Show updated status breakdown
        print("\nUpdated status breakdown:")
        cursor.execute("""
            SELECT 
                COALESCE(notes->>'status', 'NULL') as status,
                COUNT(*) as count
            FROM catalog
            GROUP BY notes->>'status'
            ORDER BY count DESC
        """)
        
        for row in cursor.fetchall():
            print(f"  - {row['status']}: {row['count']} products")
        
        # Show sample products
        print("\nSample products (first 10):")
        cursor.execute("""
            SELECT 
                id,
                product_name,
                brand_name,
                notes->>'status' as status,
                notes->>'actionType' as action_type
            FROM catalog
            WHERE product_name IS NOT NULL
            ORDER BY product_name
            LIMIT 10
        """)
        
        for row in cursor.fetchall():
            print(f"  ID {row['id']}: {row['product_name']}")
            print(f"    Brand: {row['brand_name']}")
            print(f"    Status: {row['status']}")
            print(f"    Action Type: {row['action_type']}")
            print()
        
        cursor.close()
        conn.close()
        
        print("=" * 80)
        print("SUCCESS! All catalog products now have 'Launched' status")
        print("=" * 80)
        print("\nThe /products/selection endpoint should now return status = 'Launched'")
        print("for all products instead of null.")
        print("\nTest the endpoint:")
        print("https://sl2r0ip8zl.execute-api.ap-southeast-2.amazonaws.com/products/selection")
        print()
        
    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    update_catalog_status()


