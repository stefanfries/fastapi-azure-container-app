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
   - Linting with pylint
   - Code formatting check with black
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

## 📚 Related Documentation

- [Azure Container Apps Documentation](https://learn.microsoft.com/en-us/azure/container-apps/)
- [GitHub Actions - Azure Login](https://github.com/Azure/login)
- [Dockerfile Best Practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)

---

**Last Updated:** February 8, 2026
