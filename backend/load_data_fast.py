"""
Fast data loader using PostgreSQL COPY command
This is 3-5x faster than pandas to_sql
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
    
    # Parse SQLAlchemy URL to psycopg2 connection string
    # postgresql://user:pass@host:port/db?sslmode=require
    return psycopg2.connect(db_url)


def load_parquet_with_copy(file_path: str, trip_type: str, batch_size: int = 100000):
    """
    Load a parquet file using PostgreSQL COPY command - MUCH faster!
    
    Args:
        file_path: Path to the parquet file
        trip_type: One of 'yellow', 'green', 'fhv', 'fhvhv'
        batch_size: Number of records to process at once
    """
    print(f"\nLoading {file_path}...")
    
    try:
        # Read parquet file
        df = pd.read_parquet(file_path)
        total_rows = len(df)
        print(f"  Found {total_rows:,} records")
        
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
        
        # Connect to PostgreSQL
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
            
            # Use COPY command - this is MUCH faster than INSERT
            copy_sql = f"""
                COPY {table_name} ({', '.join(columns)})
                FROM STDIN
                WITH (FORMAT CSV, DELIMITER E'\\t', NULL '\\N')
            """
            
            try:
                cur.copy_expert(copy_sql, buffer)
                conn.commit()
                
                loaded += len(batch_df)
                
                if loaded % 100000 == 0:
                    print(f"  Progress: {loaded:,} / {total_rows:,} ({loaded/total_rows*100:.1f}%)")
                    
            except Exception as e:
                conn.rollback()
                print(f"  Warning: Batch failed (likely duplicates): {e}")
                # Continue with next batch
        
        cur.close()
        conn.close()
        
        print(f"  ✓ Loaded {loaded:,} records")
        return loaded
        
    except Exception as e:
        print(f"  ✗ Error loading {file_path}: {e}")
        import traceback
        traceback.print_exc()
        return 0


def load_all_files(data_dir: str, trip_types: list = None, year_filter: int = None):
    """
    Load all parquet files from the data directory using fast COPY method
    
    Args:
        data_dir: Directory containing parquet files
        trip_types: List of trip types to load (default: all)
        year_filter: Only load files from this year (default: all years)
    """
    if trip_types is None:
        trip_types = ['yellow', 'green', 'fhv', 'fhvhv']
    
    print("=" * 60)
    print("TLC Trip Data Loader (Fast COPY Method)")
    print("=" * 60)
    
    total_loaded = 0
    total_files = 0
    start_time = datetime.now()
    
    for trip_type in trip_types:
        pattern = f"{data_dir}/{trip_type}_tripdata_*.parquet"
        files = sorted(glob.glob(pattern))
        
        if year_filter:
            files = [f for f in files if f"{year_filter}-" in f]
        
        if not files:
            print(f"\nNo files found for {trip_type} trips")
            continue
        
        print(f"\n{trip_type.upper()} TRIPS: Found {len(files)} files")
        
        for file_path in files:
            loaded = load_parquet_with_copy(file_path, trip_type)
            total_loaded += loaded
            total_files += 1
    
    # Refresh materialized views
    print("\n" + "=" * 60)
    print("Refreshing materialized views...")
    with engine.begin() as conn:
        print("  Refreshing trip_summary_view...")
        conn.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY trip_summary_view"))
        print("  ✓ trip_summary_view refreshed")
        
        print("  Refreshing daily_trip_aggregates...")
        conn.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY daily_trip_aggregates"))
        print("  ✓ daily_trip_aggregates refreshed")
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "=" * 60)
    print(f"COMPLETE!")
    print(f"  Files processed: {total_files}")
    print(f"  Records loaded: {total_loaded:,}")
    print(f"  Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    print(f"  Speed: {total_loaded/duration:,.0f} records/second")
    print("=" * 60)


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
        
        # Get date range
        result = conn.execute(text("""
            SELECT 
                MIN(LEAST(
                    (SELECT MIN(tpep_pickup_datetime) FROM yellow_trips),
                    (SELECT MIN(lpep_pickup_datetime) FROM green_trips),
                    (SELECT MIN(pickup_datetime) FROM fhv_trips),
                    (SELECT MIN(pickup_datetime) FROM fhvhv_trips)
                )) as min_date,
                MAX(GREATEST(
                    (SELECT MAX(tpep_pickup_datetime) FROM yellow_trips),
                    (SELECT MAX(lpep_pickup_datetime) FROM green_trips),
                    (SELECT MAX(pickup_datetime) FROM fhv_trips),
                    (SELECT MAX(pickup_datetime) FROM fhvhv_trips)
                )) as max_date
        """))
        
        date_range = result.fetchone()
        if date_range[0]:
            print(f"  Date range: {date_range[0]} to {date_range[1]}")
        print()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Load TLC trip data using fast COPY method')
    parser.add_argument('--data-dir', default='../tlc', help='Directory containing parquet files')
    parser.add_argument('--trip-types', nargs='+', choices=['yellow', 'green', 'fhv', 'fhvhv'],
                       help='Trip types to load (default: all)')
    parser.add_argument('--year', type=int, help='Only load data for specific year')
    parser.add_argument('--stats-only', action='store_true', help='Only show statistics, do not load')
    
    args = parser.parse_args()
    
    if args.stats_only:
        get_stats()
    else:
        load_all_files(args.data_dir, args.trip_types, args.year)
        get_stats()
