#!/bin/bash
# Upload parquet files to Azure Blob Storage

set -e

echo "📤 Uploading Parquet Files to Azure Blob Storage"
echo "================================================"

# Configuration
RESOURCE_GROUP="nyc-dev-rg"
STORAGE_ACCOUNT="nycdevstorage$(date +%s | tail -c 6)"
CONTAINER_NAME="tlc-data"
LOCAL_DATA_DIR="../tlc"

echo ""
echo "📦 Step 1: Creating Storage Account..."
az storage account create \
  --name $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --location westus \
  --sku Standard_LRS \
  --kind StorageV2

echo ""
echo "🔑 Step 2: Getting Storage Account Key..."
STORAGE_KEY=$(az storage account keys list \
  --resource-group $RESOURCE_GROUP \
  --account-name $STORAGE_ACCOUNT \
  --query "[0].value" -o tsv)

echo ""
echo "📁 Step 3: Creating Blob Container..."
az storage container create \
  --name $CONTAINER_NAME \
  --account-name $STORAGE_ACCOUNT \
  --account-key $STORAGE_KEY \
  --public-access off

echo ""
echo "⬆️  Step 4: Uploading Files..."
echo "This will take several minutes..."

# Upload taxi zone lookup CSV first
echo "Uploading taxi_zone_lookup.csv..."
if [ -f "$LOCAL_DATA_DIR/taxi_zone_lookup.csv" ]; then
    az storage blob upload \
      --account-name $STORAGE_ACCOUNT \
      --account-key $STORAGE_KEY \
      --container-name $CONTAINER_NAME \
      --name "taxi_zone_lookup.csv" \
      --file "$LOCAL_DATA_DIR/taxi_zone_lookup.csv" \
      --overwrite \
      --no-progress
    echo "✓ Uploaded taxi_zone_lookup.csv"
fi

# Count total parquet files
TOTAL_FILES=$(ls -1 $LOCAL_DATA_DIR/*.parquet 2>/dev/null | wc -l)
echo "Found $TOTAL_FILES parquet files to upload"

# Upload all parquet files
COUNTER=0
for file in $LOCAL_DATA_DIR/*.parquet; do
    if [ -f "$file" ]; then
        FILENAME=$(basename "$file")
        COUNTER=$((COUNTER + 1))
        
        echo "[$COUNTER/$TOTAL_FILES] Uploading $FILENAME..."
        
        az storage blob upload \
          --account-name $STORAGE_ACCOUNT \
          --account-key $STORAGE_KEY \
          --container-name $CONTAINER_NAME \
          --name "$FILENAME" \
          --file "$file" \
          --overwrite \
          --no-progress
    fi
done

echo ""
echo "✅ Upload Complete!"
echo ""
echo "Storage Account: $STORAGE_ACCOUNT"
echo "Container: $CONTAINER_NAME"
echo "Total Files: $COUNTER"
echo ""
echo "Connection String (save this):"
az storage account show-connection-string \
  --name $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --query connectionString -o tsv

echo ""
echo "📝 Save these values for the next step:"
echo "STORAGE_ACCOUNT=$STORAGE_ACCOUNT"
echo "CONTAINER_NAME=$CONTAINER_NAME"
