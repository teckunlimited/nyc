"""
Azure Blob Storage loader - downloads from blob and loads to PostgreSQL
Designed to run in Azure Container App for fast in-region data loading
"""
import os
import sys
import glob
import io
from pathlib import Path
import pandas as pd
import psycopg2
from io import StringIO
from sqlalchemy import text
from database import engine
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from azure.storage.blob import BlobServiceClient
import time

# Thread-safe counter
stats_lock = Lock()
total_loaded = 0
total_files = 0
total_downloaded = 0

# Column mappings (same as before)
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


def get_blob_service_client():
    """Get Azure Blob Storage client"""
    connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    if not connection_string:
        raise ValueError("AZURE_STORAGE_CONNECTION_STRING environment variable not set")
    return BlobServiceClient.from_connection_string(connection_string)


def download_blob(blob_name: str, container_name: str, local_path: str):
    """Download a blob to local file"""
    global total_downloaded
    
    try:
        blob_service = get_blob_service_client()
        blob_client = blob_service.get_blob_client(container=container_name, blob=blob_name)
        
        with open(local_path, "wb") as download_file:
            download_file.write(blob_client.download_blob().readall())
        
        with stats_lock:
            total_downloaded += 1
        
        return True
    except Exception as e:
        print(f"✗ Error downloading {blob_name}: {e}")
        return False


def get_postgres_connection():
    """Get a raw psycopg2 connection for COPY command"""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        raise ValueError("DATABASE_URL environment variable not set")
    return psycopg2.connect(db_url)


def load_single_file(file_path: str, trip_type: str, batch_size: int = 50000):
    """Load a single parquet file using PostgreSQL COPY command"""
    global total_loaded, total_files
    
    file_name = os.path.basename(file_path)
    start_time = time.time()
    
    try:
        df = pd.read_parquet(file_path)
        total_rows = len(df)
        
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
        
        available_columns = {k: v for k, v in column_map.items() if k in df.columns}
        df = df[list(available_columns.keys())]
        df.rename(columns=available_columns, inplace=True)
        df = df.where(pd.notnull(df), None)
        
        columns = list(df.columns)
        conn = get_postgres_connection()
        cur = conn.cursor()
        
        loaded = 0
        
        for i in range(0, len(df), batch_size):
            batch_df = df.iloc[i:i + batch_size]
            buffer = StringIO()
            batch_df.to_csv(buffer, index=False, header=False, sep='\t', na_rep='\\N')
            buffer.seek(0)
            
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
        
        cur.close()
        conn.close()
        
        # Clean up downloaded file
        os.remove(file_path)
        
        duration = time.time() - start_time
        speed = loaded / duration if duration > 0 else 0
        
        with stats_lock:
            total_loaded += loaded
            total_files += 1
        
        print(f"✓ {file_name}: {loaded:,} records in {duration:.1f}s ({speed:,.0f} rec/s)")
        return loaded
        
    except Exception as e:
        print(f"✗ {file_name}: Error - {e}")
        return 0


def process_blob(blob_name: str, container_name: str, trip_type: str, temp_dir: str):
    """Download blob and load it"""
    local_path = os.path.join(temp_dir, blob_name)
    
    # Download
    if not download_blob(blob_name, container_name, local_path):
        return 0
    
    # Load
    return load_single_file(local_path, trip_type)


def load_from_azure_blob(container_name: str, trip_types: list = None, max_workers: int = 3, year_filter: int = None):
    """Load data from Azure Blob Storage in parallel"""
    global total_loaded, total_files, total_downloaded
    
    if trip_types is None:
        trip_types = ['yellow', 'green', 'fhv', 'fhvhv']
    
    print("=" * 80)
    print("Azure Blob Storage → PostgreSQL Data Loader")
    print(f"Container: {container_name}")
    print(f"Workers: {max_workers}")
    print("=" * 80)
    
    total_loaded = 0
    total_files = 0
    total_downloaded = 0
    overall_start = time.time()
    
    temp_dir = "/tmp/data"
    os.makedirs(temp_dir, exist_ok=True)
    
    blob_service = get_blob_service_client()
    container_client = blob_service.get_container_client(container_name)
    
    # First, check and load taxi zone lookup if needed
    print("\n📍 TAXI ZONE LOOKUP")
    print("-" * 40)
    try:
        conn = get_postgres_connection()
        cur = conn.cursor()
        
        # Ensure created_at column exists
        cur.execute("""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'taxi_zone_lookup' 
                    AND column_name = 'created_at'
                ) THEN
                    ALTER TABLE taxi_zone_lookup 
                    ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
                END IF;
            END $$;
        """)
        conn.commit()
        
        cur.execute("SELECT COUNT(*) FROM taxi_zone_lookup")
        existing_zones = cur.fetchone()[0]
        cur.close()
        conn.close()
        
        if existing_zones > 0:
            print(f"✓ Taxi zones already loaded ({existing_zones:,} zones)\n")
        else:
            zone_blob = container_client.get_blob_client("taxi_zone_lookup.csv")
            if zone_blob.exists():
                local_path = os.path.join(temp_dir, "taxi_zone_lookup.csv")
                
                # Download
                print("Downloading taxi_zone_lookup.csv...")
                with open(local_path, "wb") as download_file:
                    download_file.write(zone_blob.download_blob().readall())
                
                # Load using pandas and COPY
                import pandas as pd
                df = pd.read_csv(local_path)
                
                conn = get_postgres_connection()
                cur = conn.cursor()
                
                # Convert to TSV buffer
                buffer = io.StringIO()
                df.to_csv(buffer, sep='\t', index=False, header=False)
                buffer.seek(0)
                
                # Load with COPY - all columns from CSV
                copy_sql = "COPY taxi_zone_lookup (locationid, borough, zone, service_zone) FROM STDIN WITH (FORMAT text, DELIMITER E'\\t', NULL '')"
                cur.copy_expert(copy_sql, buffer)
                conn.commit()
                
                cur.close()
                conn.close()
                os.remove(local_path)
                
                print(f"✓ Loaded {len(df):,} taxi zones\n")
    except Exception as e:
        print(f"⚠️  Taxi zone lookup check/load error: {e}\n")
    
    # Now process trip data
    for trip_type in trip_types:
        print(f"\n{trip_type.upper()} TRIPS")
        print("-" * 80)
        
        # List blobs matching trip type
        prefix = f"{trip_type}_tripdata_"
        blobs = [blob.name for blob in container_client.list_blobs(name_starts_with=prefix)]
        
        if year_filter:
            blobs = [b for b in blobs if f"{year_filter}-" in b]
        
        if not blobs:
            print(f"No files found for {trip_type}")
            continue
        
        print(f"Found {len(blobs)} files")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(process_blob, blob_name, container_name, trip_type, temp_dir): blob_name
                for blob_name in blobs
            }
            
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"✗ Exception: {e}")
    
    overall_duration = time.time() - overall_start
    
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
    print(f"  Files downloaded: {total_downloaded}")
    print(f"  Files processed: {total_files}")
    print(f"  Records loaded: {total_loaded:,}")
    print(f"  Duration: {overall_duration:.1f}s ({overall_duration/60:.1f} min)")
    print(f"  Average speed: {total_loaded/overall_duration:,.0f} records/second")
    print("=" * 80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Load TLC data from Azure Blob Storage')
    parser.add_argument('--container', default='tlc-data', help='Azure blob container name')
    parser.add_argument('--trip-types', nargs='+', choices=['yellow', 'green', 'fhv', 'fhvhv'],
                       help='Trip types to load (default: all)')
    parser.add_argument('--workers', type=int, default=3,
                       help='Number of parallel workers (default: 3)')
    parser.add_argument('--year', type=int, help='Only load data for specific year')
    
    args = parser.parse_args()
    
    load_from_azure_blob(args.container, args.trip_types, args.workers, args.year)
