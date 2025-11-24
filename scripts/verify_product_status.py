"""
Verify product status in RDS and show sample products
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, text
from config import Config

def verify_status():
    """Verify product status"""
    
    print("=" * 80)
    print("Verifying Product Status in RDS")
    print("=" * 80)
    
    engine = create_engine(Config.DATABASE_URL)
    
    with engine.connect() as conn:
        # Get status breakdown
        print("\nStatus breakdown:")
        result = conn.execute(text("""
            SELECT 
                COALESCE(status, 'NULL') as status,
                COUNT(*) as count
            FROM products
            GROUP BY status
            ORDER BY count DESC
        """))
        
        for row in result:
            print(f"  - {row[0]}: {row[1]} products")
        
        # Show sample products with their ASINs
        print("\nSample products (first 10):")
        result = conn.execute(text("""
            SELECT asin, product_name, brand, status
            FROM products
            ORDER BY product_name
            LIMIT 10
        """))
        
        for row in result:
            print(f"  ASIN: {row[0]}")
            print(f"    Product: {row[1]}")
            print(f"    Brand: {row[2]}")
            print(f"    Status: {row[3]}")
            print()
        
        # Search for specific products from the API response
        print("\nSearching for '10-10-10 Fertilizer' variations:")
        result = conn.execute(text("""
            SELECT asin, product_name, size, brand, status
            FROM products
            WHERE product_name LIKE '%10-10-10%'
            ORDER BY product_name, size
        """))
        
        found = False
        for row in result:
            found = True
            print(f"  ASIN: {row[0]}")
            print(f"    Product: {row[1]}")
            print(f"    Size: {row[2]}")
            print(f"    Brand: {row[3]}")
            print(f"    Status: {row[4]}")
            print()
        
        if not found:
            print("  (No products found)")
        
        # Check specific ASINs from the API response
        print("\nChecking specific ASINs from API response:")
        asins = ['B0D4JHN9KK', 'B0D4JGCSM1', 'B0D4JHVBDQ']
        
        for asin in asins:
            result = conn.execute(text("""
                SELECT asin, product_name, brand, size, status
                FROM products
                WHERE asin = :asin
            """), {'asin': asin})
            
            row = result.fetchone()
            if row:
                print(f"  {asin}:")
                print(f"    Product: {row[1]}")
                print(f"    Brand: {row[2]}")
                print(f"    Size: {row[3]}")
                print(f"    Status: {row[4]}")
            else:
                print(f"  {asin}: NOT FOUND in products table")
            print()
    
    print("=" * 80)
    print("\nIMPORTANT:")
    print("The /products/selection endpoint appears to be a DIFFERENT API/backend.")
    print("It may be querying a different database or table.")
    print("=" * 80)

if __name__ == '__main__':
    verify_status()


