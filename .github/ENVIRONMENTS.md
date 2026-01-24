# Multi-Environment Deployment Setup

## Overview
The application now supports three separate environments, each with its own isolated Azure resource group and automatically configured backend URL.

## Environments

### 1. Production (main branch)
- **Branch:** `main`
- **Resource Group:** `nyc-prod-rg`
- **Container Environment:** `nyc-prod-env`
- **Backend App:** `nyc-prod-backend`
- **Frontend App:** `nyc-prod-frontend`
- **Trigger:** Push to `main` branch

### 2. Staging (staging branch)
- **Branch:** `staging`
- **Resource Group:** `nyc-staging-rg`
- **Container Environment:** `nyc-staging-env`
- **Backend App:** `nyc-staging-backend`
- **Frontend App:** `nyc-staging-frontend`
- **Trigger:** Push to `staging` branch

### 3. Development (develop branch)
- **Branch:** `develop`
- **Resource Group:** `nyc-dev-rg`
- **Container Environment:** `nyc-dev-env`
- **Backend App:** `nyc-dev-backend`
- **Frontend App:** `nyc-dev-frontend`
- **Trigger:** Push to `develop` branch

## Deployment Flow

### Automatic Backend URL Injection
The deployment pipeline automatically handles backend URL configuration:

1. **Backend Deployment First**
   - Backend container is deployed to Azure Container Apps
   - Unique FQDN is assigned (e.g., `nyc-prod-backend.victorioustree-xyz.westus.azurecontainerapps.io`)

2. **Dynamic Configuration Update**
   - Pipeline retrieves the backend FQDN
   - Updates `frontend/nginx.conf` replacing `BACKEND_URL_PLACEHOLDER` with actual URL
   - Rebuilds frontend Docker image with correct backend URL

3. **Frontend Deployment**
   - Frontend container is deployed with environment-specific backend URL
   - Each environment's frontend points to its own backend

### Resource Management
- **Auto-creation**: Resource groups and Container Apps environments are created automatically if they don't exist
- **Isolation**: Each environment is completely isolated with its own resources
- **Location**: All environments deploy to `westus` region

## Workflow

### Creating a New Environment
To deploy to a specific environment:

```bash
# Deploy to Development
git checkout develop
git push origin develop

# Deploy to Staging
git checkout staging
git push origin staging

# Deploy to Production
git checkout main
git push origin main
```

### First-Time Setup
On the first deployment to each environment:
1. Resource group is created
2. Log Analytics workspace is provisioned
3. Container Apps environment is set up
4. Backend and frontend apps are deployed

### Subsequent Deployments
Future deployments to the same environment:
1. Existing resources are reused
2. Container images are updated
3. Applications are rolled out with zero downtime

## Environment Variables

Each container app receives:
- **BACKEND_URL**: Automatically set to the environment's backend URL
- **ENVIRONMENT**: Set to `production`, `staging`, or `development`

## Accessing Deployed Applications

After deployment, check the GitHub Actions summary for URLs:
- Backend API: `https://nyc-{env}-backend.*.azurecontainerapps.io`
- Backend Health: `https://nyc-{env}-backend.*.azurecontainerapps.io/health`
- Backend Docs: `https://nyc-{env}-backend.*.azurecontainerapps.io/docs`
- Frontend App: `https://nyc-{env}-frontend.*.azurecontainerapps.io`

## Cost Management

### Recommendations
- **Development**: Use for feature testing, keep scaled down or stopped when not in use
- **Staging**: Use for pre-production testing, mirror production configuration
- **Production**: Always running with appropriate scaling

### Cleanup
To delete an environment:
```bash
# Delete development environment
az group delete --name nyc-dev-rg --yes --no-wait

# Delete staging environment
az group delete --name nyc-staging-rg --yes --no-wait
```

## Troubleshooting

### Backend URL Issues
If frontend can't connect to backend:
1. Check deployment logs in GitHub Actions
2. Verify backend is healthy: `curl https://nyc-{env}-backend.*.azurecontainerapps.io/health`
3. Check frontend logs: `az containerapp logs show --name nyc-{env}-frontend --resource-group nyc-{env}-rg`

### Environment Not Created
If deployment fails on first run:
1. Verify Azure subscription has required providers: `Microsoft.App`, `Microsoft.OperationalInsights`
2. Check service principal has contributor access to subscription
3. Verify region `westus` has available quota

### Image Pull Errors
If containers can't pull from ACR:
1. Verify ACR credentials in GitHub secrets
2. Check ACR is accessible: `az acr check-health --name nycacrtakkd33nvzu2k`
3. Verify service principal has AcrPull role on ACR

## Next Steps

1. **Add Database Support**: Deploy PostgreSQL for each environment
2. **Configure Secrets**: Use Azure Key Vault for sensitive configuration
3. **Set Up Monitoring**: Configure Application Insights for each environment
4. **Implement Tests**: Add environment-specific test suites
5. **Custom Domains**: Add custom domain names for each environment
