#!/bin/bash

echo "🚀 Loading Trip Data Sequentially (One Type at a Time)"
echo "======================================================"

RESOURCE_GROUP="nyc-dev-rg"
JOB_NAME="nyc-data-loader-job"

load_trip_type() {
    local trip_type=$1
    local container=$2
    
    echo "🔄 Loading $trip_type from $container..."
    
    # Update job with specific configuration
    az containerapp job update \
        --name $JOB_NAME \
        --resource-group $RESOURCE_GROUP \
        --set-env-vars CONTAINER_NAME=$container LOAD_YEAR=2024 TRIP_TYPES=$trip_type LIMIT_RECORDS=5000000 \
        >/dev/null 2>&1
    
    # Start job and wait for completion
    execution_id=$(az containerapp job start \
        --name $JOB_NAME \
        --resource-group $RESOURCE_GROUP \
        --query "name" -o tsv)
    
    echo "  ⏳ Execution ID: $execution_id"
    
    # Wait for job to complete
    echo "  ⏳ Waiting for completion..."
    while true; do
        status=$(az containerapp job execution show \
            --name $JOB_NAME \
            --job-execution-name $execution_id \
            --resource-group $RESOURCE_GROUP \
            --query "properties.status" -o tsv)
        
        case $status in
            "Succeeded")
                echo "  ✅ $trip_type completed successfully"
                break
                ;;
            "Failed")
                echo "  ❌ $trip_type failed"
                echo "  🔍 Check logs with: az containerapp job logs show --name $JOB_NAME --resource-group $RESOURCE_GROUP --container $JOB_NAME --execution $execution_id"
                break
                ;;
            "Running"|"Pending")
                echo "  ⏳ Status: $status - waiting..."
                sleep 30
                ;;
            *)
                echo "  ❓ Unknown status: $status"
                sleep 30
                ;;
        esac
    done
    
    echo ""
}

# Load each trip type sequentially to avoid environment variable conflicts
load_trip_type "green" "nyc-2024-data"
load_trip_type "fhv" "fhv-2024-data" 
load_trip_type "fhvhv" "fhvhv-2024-data"
load_trip_type "yellow" "yellow-2024-data"

echo "🎉 All trip types processed!"
echo "Check database status to verify data loaded into correct tables."