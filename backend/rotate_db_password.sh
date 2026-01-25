#!/bin/bash
# Rotate database password after accidentally committing it

set -e

RESOURCE_GROUP="${1:-nyc-dev-rg}"
KEY_VAULT_NAME=$(az keyvault list --resource-group $RESOURCE_GROUP --query "[0].name" -o tsv)
DB_SERVER=$(az postgres flexible-server list --resource-group $RESOURCE_GROUP --query "[0].name" -o tsv)

if [ -z "$KEY_VAULT_NAME" ] || [ -z "$DB_SERVER" ]; then
    echo "❌ Error: Could not find Key Vault or PostgreSQL server in $RESOURCE_GROUP"
    exit 1
fi

echo "🔄 Rotating database password for $DB_SERVER"
echo "Resource Group: $RESOURCE_GROUP"
echo "Key Vault: $KEY_VAULT_NAME"
echo ""

# Generate new secure password
NEW_PASSWORD=$(openssl rand -base64 30 | tr -dc 'a-zA-Z0-9' | head -c 24)

# Update PostgreSQL server password
echo "📝 Updating PostgreSQL server password..."
az postgres flexible-server update \
  --resource-group $RESOURCE_GROUP \
  --name $DB_SERVER \
  --admin-password "$NEW_PASSWORD"

# Update Key Vault secret
echo "🔐 Updating Key Vault secret 'db-password'..."
az keyvault secret set \
  --vault-name $KEY_VAULT_NAME \
  --name db-password \
  --value "$NEW_PASSWORD" \
  --output none

# Build and store new DATABASE_URL
DB_HOST="${DB_SERVER}.postgres.database.azure.com"
NEW_DATABASE_URL="postgresql://nycadmin:${NEW_PASSWORD}@${DB_HOST}:5432/nycdb?sslmode=require"

echo "🔐 Updating Key Vault secret 'DATABASE-URL'..."
az keyvault secret set \
  --vault-name $KEY_VAULT_NAME \
  --name DATABASE-URL \
  --value "$NEW_DATABASE_URL" \
  --output none

echo ""
echo "✅ Password rotated successfully!"
echo ""
echo "⚠️  Action required:"
echo "1. Update any running Container Apps with the new connection string"
echo "2. Restart data loader jobs"
echo "3. Test connectivity"
echo ""
echo "To update Container Apps:"
echo "  az containerapp update --name <app-name> --resource-group $RESOURCE_GROUP \\"
echo "    --set-env-vars DATABASE_URL=@$KEY_VAULT_NAME/DATABASE-URL"
