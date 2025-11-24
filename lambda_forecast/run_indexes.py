"""
Run database indexes on RDS PostgreSQL
"""
import os
import sys
from pathlib import Path

# Add parent directory to path to import config
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import psycopg2
from config import Config

def run_indexes():
    """Execute the ADD_INDEXES.sql script on RDS"""
    
    print("=" * 60)
    print("Creating Performance Indexes on RDS")
    print("=" * 60)
    
    # Read SQL file
    sql_file = Path(__file__).parent / 'ADD_INDEXES.sql'
    with open(sql_file, 'r') as f:
        sql_commands = f.read()
    
    try:
        print(f"\nConnecting to: {Config.DB_HOST}")
        print(f"Database: {Config.DB_NAME}")
        print(f"User: {Config.DB_USER}\n")
        
        # Connect to database
        conn = psycopg2.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            database=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            connect_timeout=10
        )
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        
        cur = conn.cursor()
        
        # Process SQL file line by line to handle multi-line statements
        current_statement = []
        line_num = 0
        
        for line in sql_commands.split('\n'):
            line = line.strip()
            line_num += 1
            
            # Skip comments and empty lines
            if not line or line.startswith('--'):
                continue
            
            current_statement.append(line)
            
            # Execute when we hit a semicolon
            if line.endswith(';'):
                statement = ' '.join(current_statement).strip()
                current_statement = []
                
                if 'CREATE INDEX' in statement.upper():
                    # Extract index name for progress display
                    if 'idx_' in statement:
                        idx_name = statement.split('idx_')[1].split()[0]
                        print(f"Creating index: idx_{idx_name}...", end=' ', flush=True)
                    else:
                        print("Creating index...", end=' ', flush=True)
                        
                    cur.execute(statement)
                    print("[OK]")
                    
                elif 'ANALYZE' in statement.upper():
                    table_name = statement.split()[1].strip(';')
                    print(f"Analyzing table: {table_name}...", end=' ', flush=True)
                    cur.execute(statement)
                    print("[OK]")
                    
                elif 'SELECT' in statement.upper():
                    print("\nVerifying indexes...")
                    cur.execute(statement)
                    results = cur.fetchall()
                    
                    print("\n" + "=" * 80)
                    print("CREATED INDEXES:")
                    print("=" * 80)
                    for row in results:
                        if 'idx_' in row[2]:  # indexname column
                            print(f"  [+] {row[2]}")
                    print("=" * 80)
        
        cur.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("[SUCCESS] All indexes created successfully")
        print("=" * 60)
        print("\nYour /planning endpoint will now be MUCH faster!")
        print("Deploy the Lambda and test: GET /planning?page=1&limit=20\n")
        
    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    run_indexes()

