#!/bin/bash

echo "🚀 Loading 2024 Trip Data Sequentially"
echo "Each trip type will load into its correct table"
echo "======================================================"

RESOURCE_GROUP="nyc-dev-rg"
JOB_NAME="nyc-data-loader-job"

load_trip_type() {
    local trip_type=$1
    local container=$2
    
    echo ""
    echo "🔄 Loading $trip_type trips from $container..."
    
    # Update job configuration
    az containerapp job update \
        --name $JOB_NAME \
        --resource-group $RESOURCE_GROUP \
        --set-env-vars CONTAINER_NAME=$container LOAD_YEAR=2024 TRIP_TYPES=$trip_type LIMIT_RECORDS=5000000 \
        >/dev/null 2>&1
    
    # Start job
    execution_id=$(az containerapp job start \
        --name $JOB_NAME \
        --resource-group $RESOURCE_GROUP \
        --query "name" -o tsv)
    
    echo "  ✅ Started: $execution_id"
    
    # Monitor progress
    echo "  ⏳ Monitoring progress (will check every 2 minutes)..."
    
    while true; do
        status=$(az containerapp job execution show \
            --name $JOB_NAME \
            --job-execution-name $execution_id \
            --resource-group $RESOURCE_GROUP \
            --query "properties.status" -o tsv 2>/dev/null)
        
        case $status in
            "Succeeded")
                echo "  🎉 $trip_type loading completed successfully!"
                break
                ;;
            "Failed")
                echo "  ❌ $trip_type loading failed"
                echo "  📋 Check logs: az containerapp job logs show --name $JOB_NAME --resource-group $RESOURCE_GROUP --container $JOB_NAME --execution $execution_id"
                return 1
                ;;
            "Running")
                # Check database progress
                echo "  ⏳ Still running... checking database progress"
                cd /Users/joshperryman/NewAge/nyc/backend
                export DATABASE_URL="postgresql://nycadmin:8rx9ORdI0eBbnPv5LiaKGmwT@nyc-dev-dbfaff08.postgres.database.azure.com:5432/nycdb?sslmode=require"
                python3 -c "
from database import engine
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text('SELECT COUNT(*) FROM ${trip_type}_trips'))
    count = result.scalar()
    print(f'    📊 Current ${trip_type}_trips: {count:,} records')
"
                sleep 120  # Wait 2 minutes
                ;;
            *)
                echo "  ⏳ Status: $status - waiting..."
                sleep 30
                ;;
        esac
    done
    
    # Show final count for this trip type
    cd /Users/joshperryman/NewAge/nyc/backend
    export DATABASE_URL="postgresql://nycadmin:8rx9ORdI0eBbnPv5LiaKGmwT@nyc-dev-dbfaff08.postgres.database.azure.com:5432/nycdb?sslmode=require"
    python3 -c "
from database import engine
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text('SELECT COUNT(*) FROM ${trip_type}_trips'))
    count = result.scalar()
    print(f'  🏁 Final ${trip_type}_trips: {count:,} records')
"
}

# Load each trip type sequentially
load_trip_type "green" "nyc-2024-data"
load_trip_type "fhv" "fhv-2024-data" 
load_trip_type "fhvhv" "fhvhv-2024-data"
load_trip_type "yellow" "yellow-2024-data"

echo ""
echo "🎉 All trip types processed!"
echo "Final database status:"
cd /Users/joshperryman/NewAge/nyc/backend
export DATABASE_URL="postgresql://nycadmin:8rx9ORdI0eBbnPv5LiaKGmwT@nyc-dev-dbfaff08.postgres.database.azure.com:5432/nycdb?sslmode=require"
python3 load_data_safe.py --stats-only