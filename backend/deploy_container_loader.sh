#!/bin/bash
# Deploy data loader as Azure Container App Job

set -e

echo "🚀 Deploying Data Loader Container App"
echo "======================================"

# Configuration (UPDATE THESE)
RESOURCE_GROUP="nyc-dev-rg"
ACR_NAME="nycacrtakkd33nvzu2k"
IMAGE_NAME="nyc-data-loader"
JOB_NAME="nyc-data-loader-job"
CONTAINER_ENV="nyc-dev-env"

# Get these from upload script output
STORAGE_ACCOUNT="${1:-}"
CONTAINER_NAME="${2:-tlc-data}"

if [ -z "$STORAGE_ACCOUNT" ]; then
    echo "❌ Error: Storage account name required"
    echo "Usage: $0 <storage-account-name> [container-name]"
    echo ""
    echo "Run upload_to_azure.sh first and use the storage account name from output"
    exit 1
fi

DATABASE_URL="postgresql://nycadmin:Wg8zL7tt4lN05szaXGTD@nyc-dev-dbfaff08.postgres.database.azure.com:5432/nycdb?sslmode=require"

echo ""
echo "Configuration:"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  Storage Account: $STORAGE_ACCOUNT"
echo "  Container: $CONTAINER_NAME"
echo ""

# Step 1: Build and push Docker image
echo "📦 Step 1: Building Docker image..."
cd "$(dirname "$0")"
docker build -f Dockerfile.dataloader -t $ACR_NAME.azurecr.io/$IMAGE_NAME:latest .

echo ""
echo "🔐 Step 2: Logging into ACR..."
az acr login --name $ACR_NAME

echo ""
echo "📤 Step 3: Pushing image to ACR..."
docker push $ACR_NAME.azurecr.io/$IMAGE_NAME:latest

echo ""
echo "🔑 Step 4: Getting Storage Connection String..."
STORAGE_CONNECTION_STRING=$(az storage account show-connection-string \
  --name $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --query connectionString -o tsv)

echo ""
echo "🏗️  Step 5: Creating Container App Job..."

# Check if Container Environment exists
if ! az containerapp env show --name $CONTAINER_ENV --resource-group $RESOURCE_GROUP &>/dev/null; then
    echo "Creating Container App Environment..."
    az containerapp env create \
      --name $CONTAINER_ENV \
      --resource-group $RESOURCE_GROUP \
      --location westus
fi

# Delete existing job if it exists
az containerapp job delete \
  --name $JOB_NAME \
  --resource-group $RESOURCE_GROUP \
  --yes \
  2>/dev/null || true

# Create the job
az containerapp job create \
  --name $JOB_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINER_ENV \
  --trigger-type Manual \
  --replica-timeout 7200 \
  --replica-retry-limit 1 \
  --replica-completion-count 1 \
  --parallelism 1 \
  --image $ACR_NAME.azurecr.io/$IMAGE_NAME:latest \
  --cpu 4 \
  --memory 8Gi \
  --registry-server $ACR_NAME.azurecr.io \
  --registry-username $ACR_NAME \
  --registry-password $(az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv) \
  --secrets \
    database-url="$DATABASE_URL" \
    storage-connection-string="$STORAGE_CONNECTION_STRING" \
  --env-vars \
    DATABASE_URL=secretref:database-url \
    AZURE_STORAGE_CONNECTION_STRING=secretref:storage-connection-string

echo ""
echo "✅ Container App Job Created!"
echo ""
echo "▶️  To start the data loading job:"
echo "   az containerapp job start --name $JOB_NAME --resource-group $RESOURCE_GROUP"
echo ""
echo "📋 To view logs:"
echo "   az containerapp job execution list --name $JOB_NAME --resource-group $RESOURCE_GROUP --output table"
echo "   # Get execution name from above, then:"
echo "   az containerapp job logs show --name $JOB_NAME --resource-group $RESOURCE_GROUP --execution <execution-name>"
echo ""
echo "📊 To check just 2025 data:"
echo "   Update the job command to: --year 2025"
echo ""
