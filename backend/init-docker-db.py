#!/usr/bin/env python3
"""
Docker PostgreSQL initialization script
Runs automatically when the database container starts for the first time
"""
import sys
import time
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def wait_for_db(max_retries=30):
    """Wait for PostgreSQL to be ready"""
    print("Waiting for PostgreSQL to be ready...")
    for i in range(max_retries):
        try:
            conn = psycopg2.connect(
                host='localhost',
                port=5432,
                user='postgres',
                password='postgres',
                database='postgres'
            )
            conn.close()
            print("✓ PostgreSQL is ready!")
            return True
        except psycopg2.OperationalError:
            if i < max_retries - 1:
                time.sleep(1)
            else:
                print("✗ PostgreSQL failed to start")
                return False
    return False

def init_schema():
    """Initialize database schema"""
    print("\n" + "="*60)
    print("Initializing NYC TLC Database Schema")
    print("="*60 + "\n")
    
    # Import after PostgreSQL is ready
    sys.path.insert(0, '/docker-entrypoint-initdb.d')
    
    try:
        from create_schema import create_tables, create_views, create_daily_aggregates
        
        create_tables()
        create_views()
        create_daily_aggregates()
        
        print("\n" + "="*60)
        print("✓ Database schema initialized successfully!")
        print("="*60)
        
    except Exception as e:
        print(f"\n✗ Error initializing schema: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    if wait_for_db():
        init_schema()
    else:
        sys.exit(1)
