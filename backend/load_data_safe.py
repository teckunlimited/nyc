#!/usr/bin/env python3
"""
Safe NYC TLC Data Loader with Duplicate Prevention
Uses PostgreSQL COPY for fast loading + file tracking to prevent duplicates
"""

import os
import sys
import glob
import time
import psycopg2
import pandas as pd
from io import StringIO
from datetime import datetime
from typing import List
import argparse

# Add parent directory to path to import models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import engine
from sqlalchemy import text

def get_postgres_connection():
    """Get a raw psycopg2 connection for COPY command"""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        raise ValueError("DATABASE_URL environment variable not set")
    return psycopg2.connect(db_url)


def create_tracking_table():
    """Create table to track loaded files to prevent duplicates"""
    conn = get_postgres_connection()
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS loaded_files (
            filename VARCHAR(255) PRIMARY KEY,
            load_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            record_count INTEGER,
            trip_type VARCHAR(20)
        )
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("✓ File tracking table ready")


def is_file_loaded(filename: str) -> bool:
    """Check if file has already been loaded"""
    conn = get_postgres_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM loaded_files WHERE filename = %s", (filename,))
    count = cur.fetchone()[0]
    
    cur.close()
    conn.close()
    return count > 0


def mark_file_loaded(filename: str, record_count: int, trip_type: str):
    """Mark file as loaded in tracking table"""
    conn = get_postgres_connection()
    cur = conn.cursor()
    
    cur.execute(
        """INSERT INTO loaded_files (filename, record_count, trip_type) 
           VALUES (%s, %s, %s) 
           ON CONFLICT (filename) DO NOTHING""",
        (filename, record_count, trip_type)
    )
    conn.commit()
    cur.close()
    conn.close()


def get_loaded_files_stats():
    """Get statistics on already loaded files"""
    conn = get_postgres_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT trip_type, COUNT(*), SUM(record_count) 
        FROM loaded_files 
        GROUP BY trip_type 
        ORDER BY trip_type
    """)
    results = cur.fetchall()
    
    cur.close()
    conn.close()
    return results


def load_parquet_with_copy(file_path: str, trip_type: str, batch_size: int = 100000):
    """
    Load a parquet file using PostgreSQL COPY command
    
    Args:
        file_path: Path to the parquet file
        trip_type: One of 'yellow', 'green', 'fhv', 'fhvhv'
        batch_size: Number of records to process at once
    """
    table_name = f"{trip_type}_trips"
    
    # Read the parquet file
    df = pd.read_parquet(file_path)
    
    if df.empty:
        return 0
    
    # Normalize column names
    df.columns = df.columns.str.lower().str.replace(' ', '_')
    
    total_loaded = 0
    conn = get_postgres_connection()
    cur = conn.cursor()
    
    try:
        # Process in batches
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i + batch_size]
            
            # Convert DataFrame to TSV string in memory
            buffer = StringIO()
            batch.to_csv(buffer, sep='\t', index=False, header=False, na_rep='\\N')
            buffer.seek(0)
            
            # Use COPY command
            copy_sql = f"COPY {table_name} FROM STDIN WITH (FORMAT text, DELIMITER E'\\t', NULL '\\N')"
            cur.copy_expert(copy_sql, buffer)
            
            total_loaded += len(batch)
        
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()
    
    return total_loaded


def check_taxi_zones():
    """Check if taxi zones are already loaded"""
    conn = get_postgres_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM taxi_zone_lookup")
    count = cur.fetchone()[0]
    
    cur.close()
    conn.close()
    return count


def load_taxi_zones(csv_path: str):
    """Load taxi zone lookup data"""
    zones_count = check_taxi_zones()
    
    if zones_count > 0:
        print(f"✓ Taxi zones already loaded ({zones_count:,} zones)")
        return zones_count
    
    if not os.path.exists(csv_path):
        print(f"⚠️  Taxi zone file not found: {csv_path}")
        return 0
    
    print(f"Loading taxi zones from {csv_path}...")
    
    df = pd.read_csv(csv_path)
    
    conn = get_postgres_connection()
    cur = conn.cursor()
    
    try:
        # Convert to TSV buffer
        buffer = StringIO()
        df.to_csv(buffer, sep='\t', index=False, header=False)
        buffer.seek(0)
        
        # Load with COPY
        copy_sql = "COPY taxi_zone_lookup FROM STDIN WITH (FORMAT text, DELIMITER E'\\t', NULL '')"
        cur.copy_expert(copy_sql, buffer)
        conn.commit()
        
        print(f"✓ Loaded {len(df):,} taxi zones")
        return len(df)
        
    except Exception as e:
        conn.rollback()
        print(f"✗ Error loading taxi zones: {e}")
        return 0
    finally:
        cur.close()
        conn.close()


def get_stats():
    """Get current database statistics"""
    with engine.connect() as conn:
        tables = ['yellow_trips', 'green_trips', 'fhv_trips', 'fhvhv_trips']
        
        print("\n" + "=" * 60)
        print("CURRENT DATABASE STATISTICS")
        print("=" * 60)
        
        total_records = 0
        for table in tables:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            total_records += count
            print(f"  {table:20s}: {count:>15,} records")
        
        # Check taxi zones
        result = conn.execute(text("SELECT COUNT(*) FROM taxi_zone_lookup"))
        zones = result.scalar()
        print(f"  {'taxi_zone_lookup':20s}: {zones:>15,} zones")
        
        print("-" * 60)
        print(f"  {'TOTAL TRIPS':20s}: {total_records:>15,} records")
        print("=" * 60)
        
        return total_records


def show_loaded_files():
    """Show which files have been loaded"""
    stats = get_loaded_files_stats()
    
    if not stats:
        print("\n📋 No files loaded yet (tracking table is empty)")
        return
    
    print("\n" + "=" * 60)
    print("LOADED FILES TRACKING")
    print("=" * 60)
    
    total_files = 0
    total_records = 0
    
    for trip_type, file_count, record_count in stats:
        total_files += file_count or 0
        total_records += record_count or 0
        print(f"  {trip_type:10s}: {file_count:>3} files, {record_count:>15,} records")
    
    print("-" * 60)
    print(f"  {'TOTAL':10s}: {total_files:>3} files, {total_records:>15,} records")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='Safe NYC TLC Data Loader (prevents duplicates)')
    parser.add_argument('--stats-only', action='store_true', help='Only show database statistics')
    parser.add_argument('--show-loaded', action='store_true', help='Show which files have been loaded')
    parser.add_argument('--trip-types', nargs='+', choices=['yellow', 'green', 'fhv', 'fhvhv'],
                       default=['yellow', 'green', 'fhv', 'fhvhv'],
                       help='Trip types to load')
    parser.add_argument('--data-dir', default='../tlc', help='Directory with parquet files')
    args = parser.parse_args()
    
    if args.stats_only:
        get_stats()
        return
    
    if args.show_loaded:
        show_loaded_files()
        return
    
    print("\n" + "=" * 60)
    print("NYC TLC SAFE DATA LOADER")
    print("=" * 60)
    
    # Create tracking table
    print("\n🔧 Setting up...")
    create_tracking_table()
    
    # Load taxi zones first
    print("\n📍 Checking taxi zones...")
    taxi_csv = os.path.join(args.data_dir, 'taxi_zone_lookup.csv')
    load_taxi_zones(taxi_csv)
    
    # Show what's already loaded
    show_loaded_files()
    
    # Now process trip data
    total_loaded = 0
    total_files = 0
    total_skipped = 0
    overall_start = time.time()
    
    for trip_type in args.trip_types:
        print(f"\n{'=' * 60}")
        print(f"🚕 {trip_type.upper()} TRIPS")
        print("=" * 60)
        
        pattern = os.path.join(args.data_dir, f"{trip_type}_tripdata_*.parquet")
        files = sorted(glob.glob(pattern))
        
        if not files:
            print(f"No files found: {pattern}")
            continue
        
        print(f"Found {len(files)} files")
        
        for file_path in files:
            file_name = os.path.basename(file_path)
            
            # Check if already loaded
            if is_file_loaded(file_name):
                print(f"⏭️  Skipping {file_name} (already loaded)")
                total_skipped += 1
                continue
            
            print(f"\n📥 Loading {file_name}...")
            
            try:
                start_time = time.time()
                loaded = load_parquet_with_copy(file_path, trip_type)
                duration = time.time() - start_time
                speed = loaded / duration if duration > 0 else 0
                
                total_loaded += loaded
                total_files += 1
                
                # Mark file as loaded
                mark_file_loaded(file_name, loaded, trip_type)
                
                print(f"✓ Loaded {loaded:,} records in {duration:.1f}s ({speed:,.0f} rec/s)")
                
            except Exception as e:
                print(f"✗ Error: {e}")
    
    # Final summary
    overall_duration = time.time() - overall_start
    
    print("\n" + "=" * 60)
    print("LOADING COMPLETE")
    print("=" * 60)
    print(f"  New files loaded:  {total_files}")
    print(f"  Files skipped:     {total_skipped}")
    print(f"  Records loaded:    {total_loaded:,}")
    print(f"  Duration:          {overall_duration:.1f}s ({overall_duration/60:.1f} min)")
    if total_loaded > 0:
        print(f"  Speed:             {total_loaded/overall_duration:,.0f} rec/s")
    print("=" * 60)
    
    # Show final stats
    get_stats()


if __name__ == "__main__":
    main()
