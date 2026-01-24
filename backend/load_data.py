"""
Data loader for TLC trip parquet files
Efficiently loads trip data into PostgreSQL with batch processing
"""
import os
import sys
import glob
from pathlib import Path
import pandas as pd
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from database import engine, SessionLocal
from models import YellowTripData, GreenTripData, FHVTripData, FHVHVTripData
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


def load_parquet_batch(file_path: str, trip_type: str, batch_size: int = 50000):
    """
    Load a parquet file into the database in batches
    
    Args:
        file_path: Path to the parquet file
        trip_type: One of 'yellow', 'green', 'fhv', 'fhvhv'
        batch_size: Number of records to insert at once
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
        
        # Data cleaning
        # Replace NaN with None for proper NULL handling
        df = df.where(pd.notnull(df), None)
        
        # Convert to records for bulk insert
        records = df.to_dict('records')
        
        # Insert in batches using pandas to_sql with if_exists='append'
        # This is more efficient and handles duplicates gracefully
        loaded = 0
        for i in range(0, len(records), batch_size):
            batch_df = df.iloc[i:i + batch_size]
            
            # Use to_sql with if_exists='append' - it's faster and avoids duplicates via transaction
            batch_df.to_sql(
                table_name,
                engine,
                if_exists='append',
                index=False,
                method='multi',
                chunksize=1000
            )
            
            loaded += len(batch_df)
            
            if loaded % 100000 == 0:
                print(f"  Progress: {loaded:,} / {total_rows:,} ({loaded/total_rows*100:.1f}%)")
        
        print(f"  ✓ Loaded {loaded:,} records")
        return loaded
        
    except Exception as e:
        print(f"  ✗ Error loading {file_path}: {e}")
        return 0


def load_all_files(data_dir: str, trip_types: list = None, year_filter: int = None):
    """
    Load all parquet files from the data directory
    
    Args:
        data_dir: Directory containing parquet files
        trip_types: List of trip types to load (default: all)
        year_filter: Only load files from this year (default: all years)
    """
    if trip_types is None:
        trip_types = ['yellow', 'green', 'fhv', 'fhvhv']
    
    print("=" * 60)
    print("TLC Trip Data Loader")
    print("=" * 60)
    
    total_loaded = 0
    total_files = 0
    
    for trip_type in trip_types:
        pattern = f"{data_dir}/{trip_type}_tripdata_*.parquet"
        files = sorted(glob.glob(pattern))
        
        if year_filter:
            files = [f for f in files if f"{year_filter}-" in f]
        
        print(f"\n{trip_type.upper()} Trips: Found {len(files)} files")
        
        for file_path in files:
            total_files += 1
            loaded = load_parquet_batch(file_path, trip_type)
            total_loaded += loaded
    
    print("\n" + "=" * 60)
    print(f"✓ Load complete!")
    print(f"  Files processed: {total_files}")
    print(f"  Total records loaded: {total_loaded:,}")
    print("=" * 60)
    
    # Refresh materialized views
    print("\nRefreshing materialized views...")
    with engine.begin() as conn:
        print("  Refreshing trip_summary_view...")
        conn.execute(text("REFRESH MATERIALIZED VIEW trip_summary_view"))
        print("  ✓ trip_summary_view refreshed")
        
        print("  Refreshing daily_trip_aggregates...")
        conn.execute(text("REFRESH MATERIALIZED VIEW daily_trip_aggregates"))
        print("  ✓ daily_trip_aggregates refreshed")
    
    print("✓ All materialized views refreshed")


def get_load_stats():
    """Display current database statistics"""
    print("\n" + "=" * 60)
    print("Database Statistics")
    print("=" * 60)
    
    with engine.connect() as conn:
        for table in ['yellow_trips', 'green_trips', 'fhv_trips', 'fhvhv_trips']:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            print(f"{table:20s}: {count:>15,} records")
        
        # Get date range
        for table, date_col in [
            ('yellow_trips', 'tpep_pickup_datetime'),
            ('green_trips', 'lpep_pickup_datetime'),
            ('fhv_trips', 'pickup_datetime'),
            ('fhvhv_trips', 'pickup_datetime')
        ]:
            result = conn.execute(text(f"""
                SELECT MIN({date_col}), MAX({date_col}) 
                FROM {table} 
                WHERE {date_col} IS NOT NULL
            """))
            row = result.fetchone()
            if row and row[0]:
                print(f"{table:20s}: {row[0]} to {row[1]}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Load TLC trip data into PostgreSQL')
    parser.add_argument('--data-dir', default='../tlc', help='Directory containing parquet files')
    parser.add_argument('--trip-types', nargs='+', choices=['yellow', 'green', 'fhv', 'fhvhv'],
                       help='Trip types to load (default: all)')
    parser.add_argument('--year', type=int, help='Only load data from this year')
    parser.add_argument('--stats-only', action='store_true', help='Only display statistics')
    
    args = parser.parse_args()
    
    if args.stats_only:
        get_load_stats()
    else:
        load_all_files(args.data_dir, args.trip_types, args.year)
        get_load_stats()
