#!/bin/bash
"""
Start multiple container jobs for different trip types
"""

echo "🚀 Starting Multiple Trip Type Loaders"
echo "====================================="

# Configuration
RESOURCE_GROUP="nyc-dev-rg"
JOB_NAME="nyc-data-loader-job"

echo "📋 Trip Type Loading Plan:"
echo "  🟢 Green: nyc-2024-data container (12 files)"
echo "  🟡 Yellow: tlc-data container (2024 files)" 
echo "  🔵 FHV: fhv-2024-data container (12 files)"
echo "  🟣 FHVHV: tlc-data container (2024 files)"
echo ""

# Function to start a job with specific config
start_trip_loader() {
    local trip_type=$1
    local container=$2
    local limit=$3
    
    echo "🔄 Starting $trip_type loader..."
    
    # Update job configuration
    az containerapp job update \
        --name $JOB_NAME \
        --resource-group $RESOURCE_GROUP \
        --set-env-vars CONTAINER_NAME=$container LOAD_YEAR=2024 TRIP_TYPES=$trip_type LIMIT_RECORDS=$limit \
        --quiet
    
    # Start the job
    execution_result=$(az containerapp job start \
        --name $JOB_NAME \
        --resource-group $RESOURCE_GROUP \
        --query "name" -o tsv)
    
    echo "  ✅ $trip_type loader started: $execution_result"
    sleep 2  # Small delay between starts
}

# Start each trip type loader
echo "🚀 Starting loaders sequentially..."
echo ""

# 1. Green trips from nyc-2024-data
start_trip_loader "green" "nyc-2024-data" "5000000"

# 2. FHV trips from fhv-2024-data  
start_trip_loader "fhv" "fhv-2024-data" "5000000"

# 3. Yellow trips from tlc-data
start_trip_loader "yellow" "tlc-data" "5000000"

echo ""
echo "🎉 All loaders started!"
echo ""
echo "📊 Check progress with:"
echo "  az containerapp job execution list --name $JOB_NAME --resource-group $RESOURCE_GROUP --output table"
echo ""
echo "📈 Monitor database with:"
echo "  python3 load_data_safe.py --stats-only"