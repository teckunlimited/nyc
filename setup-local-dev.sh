#!/bin/bash
# Setup script for local development environment

set -e

echo "🚀 Setting up NYC TLC Local Development Environment"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker Desktop."
    exit 1
fi

echo "1️Starting local PostgreSQL database with auto-schema initialization..."
docker-compose down -v  # Clean start
docker-compose up -d db

echo "Waiting for database to be ready and schema to initialize..."
sleep 5
until docker-compose exec -T db pg_isready -U postgres > /dev/null 2>&1; do
    sleep 1
done

# Give schema initialization time to complete
echo "Waiting for schema initialization to complete..."
sleep 3

echo "Database is ready with schema initialized!"

echo ""
echo "2️Verifying schema..."
docker-compose exec -T db psql -U postgres -d nycdb -c "\dt" | head -20

echo ""
echo "3️⃣  Loading taxi zone lookup data..."
cd backend
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/nycdb"

# Check if table is already populated
ZONE_COUNT=$(PGPASSWORD=postgres psql -h localhost -U postgres -d nycdb -t -c "SELECT COUNT(*) FROM taxi_zone_lookup;" | xargs)
if [ "$ZONE_COUNT" -gt 0 ] 2>/dev/null; then
    echo "  Taxi zones already loaded ($ZONE_COUNT zones) ✅"
elif [ -f "../tlc/taxi_zone_lookup.csv" ]; then
    echo "  Using local taxi zone file..."
    python3 -c "
from database import engine
import pandas as pd

df = pd.read_csv('../tlc/taxi_zone_lookup.csv')
df.columns = df.columns.str.lower().str.replace('locationid', 'location_id')
df.to_sql('taxi_zone_lookup', engine, if_exists='append', index=False)
print(f'✅ Loaded {len(df)} taxi zones from local file')
"
else
    echo "  Downloading taxi zone data..."
    python3 -c "
from database import engine
import pandas as pd

url = 'https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv'
df = pd.read_csv(url)
df.columns = df.columns.str.lower().str.replace('locationid', 'location_id')
df.to_sql('taxi_zone_lookup', engine, if_exists='append', index=False)
print(f'✅ Loaded {len(df)} taxi zones')
"
fi


echo ""
echo "4️⃣  Loading sample trip data (3,000 records each from 2025)..."
python3 << 'PYTHON_SCRIPT'
from database import engine
import pandas as pd
import os
from sqlalchemy import text

def load_sample_from_file(file_path, table_name, limit=3000):
    """Load limited records from local parquet file"""
    try:
        print(f"  Loading {table_name} from {os.path.basename(file_path)}...")
        
        # Read parquet file
        df = pd.read_parquet(file_path)
        
        # Take first N records
        df_sample = df.head(limit)
        
        # Normalize column names
        df_sample.columns = df_sample.columns.str.lower()
        
        # Load to database
        df_sample.to_sql(table_name, engine, if_exists='append', index=False)
        print(f"  ✅ Loaded {len(df_sample)} records")
        return len(df_sample)
    except Exception as e:
        print(f"  ⚠️  Could not load {os.path.basename(file_path)}: {e}")
        return 0

# Local file paths (2025 data - Jan, Feb, Mar)
data_dir = "../tlc"
samples = [
    (f"{data_dir}/yellow_tripdata_2025-01.parquet", "yellow_trips"),
    (f"{data_dir}/green_tripdata_2025-01.parquet", "green_trips"),
    (f"{data_dir}/fhv_tripdata_2025-01.parquet", "fhv_trips"),
    (f"{data_dir}/fhvhv_tripdata_2025-01.parquet", "fhvhv_trips"),
    (f"{data_dir}/yellow_tripdata_2025-02.parquet", "yellow_trips"),
    (f"{data_dir}/green_tripdata_2025-02.parquet", "green_trips"),
    (f"{data_dir}/fhv_tripdata_2025-02.parquet", "fhv_trips"),
    (f"{data_dir}/fhvhv_tripdata_2025-02.parquet", "fhvhv_trips"),
    (f"{data_dir}/yellow_tripdata_2025-03.parquet", "yellow_trips"),
    (f"{data_dir}/green_tripdata_2025-03.parquet", "green_trips"),
    (f"{data_dir}/fhv_tripdata_2025-03.parquet", "fhv_trips"),
    (f"{data_dir}/fhvhv_tripdata_2025-03.parquet", "fhvhv_trips"),
]

total = 0
for file_path, table in samples:
    if os.path.exists(file_path):
        count = load_sample_from_file(file_path, table, limit=3000)
        total += count
    else:
        print(f"  ⚠️  File not found: {os.path.basename(file_path)}")

print(f"\n✅ Total sample records loaded: {total:,}")

# Show record counts
with engine.connect() as conn:
    print("\nRecord counts by trip type:")
    for table in ["yellow_trips", "green_trips", "fhv_trips", "fhvhv_trips"]:
        result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
        count = result.scalar()
        print(f"  {table}: {count:,}")

# Refresh materialized views
print("\n5️⃣  Refreshing materialized views...")
with engine.connect() as conn:
    conn.execute(text("REFRESH MATERIALIZED VIEW trip_summary_view"))
    conn.execute(text("REFRESH MATERIALIZED VIEW daily_trip_aggregates"))
    conn.commit()
print("✅ Views refreshed")
PYTHON_SCRIPT

echo ""
echo "Local development environment is ready!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Database Summary:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  • 265 Taxi Zones (reference data)"
echo "  • ~3,000 Yellow Taxi trips (Jan-Mar 2025)"
echo "  • ~3,000 Green Taxi trips (Jan-Mar 2025)"
echo "  • ~3,000 FHV trips (Jan-Mar 2025)"
echo "  • ~3,000 FHVHV trips (Jan-Mar 2025)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Next Steps:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Start Backend:"
echo "  cd backend"
echo "  source venv/bin/activate"
echo "  uvicorn main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "Start Frontend:"
echo "  cd frontend"
echo "  npm start"
echo ""
echo "Load More Data (optional):"
echo "  cd backend"
echo "  python3 load_data_safe.py --data-dir ../tlc/data"
echo ""
echo "View Sample Data:"
echo "  http://localhost:8000/docs"
echo "  Try: GET /api/trips?limit=10"
echo ""
echo "Database Connection:"
echo "  postgresql://postgres:postgres@localhost:5432/nycdb"
echo ""
echo "Stop Database:"
echo "  docker-compose down"
echo ""
