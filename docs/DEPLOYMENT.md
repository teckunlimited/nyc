# Deployment Guide

## Overview

Multi-environment CI/CD deployment to Azure Container Apps using GitHub Actions with automated infrastructure provisioning.

## Environments

### Production (main branch)
- **Branch:** `main`
- **Resource Group:** `nyc-prod-rg`
- **Backend:** `https://nyc-prod-backend.*.westus.azurecontainerapps.io`
- **Frontend:** `https://nyc-prod-frontend.*.westus.azurecontainerapps.io`
- **Database:** `nyc-prod-db-xxxxxxxx` (PostgreSQL 16)
- **Key Vault:** `nyc-prod-kv-xxxxxxxx`

### Staging (staging branch)
- **Branch:** `staging`
- **Resource Group:** `nyc-staging-rg`
- **Backend:** `https://nyc-staging-backend.*.westus.azurecontainerapps.io`
- **Frontend:** `https://nyc-staging-frontend.*.westus.azurecontainerapps.io`
- **Database:** `nyc-staging-db-xxxxxxxx` (PostgreSQL 16)
- **Key Vault:** `nyc-staging-kv-xxxxxxxx`

### Development (develop branch)
- **Branch:** `develop`
- **Resource Group:** `nyc-dev-rg`
- **Backend:** `https://nyc-dev-backend.*.westus.azurecontainerapps.io`
- **Frontend:** `https://nyc-dev-frontend.*.westus.azurecontainerapps.io`
- **Database:** `nyc-dev-db-xxxxxxxx` (PostgreSQL 16)
- **Key Vault:** `nyc-dev-kv-xxxxxxxx`

### Shared Resources
- **Container Registry:** `nycacrtakkd33nvzu2k.azurecr.io`
- **Resource Group:** `nyc-shared-rg`

---

## GitHub Actions Workflows

### CI Pipeline (`.github/workflows/ci.yml`)
**Triggers:** Pull requests to `main`, `develop`, `staging`

**Actions:**
- Python linting and backend tests (24 tests)
- Node.js build and frontend tests (47 tests)
- Dockerfile validation
- Security scanning with Trivy
- Frontend tests use `continue-on-error` to not block pipeline

### Deploy Pipeline (`.github/workflows/deploy.yml`)
**Triggers:** Push to `main`, `develop`, `staging` or manual dispatch

**Actions:**
1. Build Docker images for backend and frontend
2. Push images to Azure Container Registry
3. Deploy backend to Container Apps
4. Retrieve backend URL and inject into frontend
5. Deploy frontend with correct backend URL
6. Tag images based on environment (prod/staging/dev)

---

## Security Features

### Database Password Management
- **Auto-generated:** Unique 20-character secure passwords per environment
- **Key Vault:** Passwords stored securely, never in code or logs
- **Masked:** All sensitive values masked in GitHub Actions logs
- **Secure Injection:** Connection strings passed as environment variables

### API Security
- **Rate Limiting:** 100 req/min per IP for data endpoints
- **CORS:** Automatic allowlist for Azure Container Apps URLs via regex
- **HTTPS:** All Container Apps use HTTPS with automatic TLS certificates
- **Environment Variables:** Security settings configurable per environment

See [SECURITY.md](SECURITY.md) for comprehensive API security documentation.

---

## Setup

### Required GitHub Secrets

Configure these in **Settings → Secrets and variables → Actions**:

#### AZURE_CREDENTIALS

Create Azure Service Principal:

```bash
az ad sp create-for-rbac \
  --name "github-nyc-deployment" \
  --role contributor \
  --scopes /subscriptions/YOUR_SUB_ID/resourceGroups/nyc-app-rg \
  --sdk-auth
```

Save the JSON output as `AZURE_CREDENTIALS` secret:

```json
{
  "clientId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "clientSecret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "subscriptionId": "6d6a5fb5-b9fc-41bc-a4ec-08a2529e81d8",
  "tenantId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

### Expected Azure Resources

The workflows require:
- **Container Registry:** `nycacrtakkd33nvzu2k`
- **Subscription:** Active Azure subscription

All other resources (resource groups, Container Apps, databases, Key Vaults) are created automatically per environment.

---

## Deployment Flow

### 1. Backend Deployment
- Backend container deployed to Azure Container Apps
- Unique FQDN assigned (e.g., `nyc-prod-backend.victorioustree-xyz.westus.azurecontainerapps.io`)
- Database connection string injected from Key Vault

### 2. Frontend Configuration
- Pipeline retrieves backend FQDN
- Updates `frontend/nginx.conf` replacing `BACKEND_URL_PLACEHOLDER`
- Rebuilds frontend Docker image with environment-specific backend URL

### 3. Frontend Deployment
- Frontend container deployed with correct backend URL
- Each environment's frontend points to its own backend

### 4. Resource Management
- **Auto-creation:** Resource groups and environments created if missing
- **Isolation:** Each environment completely isolated
- **Location:** All resources deploy to `westus` region

---

## Usage

### Deploy to Environment

```bash
# Development
git checkout develop
git push origin develop

# Staging
git checkout staging
git push origin staging

# Production
git checkout main
git push origin main
```

### Manual Deployment

1. Go to **Actions** tab in GitHub
2. Select **Deploy to Azure** workflow
3. Click **Run workflow**
4. Select branch to deploy

### First Deployment Per Environment

On first deployment:
1. Resource group created
2. Log Analytics workspace provisioned
3. Container Apps environment set up
4. PostgreSQL database created with secure password
5. Key Vault provisioned and password stored
6. Backend and frontend apps deployed

### Subsequent Deployments

Future deployments:
1. Existing resources reused
2. Container images updated
3. Zero-downtime rollout

---

## Configuration

### Environment Variables

Each Container App receives:

**Backend:**
- `DATABASE_URL` - PostgreSQL connection (from Key Vault)
- `CORS_ORIGINS` - Allowed origins (automatically includes Azure URLs)
- `RATE_LIMIT_PER_MINUTE` - Rate limit (default: 100)
- `ENVIRONMENT` - `production`, `staging`, or `development`

**Frontend:**
- `BACKEND_URL` - Backend API URL (auto-injected)

### Database Configuration

**PostgreSQL Flexible Server:**
- Version: PostgreSQL 16
- Tier: Burstable (Standard_B1ms)
- Storage: 32 GB
- SSL: Required
- Firewall: Allows Azure services
- Database: `nycdb`
- Admin User: `nycadmin`

**Access Credentials:**
```bash
az keyvault secret show \
  --vault-name nyc-{env}-kv-xxxxxxxx \
  --name db-password \
  --query value -o tsv
```

---

## Monitoring

### View Application Logs

```bash
# Backend logs
az containerapp logs show \
  --name nyc-{env}-backend \
  --resource-group nyc-{env}-rg

# Frontend logs
az containerapp logs show \
  --name nyc-{env}-frontend \
  --resource-group nyc-{env}-rg
```

### Health Checks

- Backend Health: `https://nyc-{env}-backend.*.azurecontainerapps.io/health`
- Backend Docs: `https://nyc-{env}-backend.*.azurecontainerapps.io/docs`

### Azure Portal Monitoring

- Navigate to Container Apps in resource group
- Use Log Analytics workspace for detailed logging
- View metrics, logs, and health probes

---

## Cost Management

### Recommendations
- **Development:** Scale down or stop when not in use
- **Staging:** Mirror production configuration for testing
- **Production:** Always running with appropriate scaling

### Cleanup Environment

```bash
# Delete development
az group delete --name nyc-dev-rg --yes --no-wait

# Delete staging
az group delete --name nyc-staging-rg --yes --no-wait
```

---

## Troubleshooting

### Pipeline Fails at Azure Login
- Verify `AZURE_CREDENTIALS` secret is correctly set
- Ensure Service Principal has Contributor role

### Container App Deployment Fails
- Check Container Apps Environment exists
- Verify ACR credentials accessible
- Review logs in Azure Portal

### Backend URL Issues
1. Check deployment logs in GitHub Actions
2. Verify backend health: `curl https://nyc-{env}-backend.*.azurecontainerapps.io/health`
3. Check frontend logs

### Image Pull Errors
1. Verify ACR credentials in GitHub secrets
2. Check ACR health: `az acr check-health --name nycacrtakkd33nvzu2k`
3. Verify Service Principal has AcrPull role

### Environment Not Created
1. Verify Azure subscription has `Microsoft.App` and `Microsoft.OperationalInsights` providers
2. Check service principal has contributor access
3. Verify region `westus` has available quota

---

## Best Practices

### Security
- Never commit secrets to repository
- Rotate Service Principal credentials regularly
- Use branch protection rules on `main`
- Require PR reviews before merging
- Enable Dependabot for security updates
- Review API security in [SECURITY.md](SECURITY.md)

### Development
- Test in dev environment first
- Use staging for pre-production validation
- Deploy to production only from `main` branch
- Monitor logs after each deployment

### CI/CD
- Keep workflows DRY (Don't Repeat Yourself)
- Use environment-specific secrets when needed
- Test deployment pipeline changes in dev first
- Document any workflow modifications
