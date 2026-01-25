#!/bin/bash
# Rotate database password after accidentally committing it

set -e

RESOURCE_GROUP="${1:-nyc-dev-rg}"
KEY_VAULT_NAME=$(az keyvault list --resource-group $RESOURCE_GROUP --query "[0].name" -o tsv)
DB_SERVER=$(az postgres flexible-server list --resource-group $RESOURCE_GROUP --query "[0].name" -o tsv)

if [ -z "$KEY_VAULT_NAME" ] || [ -z "$DB_SERVER" ]; then
    echo "Error: Could not find Key Vault or PostgreSQL server in $RESOURCE_GROUP"
    exit 1
fi

echo "Rotating database password for $DB_SERVER"
echo "Resource Group: $RESOURCE_GROUP"
echo "Key Vault: $KEY_VAULT_NAME"
echo ""

# Grant current user permissions to Key Vault if needed
echo "Checking Key Vault permissions..."
CURRENT_USER=$(az account show --query user.name -o tsv)
CURRENT_USER_ID=$(az ad signed-in-user show --query id -o tsv 2>/dev/null || az account show --query user.name -o tsv)

echo "Granting permissions to $CURRENT_USER..."
az keyvault set-policy \
  --name $KEY_VAULT_NAME \
  --resource-group $RESOURCE_GROUP \
  --upn "$CURRENT_USER" \
  --secret-permissions get list set delete \
  --output none 2>/dev/null || \
az keyvault set-policy \
  --name $KEY_VAULT_NAME \
  --resource-group $RESOURCE_GROUP \
  --object-id "$CURRENT_USER_ID" \
  --secret-permissions get list set delete \
  --output none

echo "Permissions granted"
echo ""

# Generate new secure password
NEW_PASSWORD=$(openssl rand -base64 30 | tr -dc 'a-zA-Z0-9' | head -c 24)

# Update PostgreSQL server password
echo "Updating PostgreSQL server password..."
az postgres flexible-server update \
  --resource-group $RESOURCE_GROUP \
  --name $DB_SERVER \
  --admin-password "$NEW_PASSWORD"

# Update Key Vault secret
echo "Updating Key Vault secret 'db-password'..."
az keyvault secret set \
  --vault-name $KEY_VAULT_NAME \
  --name db-password \
  --value "$NEW_PASSWORD" \
  --output none

# Build and store new DATABASE_URL
DB_HOST="${DB_SERVER}.postgres.database.azure.com"
NEW_DATABASE_URL="postgresql://nycadmin:${NEW_PASSWORD}@${DB_HOST}:5432/nycdb?sslmode=require"

echo "Updating Key Vault secret 'DATABASE-URL'..."
az keyvault secret set \
  --vault-name $KEY_VAULT_NAME \
  --name DATABASE-URL \
  --value "$NEW_DATABASE_URL" \
  --output none

# Update storage connection string in Key Vault (refresh from current storage account)
echo "Refreshing storage connection string in Key Vault..."
STORAGE_ACCOUNT=$(az storage account list --resource-group $RESOURCE_GROUP --query "[0].name" -o tsv)
if [ -n "$STORAGE_ACCOUNT" ]; then
  STORAGE_CONNECTION=$(az storage account show-connection-string \
    --name $STORAGE_ACCOUNT \
    --resource-group $RESOURCE_GROUP \
    --query connectionString -o tsv)
  
  az keyvault secret set \
    --vault-name $KEY_VAULT_NAME \
    --name storage-connection \
    --value "$STORAGE_CONNECTION" \
    --output none
  echo "Storage connection string updated in Key Vault"
else
  echo "WARNING: No storage account found in $RESOURCE_GROUP"
fi

echo ""
echo "Password rotated successfully!"
echo ""
echo "Updating Container Apps with new connection string..."

# Get all container apps in the resource group
APPS=$(az containerapp list --resource-group $RESOURCE_GROUP --query "[].name" -o tsv)

if [ -z "$APPS" ]; then
    echo "WARNING: No Container Apps found in $RESOURCE_GROUP"
else
    for APP in $APPS; do
        echo "  Updating $APP..."
        az containerapp update \
          --name $APP \
          --resource-group $RESOURCE_GROUP \
          --set-env-vars DATABASE_URL="$NEW_DATABASE_URL" \
          --output none 2>/dev/null || echo "    WARNING: Skipped $APP (may not use DATABASE_URL)"
        
        # Force restart to apply new password
        echo "    Restarting $APP to apply new password..."
        az containerapp revision restart \
          --name $APP \
          --resource-group $RESOURCE_GROUP \
          --output none 2>/dev/null || echo "    INFO: Restart not needed (app will reload automatically)"
    done
    echo "  Container Apps updated and restarted"
fi

echo ""
echo "Checking for data loader jobs..."
JOBS=$(az containerapp job list --resource-group $RESOURCE_GROUP --query "[].name" -o tsv)

if [ -z "$JOBS" ]; then
    echo "  No Container App Jobs found in $RESOURCE_GROUP"
else
    for JOB in $JOBS; do
        echo "  Updating $JOB secrets..."
        # Jobs use secrets, need to update both database and storage secrets
        UPDATE_CMD="az containerapp job update --name $JOB --resource-group $RESOURCE_GROUP"
        
        # Update database secret
        $UPDATE_CMD --replace-secrets "database-url=$NEW_DATABASE_URL" --output none 2>/dev/null || echo "      Database secret update skipped"
        
        # Update storage secret if we have a storage account
        if [ -n "$STORAGE_ACCOUNT" ] && [ -n "$STORAGE_CONNECTION" ]; then
          $UPDATE_CMD --replace-secrets "storage-connection=$STORAGE_CONNECTION" --output none 2>/dev/null || echo "      Storage secret update skipped"
        fi
        
        echo "    $JOB secrets updated"
    done
    echo "  All jobs updated"
fi

echo ""
echo "All services updated with new password!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "NEW DATABASE CREDENTIALS (Store Securely)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Database Server:  $DB_HOST"
echo "Database Name:    nycdb"
echo "Admin User:       nycadmin"
echo "New Password:     $NEW_PASSWORD"
echo ""
echo "Connection String:"
echo "$NEW_DATABASE_URL"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Password is also stored in Key Vault: $KEY_VAULT_NAME"
echo "   Secret names: 'db-password' and 'DATABASE-URL'"
echo ""
echo "Test connectivity:"
echo "  Backend health: Check your backend app /health endpoint"
echo "  Direct test:    psql \"$NEW_DATABASE_URL\" -c 'SELECT version();'"
