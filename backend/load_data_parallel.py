"""
Parallel data loader for TLC trip parquet files
Loads multiple files simultaneously for 2-3x faster performance
"""
import os
import sys
import glob
from pathlib import Path
import pandas as pd
import psycopg2
from io import StringIO
from sqlalchemy import text
from database import engine
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import time

# Thread-safe counter
stats_lock = Lock()
total_loaded = 0
total_files = 0

# Column mappings from parquet to database models
YELLOW_COLUMNS = {
    'VendorID': 'vendor_id',
    'tpep_pickup_datetime': 'tpep_pickup_datetime',
    'tpep_dropoff_datetime': 'tpep_dropoff_datetime',
    'passenger_count': 'passenger_count',
    'trip_distance': 'trip_distance',
    'RatecodeID': 'rate_code_id',
    'store_and_fwd_flag': 'store_and_fwd_flag',
    'PULocationID': 'pu_location_id',
    'DOLocationID': 'do_location_id',
    'payment_type': 'payment_type',
    'fare_amount': 'fare_amount',
    'extra': 'extra',
    'mta_tax': 'mta_tax',
    'tip_amount': 'tip_amount',
    'tolls_amount': 'tolls_amount',
    'improvement_surcharge': 'improvement_surcharge',
    'total_amount': 'total_amount',
    'congestion_surcharge': 'congestion_surcharge',
    'airport_fee': 'airport_fee'
}

GREEN_COLUMNS = {
    'VendorID': 'vendor_id',
    'lpep_pickup_datetime': 'lpep_pickup_datetime',
    'lpep_dropoff_datetime': 'lpep_dropoff_datetime',
    'store_and_fwd_flag': 'store_and_fwd_flag',
    'RatecodeID': 'rate_code_id',
    'PULocationID': 'pu_location_id',
    'DOLocationID': 'do_location_id',
    'passenger_count': 'passenger_count',
    'trip_distance': 'trip_distance',
    'fare_amount': 'fare_amount',
    'extra': 'extra',
    'mta_tax': 'mta_tax',
    'tip_amount': 'tip_amount',
    'tolls_amount': 'tolls_amount',
    'ehail_fee': 'ehail_fee',
    'improvement_surcharge': 'improvement_surcharge',
    'total_amount': 'total_amount',
    'payment_type': 'payment_type',
    'trip_type': 'trip_type',
    'congestion_surcharge': 'congestion_surcharge'
}

FHV_COLUMNS = {
    'dispatching_base_num': 'dispatching_base_num',
    'pickup_datetime': 'pickup_datetime',
    'dropOff_datetime': 'dropoff_datetime',
    'PUlocationID': 'pu_location_id',
    'DOlocationID': 'do_location_id',
    'SR_Flag': 'sr_flag',
    'Affiliated_base_number': 'affiliated_base_number'
}

FHVHV_COLUMNS = {
    'hvfhs_license_num': 'hvfhs_license_num',
    'dispatching_base_num': 'dispatching_base_num',
    'originating_base_num': 'originating_base_num',
    'request_datetime': 'request_datetime',
    'on_scene_datetime': 'on_scene_datetime',
    'pickup_datetime': 'pickup_datetime',
    'dropoff_datetime': 'dropoff_datetime',
    'PULocationID': 'pu_location_id',
    'DOLocationID': 'do_location_id',
    'trip_miles': 'trip_miles',
    'trip_time': 'trip_time',
    'base_passenger_fare': 'base_passenger_fare',
    'tolls': 'tolls',
    'bcf': 'bcf',
    'sales_tax': 'sales_tax',
    'congestion_surcharge': 'congestion_surcharge',
    'airport_fee': 'airport_fee',
    'tips': 'tips',
    'driver_pay': 'driver_pay',
    'shared_request_flag': 'shared_request_flag',
    'shared_match_flag': 'shared_match_flag',
    'access_a_ride_flag': 'access_a_ride_flag',
    'wav_request_flag': 'wav_request_flag',
    'wav_match_flag': 'wav_match_flag'
}


def get_postgres_connection():
    """Get a raw psycopg2 connection for COPY command"""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        raise ValueError("DATABASE_URL environment variable not set")
    return psycopg2.connect(db_url)


def load_single_file(file_path: str, trip_type: str, batch_size: int = 50000):
    """
    Load a single parquet file using PostgreSQL COPY command
    This function is thread-safe and can be called in parallel
    """
    global total_loaded, total_files
    
    file_name = os.path.basename(file_path)
    start_time = time.time()
    
    try:
        # Read parquet file
        df = pd.read_parquet(file_path)
        total_rows = len(df)
        
        # Get column mapping and table name
        if trip_type == 'yellow':
            column_map = YELLOW_COLUMNS
            table_name = 'yellow_trips'
        elif trip_type == 'green':
            column_map = GREEN_COLUMNS
            table_name = 'green_trips'
        elif trip_type == 'fhv':
            column_map = FHV_COLUMNS
            table_name = 'fhv_trips'
        elif trip_type == 'fhvhv':
            column_map = FHVHV_COLUMNS
            table_name = 'fhvhv_trips'
        else:
            raise ValueError(f"Unknown trip type: {trip_type}")
        
        # Rename columns to match database schema
        available_columns = {k: v for k, v in column_map.items() if k in df.columns}
        df = df[list(available_columns.keys())]
        df.rename(columns=available_columns, inplace=True)
        
        # Replace NaN with None for proper NULL handling
        df = df.where(pd.notnull(df), None)
        
        # Get column names in order
        columns = list(df.columns)
        
        # Connect to PostgreSQL (each thread gets its own connection)
        conn = get_postgres_connection()
        cur = conn.cursor()
        
        loaded = 0
        
        # Process in batches
        for i in range(0, len(df), batch_size):
            batch_df = df.iloc[i:i + batch_size]
            
            # Create a StringIO buffer with CSV data
            buffer = StringIO()
            batch_df.to_csv(buffer, index=False, header=False, sep='\t', na_rep='\\N')
            buffer.seek(0)
            
            # Use COPY command
            copy_sql = f"""
                COPY {table_name} ({', '.join(columns)})
                FROM STDIN
                WITH (FORMAT CSV, DELIMITER E'\\t', NULL '\\N')
            """
            
            try:
                cur.copy_expert(copy_sql, buffer)
                conn.commit()
                loaded += len(batch_df)
                
            except Exception as e:
                conn.rollback()
                # Continue with next batch (likely duplicate key violations)
        
        cur.close()
        conn.close()
        
        duration = time.time() - start_time
        speed = loaded / duration if duration > 0 else 0
        
        # Thread-safe update of global counters
        with stats_lock:
            total_loaded += loaded
            total_files += 1
        
        print(f"✓ {file_name}: {loaded:,} records in {duration:.1f}s ({speed:,.0f} rec/s)")
        return loaded
        
    except Exception as e:
        print(f"✗ {file_name}: Error - {e}")
        return 0


def load_files_parallel(file_list: list, trip_type: str, max_workers: int = 4):
    """
    Load multiple files in parallel using ThreadPoolExecutor
    
    Args:
        file_list: List of file paths to load
        trip_type: Type of trip data
        max_workers: Number of parallel threads (default 4)
    """
    print(f"\n{trip_type.upper()} TRIPS: Loading {len(file_list)} files with {max_workers} workers")
    print("-" * 80)
    
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all files for processing
        futures = {
            executor.submit(load_single_file, file_path, trip_type): file_path 
            for file_path in file_list
        }
        
        # Wait for completion
        for future in as_completed(futures):
            file_path = futures[future]
            try:
                future.result()
            except Exception as e:
                print(f"✗ {os.path.basename(file_path)}: Exception - {e}")
    
    duration = time.time() - start_time
    print(f"\nCompleted {len(file_list)} files in {duration:.1f}s ({duration/60:.1f} min)")


def load_all_files(data_dir: str, trip_types: list = None, max_workers: int = 4, year_filter: int = None):
    """
    Load all parquet files using parallel processing
    
    Args:
        data_dir: Directory containing parquet files
        trip_types: List of trip types to load (default: all)
        max_workers: Number of parallel threads per trip type
        year_filter: Only load files from this year (default: all years)
    """
    global total_loaded, total_files
    
    if trip_types is None:
        trip_types = ['yellow', 'green', 'fhv', 'fhvhv']
    
    print("=" * 80)
    print("TLC Trip Data Parallel Loader")
    print(f"Workers per trip type: {max_workers}")
    print("=" * 80)
    
    total_loaded = 0
    total_files = 0
    overall_start = time.time()
    
    for trip_type in trip_types:
        pattern = f"{data_dir}/{trip_type}_tripdata_*.parquet"
        files = sorted(glob.glob(pattern))
        
        if year_filter:
            files = [f for f in files if f"{year_filter}-" in f]
        
        if not files:
            print(f"\n{trip_type.upper()}: No files found")
            continue
        
        # Load files in parallel for this trip type
        load_files_parallel(files, trip_type, max_workers)
    
    overall_duration = time.time() - overall_start
    
    # Refresh materialized views
    print("\n" + "=" * 80)
    print("Refreshing materialized views...")
    try:
        with engine.begin() as conn:
            print("  Refreshing trip_summary_view...")
            conn.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY trip_summary_view"))
            print("  ✓ trip_summary_view refreshed")
            
            print("  Refreshing daily_trip_aggregates...")
            conn.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY daily_trip_aggregates"))
            print("  ✓ daily_trip_aggregates refreshed")
    except Exception as e:
        print(f"  ✗ Error refreshing views: {e}")
    
    print("\n" + "=" * 80)
    print("COMPLETE!")
    print(f"  Files processed: {total_files}")
    print(f"  Records loaded: {total_loaded:,}")
    print(f"  Duration: {overall_duration:.1f}s ({overall_duration/60:.1f} min)")
    print(f"  Average speed: {total_loaded/overall_duration:,.0f} records/second")
    print("=" * 80)


def get_stats():
    """Get current database statistics"""
    with engine.connect() as conn:
        tables = ['yellow_trips', 'green_trips', 'fhv_trips', 'fhvhv_trips']
        
        print("\nCurrent Database Statistics:")
        print("-" * 60)
        
        total_records = 0
        for table in tables:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            total_records += count
            print(f"  {table:20s}: {count:>15,} records")
        
        print("-" * 60)
        print(f"  {'TOTAL':20s}: {total_records:>15,} records")
        
        # Get date range for yellow trips
        try:
            result = conn.execute(text("""
                SELECT 
                    MIN(tpep_pickup_datetime) as min_date,
                    MAX(tpep_pickup_datetime) as max_date
                FROM yellow_trips
                WHERE tpep_pickup_datetime IS NOT NULL
            """))
            date_range = result.fetchone()
            if date_range and date_range[0]:
                print(f"  Date range: {date_range[0]} to {date_range[1]}")
        except:
            pass
        
        print()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Parallel TLC trip data loader')
    parser.add_argument('--data-dir', default='../tlc', help='Directory containing parquet files')
    parser.add_argument('--trip-types', nargs='+', choices=['yellow', 'green', 'fhv', 'fhvhv'],
                       help='Trip types to load (default: all)')
    parser.add_argument('--workers', type=int, default=4, 
                       help='Number of parallel workers per trip type (default: 4)')
    parser.add_argument('--year', type=int, help='Only load data for specific year')
    parser.add_argument('--stats-only', action='store_true', help='Only show statistics, do not load')
    
    args = parser.parse_args()
    
    if args.stats_only:
        get_stats()
    else:
        load_all_files(args.data_dir, args.trip_types, args.workers, args.year)
        get_stats()
