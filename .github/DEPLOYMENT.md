# GitHub Actions CI/CD Setup

## Overview

This repository is configured with automated CI/CD pipelines using GitHub Actions to deploy to Azure Container Apps.

## Workflows

### 1. CI Pipeline (`.github/workflows/ci.yml`)
- **Triggers:** Pull requests to `main`, `develop`, `staging`
- **Actions:**
  - Runs Python linting and tests for backend
  - Runs Node.js build and linting for frontend
  - Validates Dockerfiles
  - Security scanning with Trivy

### 2. Deploy Pipeline (`.github/workflows/deploy.yml`)
- **Triggers:** 
  - Push to `main`, `develop`, or `staging` branches
  - Manual workflow dispatch
- **Actions:**
  - Builds Docker images for backend and frontend
  - Pushes images to Azure Container Registry
  - Deploys to Azure Container Apps
  - Tags images based on branch (prod, staging, dev)

## Branch Strategy

- **`main`** → Production environment
- **`staging`** → Staging environment  
- **`develop`** → Development environment

## Required GitHub Secrets

To enable the CI/CD pipeline, configure these secrets in your GitHub repository:

### Setting Up Secrets

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret** for each of the following:

### AZURE_CREDENTIALS

Create an Azure Service Principal with Contributor access:

```bash
az ad sp create-for-rbac \
  --name "github-nyc-deployment" \
  --role contributor \
  --scopes /subscriptions/6d6a5fb5-b9fc-41bc-a4ec-08a2529e81d8/resourceGroups/nyc-app-rg \
  --sdk-auth
```

Copy the entire JSON output and save it as the `AZURE_CREDENTIALS` secret.

Example output:
```json
{
  "clientId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "clientSecret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "subscriptionId": "6d6a5fb5-b9fc-41bc-a4ec-08a2529e81d8",
  "tenantId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

## Azure Resources

The workflows expect these Azure resources to exist:

- **Resource Group:** `nyc-app-rg`
- **Container Registry:** `nycacrtakkd33nvzu2k`
- **Container Apps Environment:** `nyc-env`
- **Log Analytics Workspace:** `nyc-logs`

Container Apps (`nyc-backend` and `nyc-frontend`) will be created automatically on first deployment.

## Manual Deployment

To trigger a manual deployment:

1. Go to **Actions** tab in GitHub
2. Select **Deploy to Azure** workflow
3. Click **Run workflow**
4. Select the branch to deploy

## Deployment URLs

After successful deployment, URLs will be displayed in the workflow summary:
- Backend API: `https://nyc-backend.{region}.azurecontainerapps.io`
- Frontend App: `https://nyc-frontend.{region}.azurecontainerapps.io`

## Local Development

See the main [README.md](../README.md) for local development setup.

## Monitoring

View logs and metrics in Azure Portal:
- Navigate to Azure Container Apps in `nyc-app-rg` resource group
- Use Log Analytics workspace `nyc-logs` for detailed logging

## Troubleshooting

### Pipeline Fails at Azure Login
- Verify `AZURE_CREDENTIALS` secret is correctly set
- Ensure Service Principal has Contributor role on the resource group

### Container App Deployment Fails
- Check if Container Apps Environment (`nyc-env`) exists
- Verify ACR credentials are accessible
- Review Container App logs in Azure Portal

### Image Push Fails
- Ensure ACR (`nycacrtakkd33nvzu2k`) exists and is accessible
- Verify the Service Principal has AcrPush role

## Security Best Practices

- Never commit secrets to the repository
- Rotate Service Principal credentials regularly
- Use branch protection rules on `main`
- Require PR reviews before merging to `main`
- Enable Dependabot for security updates
