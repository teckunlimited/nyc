"""
Load NYC Taxi Zone Lookup data into PostgreSQL
Downloads and imports the official zone lookup table from NYC TLC
"""
import pandas as pd
import requests
from sqlalchemy import text
from database import engine
from models import TaxiZoneLookup

# NYC TLC Taxi Zone Lookup URL
ZONE_LOOKUP_URL = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zones.zip"
ZONE_LOOKUP_CSV = "taxi_zone_lookup.csv"


def download_zone_lookup():
    """Download and extract the taxi zone lookup CSV"""
    print("Downloading Taxi Zone Lookup data...")
    
    try:
        import io
        import zipfile
        
        # Download the zip file
        response = requests.get(ZONE_LOOKUP_URL)
        response.raise_for_status()
        
        # Extract the CSV from the zip
        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
            # Find the lookup CSV file
            csv_files = [f for f in zip_file.namelist() if f.endswith('.csv') and 'lookup' in f.lower()]
            if not csv_files:
                raise ValueError("Could not find zone lookup CSV in downloaded file")
            
            # Read the CSV
            with zip_file.open(csv_files[0]) as csv_file:
                df = pd.read_csv(csv_file)
        
        print(f"✓ Downloaded {len(df)} zone records")
        return df
        
    except Exception as e:
        print(f"✗ Error downloading zone lookup: {e}")
        print("\nTrying alternative: loading from local file...")
        return None


def load_from_csv(csv_path: str = None):
    """Load zone lookup from a local CSV file"""
    if csv_path is None:
        csv_path = ZONE_LOOKUP_CSV
    
    try:
        df = pd.read_csv(csv_path)
        print(f"✓ Loaded {len(df)} zone records from {csv_path}")
        return df
    except Exception as e:
        print(f"✗ Error loading from CSV: {e}")
        return None


def clean_zone_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and normalize zone lookup data"""
    # Normalize column names to match our schema
    column_mapping = {
        'LocationID': 'location_id',
        'Borough': 'borough',
        'Zone': 'zone',
        'service_zone': 'service_zone'
    }
    
    # Only rename columns that exist in the dataframe
    available_columns = {k: v for k, v in column_mapping.items() if k in df.columns}
    df = df.rename(columns=available_columns)
    
    # Ensure we have the required columns
    required_columns = ['location_id', 'borough', 'zone', 'service_zone']
    for col in required_columns:
        if col not in df.columns:
            # Try to find alternative column names
            alt_names = {
                'location_id': ['LocationID', 'locationid', 'location_id'],
                'borough': ['Borough'],
                'zone': ['Zone'],
                'service_zone': ['service_zone', 'ServiceZone', 'service zone']
            }
            found = False
            for alt in alt_names.get(col, []):
                if alt in df.columns:
                    df[col] = df[alt]
                    found = True
                    break
            if not found:
                print(f"Warning: Column {col} not found in data")
    
    # Replace NaN with None
    df = df.where(pd.notnull(df), None)
    
    return df[required_columns]


def load_zone_lookup_data(df: pd.DataFrame = None, csv_path: str = None):
    """Load taxi zone lookup data into the database"""
    print("=" * 60)
    print("Taxi Zone Lookup Data Loader")
    print("=" * 60)
    
    # Get the data
    if df is None:
        if csv_path:
            df = load_from_csv(csv_path)
        else:
            df = download_zone_lookup()
            if df is None:
                print("\n✗ Could not load zone lookup data")
                print("Please download manually from:")
                print(ZONE_LOOKUP_URL)
                return False
    
    # Clean the data
    print("\nCleaning zone data...")
    df = clean_zone_data(df)
    print(f"✓ Prepared {len(df)} records")
    
    # Load into database
    print("\nLoading into database...")
    try:
        # Clear existing data
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM taxi_zone_lookup"))
            print("✓ Cleared existing zone data")
        
        # Insert new data
        df.to_sql(
            'taxi_zone_lookup',
            engine,
            if_exists='append',
            index=False,
            method='multi'
        )
        
        print(f"✓ Loaded {len(df)} zone records")
        
        # Verify the load
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM taxi_zone_lookup"))
            count = result.scalar()
            print(f"\nVerification: {count} records in database")
            
            # Show sample data
            print("\nSample zone data:")
            result = conn.execute(text("""
                SELECT location_id, borough, zone, service_zone 
                FROM taxi_zone_lookup 
                ORDER BY location_id 
                LIMIT 5
            """))
            for row in result:
                print(f"  {row[0]}: {row[2]} ({row[1]}) - {row[3]}")
        
        print("\n" + "=" * 60)
        print("✓ Zone lookup data loaded successfully!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"✗ Error loading zone data: {e}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Load NYC Taxi Zone Lookup data')
    parser.add_argument('--csv', help='Path to local zone lookup CSV file')
    parser.add_argument('--download', action='store_true', help='Download from NYC TLC website')
    
    args = parser.parse_args()
    
    if args.csv:
        load_zone_lookup_data(csv_path=args.csv)
    else:
        load_zone_lookup_data()
