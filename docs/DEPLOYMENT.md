# Azure Deployment Guide

This guide explains how to deploy the FastAPI application to Azure Container Apps.

---

## 🎯 How It Works

- **Azure Container Apps**: Serverless container platform that auto-scales your FastAPI application
- **GitHub Container Registry (GHCR)**: Stores Docker images
- **Automated CI/CD**: GitHub Actions automatically build and deploy on push to `main`

---

## 📋 Prerequisites

1. ✅ Azure subscription with Container Apps enabled
2. ✅ Azure CLI installed and authenticated (`az login`)
3. ✅ Docker installed (for local testing)
4. ✅ GitHub repository with GHCR enabled

---

## 🔧 Setup Steps

### Step 1: Create Azure Resources

If resources don't exist yet:

```powershell
# Login to Azure
az login

# Create resource group
az group create \
  --name rg-FastAPI-AzureContainerApp-dev \
  --location germanywestcentral

# Create Container Apps environment
az containerapp env create \
  --name managedEnvironment-rgFastAPIAzureC-a4a6 \
  --resource-group rg-FastAPI-AzureContainerApp-dev \
  --location germanywestcentral
```

### Step 2: Configure GitHub Secrets (for GitHub Actions)

Add these secrets in **GitHub Repository → Settings → Secrets and variables → Actions**:

#### Required Secrets for Azure OIDC Authentication

1. **`AZURE_CLIENT_ID`** - Application (client) ID
2. **`AZURE_TENANT_ID`** - Directory (tenant) ID
3. **`AZURE_SUBSCRIPTION_ID`** - Azure subscription ID

#### How to Create Azure Service Principal with OIDC

```powershell
# Set variables
$subscriptionId = "your-subscription-id"
$resourceGroup = "rg-FastAPI-AzureContainerApp-dev"
$repoOwner = "stefanfries"
$repoName = "fastapi-azure-container-app"

# Create service principal with federated credentials
az ad sp create-for-rbac \
  --name "fastapi-azure-container-app-deploy" \
  --role Contributor \
  --scopes /subscriptions/$subscriptionId/resourceGroups/$resourceGroup \
  --sdk-auth

# Create federated credential for GitHub Actions
$appId = "your-app-id-from-previous-command"

az ad app federated-credential create \
  --id $appId \
  --parameters '{
    "name": "github-deploy",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:'"$repoOwner"'/'"$repoName"':ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

### Step 3: Local Deployment (Optional)

For manual deployment from your local machine:

```powershell
# Copy .env.example to .env and configure
Copy-Item .env.example .env

# Edit .env with your Azure details
# Then run deployment script
.\scripts\deploy-to-azure.ps1
```

---

## 🚀 Automated Deployment

### GitHub Actions Workflows

Two workflows are configured:

1. **[ci-quality.yml](.github/workflows/ci-quality.yml)** - Runs on every push/PR
   - Linting with ruff
   - Code formatting check with ruff
   - Tests with pytest and coverage

2. **[cd-deploy.yml](.github/workflows/cd-deploy.yml)** - Runs on push to `main`
   - Builds Docker image
   - Pushes to GitHub Container Registry
   - Deploys to Azure Container Apps
   - Tests the deployment

### Triggering Deployment

Simply push to `main` branch:

```bash
git add .
git commit -m "feat: update application"
git push origin main
```

GitHub Actions will automatically:

1. ✅ Run tests and quality checks
2. ✅ Build Docker image
3. ✅ Push to GHCR
4. ✅ Deploy to Azure
5. ✅ Test the deployment

---

## 🔄 Updating the Deployment

### Update Environment Variables

```powershell
az containerapp update \
  --name ca-fastapi \
  --resource-group rg-FastAPI-AzureContainerApp-dev \
  --set-env-vars "NEW_VAR=value"
```

Recommended production baseline:

```powershell
az containerapp update \
  --name ca-fastapi \
  --resource-group rg-FastAPI-AzureContainerApp-dev \
  --set-env-vars LOG_LEVEL=WARNING ENVIRONMENT=production
```

Notes:

- `LOG_LEVEL` controls application logger verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`)
- `ENVIRONMENT` should be `production` for deployed environments
- `APP_VERSION` is injected automatically by the CD workflow on deploy

### Runtime Log-Level Tuning (No Code Deployment)

The API exposes an authenticated admin endpoint to change log level at runtime.
All admin endpoints require `X-API-Key` when `API_KEY` is configured.

Read current effective log level:

```bash
curl -H "X-API-Key: <your-api-key>" https://<app-fqdn>/v1/admin/log-level
```

Temporarily change log level for current runtime only:

```bash
curl -X PUT https://<app-fqdn>/v1/admin/log-level \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <your-api-key>" \
  -d '{"log_level":"DEBUG","persist":false}'
```

Change and persist log level in MongoDB (`app_config/logging`):

```bash
curl -X PUT https://<app-fqdn>/v1/admin/log-level \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <your-api-key>" \
  -d '{"log_level":"WARNING","persist":true}'
```

### Update Docker Image Manually

```powershell
az containerapp update \
  --name ca-fastapi \
  --resource-group rg-FastAPI-AzureContainerApp-dev \
  --image ghcr.io/stefanfries/fastapi-azure-container-app/fastapi-container:latest
```

### Scale the Application

```powershell
az containerapp update \
  --name ca-fastapi \
  --resource-group rg-FastAPI-AzureContainerApp-dev \
  --min-replicas 1 \
  --max-replicas 5
```

### Post-Deploy Data-Quality Backfill (ISIN Mapping)

After deploying mapping-related changes, run a targeted backfill to update cached
`symbol_yfinance` and constituent-name corrections without clearing the full cache.

```powershell
uv run python -m scripts.backfill_mapping_overrides
```

Expected output:

```text
Backfill complete: instrument_docs_updated=<n> index_member_docs_updated=<n>
```

### Post-Deploy Smoke Checks (Mapping)

Verify canonical mappings:

```powershell
Invoke-RestMethod -Uri "https://<app-fqdn>/v1/instruments/US74743L1008" | Select-Object -ExpandProperty global_identifiers
Invoke-RestMethod -Uri "https://<app-fqdn>/v1/instruments/CH0044328745" | Select-Object -ExpandProperty global_identifiers
Invoke-RestMethod -Uri "https://<app-fqdn>/v1/instruments/CH0114405324" | Select-Object -ExpandProperty global_identifiers
```

Expected `symbol_yfinance` values:

- `US74743L1008` -> `BG`
- `CH0044328745` -> `CB`
- `CH0114405324` -> `GRMN`

Verify S&P 500 constituent name corrections:

```powershell
$members = Invoke-RestMethod -Uri "https://<app-fqdn>/v1/indices/S%26P%20500"
$members | Where-Object { $_.isin -in @('US74743L1008','CH0044328745','CH0114405324') } | Select-Object isin, name
```

Expected names:

- `US74743L1008` -> `Bunge Global S.A.`
- `CH0044328745` -> `Chubb Limited`
- `CH0114405324` -> `Garmin Ltd.`

### Rollback (Mapping Patch)

If a regression is detected:

1. Roll back to the previous app revision.
2. Revert mapping changes and redeploy.
3. Clear affected cache entries (or let TTL expire) before re-verification.
4. Re-run the smoke checks above.

---

## 🐛 Troubleshooting

### View Logs

```powershell
# Follow logs
az containerapp logs show \
  --name ca-fastapi \
  --resource-group rg-FastAPI-AzureContainerApp-dev \
  --follow

# View recent logs
az containerapp logs show \
  --name ca-fastapi \
  --resource-group rg-FastAPI-AzureContainerApp-dev \
  --tail 50
```

### Check Container Status

```powershell
az containerapp show \
  --name ca-fastapi \
  --resource-group rg-FastAPI-AzureContainerApp-dev \
  --query "{Name:name, Status:properties.provisioningState, FQDN:properties.configuration.ingress.fqdn}"
```

### Restart Container

```powershell
az containerapp revision restart \
  --name ca-fastapi \
  --resource-group rg-FastAPI-AzureContainerApp-dev
```

---

## 🔐 Security Best Practices

1. **Never commit secrets**: The `.env` file is in `.gitignore`
2. **Use Azure OIDC**: Passwordless authentication for GitHub Actions
3. **Rotate credentials**: Regularly update service principal credentials
4. **Least privilege**: Grant only necessary permissions to service principals
5. **Use managed identity**: Consider Azure Managed Identity for production

---

## 📊 Monitoring

### Azure Portal

View metrics and logs in Azure Portal:

- Navigate to: Resource Groups → rg-FastAPI-AzureContainerApp-dev → ca-fastapi
- Monitor: Requests, Response time, CPU, Memory

### Application Insights (Optional)

For advanced monitoring, integrate Application Insights:

```powershell
# Create Application Insights
az monitor app-insights component create \
  --app fastapi-insights \
  --location germanywestcentral \
  --resource-group rg-FastAPI-AzureContainerApp-dev

# Add instrumentation key to container app
az containerapp update \
  --name ca-fastapi \
  --resource-group rg-FastAPI-AzureContainerApp-dev \
  --set-env-vars "APPLICATIONINSIGHTS_CONNECTION_STRING=your-connection-string"
```

---

## � Secrets Management (Azure Key Vault)

MongoDB credentials are stored in Azure Key Vault and injected into the Container App via a managed identity reference — no plain text secrets in the portal or environment.

### Architecture

```text
App reads MONGODB_CONNECTION_STRING env var
    → Container App secret (secretref:mongodb-connection-string)
    → Key Vault reference (keyvaultref:https://kv-depot-butler-prod.vault.azure.net/...)
    → System-assigned Managed Identity (RBAC: Key Vault Secrets User)
    → Azure Key Vault secret (encrypted at rest)
```

### Initial Setup (one-time)

1. Store the secret in Key Vault**

```bash
az keyvault secret set \
  --vault-name kv-depot-butler-prod \
  --name mongodb-connection-string \
  --value "mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority"
```

2. Enable system-assigned managed identity on the Container App**

```bash
az containerapp identity assign \
  --name ca-fastapi \
  --resource-group rg-FastAPI-AzureContainerApp-dev \
  --system-assigned
# Note the Principal ID returned — needed for the RBAC step below
```

3. Grant Key Vault access to the managed identity**

```bash
az role assignment create \
  --role "Key Vault Secrets User" \
  --assignee "<principal-id-from-step-2>" \
  --scope "/subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.KeyVault/vaults/kv-depot-butler-prod"
```

4. Add the Key Vault reference as a Container App secret**

```bash
az containerapp secret set \
  --name ca-fastapi \
  --resource-group rg-FastAPI-AzureContainerApp-dev \
  --secrets "mongodb-connection-string=keyvaultref:https://kv-depot-butler-prod.vault.azure.net/secrets/mongodb-connection-string,identityref:system"
```

5. Wire the secret to the environment variable**

```bash
az containerapp update \
  --name ca-fastapi \
  --resource-group rg-FastAPI-AzureContainerApp-dev \
  --set-env-vars "MONGODB_CONNECTION_STRING=secretref:mongodb-connection-string"
```

### Rotating the Secret

Update the secret value in Key Vault — the Container App picks it up automatically on next restart/revision.

```bash
az keyvault secret set \
  --vault-name kv-depot-butler-prod \
  --name mongodb-connection-string \
  --value "mongodb+srv://<new-credentials>@<cluster>.mongodb.net/..."
```

---

## 📚 Related Documentation

- [Azure Container Apps Documentation](https://learn.microsoft.com/en-us/azure/container-apps/)
- [GitHub Actions - Azure Login](https://github.com/Azure/login)
- [Dockerfile Best Practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)

---

**Last Updated:** May 1, 2026
