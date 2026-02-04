#!/bin/bash

echo "🚀 Starting Trip Type Loaders with Proper Configuration"
echo "======================================================"

RESOURCE_GROUP="nyc-dev-rg"
JOB_NAME="nyc-data-loader-job"

start_loader() {
    local trip_type=$1
    local container=$2
    
    echo "🔄 Starting $trip_type loader from $container..."
    
    # Update and start job
    az containerapp job update \
        --name $JOB_NAME \
        --resource-group $RESOURCE_GROUP \
        --set-env-vars CONTAINER_NAME=$container LOAD_YEAR=2024 TRIP_TYPES=$trip_type LIMIT_RECORDS=5000000 \
        >/dev/null 2>&1
    
    execution_id=$(az containerapp job start \
        --name $JOB_NAME \
        --resource-group $RESOURCE_GROUP \
        --query "name" -o tsv)
    
    echo "  ✅ $trip_type: $execution_id"
    sleep 5  # Wait between starts
}

# Start each trip type with dedicated container
start_loader "green" "nyc-2024-data"
start_loader "fhv" "fhv-2024-data" 
start_loader "fhvhv" "fhvhv-2024-data"
start_loader "yellow" "yellow-2024-data"

echo ""
echo "🎉 All 4 trip type loaders started!"
echo "Each job is configured to load from its specific container."