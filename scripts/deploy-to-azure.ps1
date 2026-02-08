# Azure Container App Deployment Script for FastAPI
# This script creates/updates the FastAPI container app in Azure
#
# ⚠️ IMPORTANT:
# 1. Make sure your .env file contains all required configuration
# 2. The .env file is in .gitignore and will NOT be committed to git
# 3. Run this script from the project root directory
# 4. Ensure you're logged into Azure CLI: az login

# Configuration
$RESOURCE_GROUP = "rg-FastAPI-AzureContainerApp-dev"
$ENVIRONMENT = "managedEnvironment-rgFastAPIAzureC-a4a6"
$APP_NAME = "ca-fastapi"
$DOCKER_IMAGE = "ghcr.io/stefanfries/fastapi-azure-container-app/fastapi-container:latest"

Write-Host "🚀 Deploying FastAPI to Azure Container Apps..." -ForegroundColor Green

# Function to read .env file
function Get-EnvVariable {
    param (
        [string]$Name
    )

    $envFile = ".env"
    if (-not (Test-Path $envFile)) {
        Write-Host "❌ Error: .env file not found in current directory" -ForegroundColor Red
        Write-Host "💡 Copy .env.example to .env and fill in your values" -ForegroundColor Yellow
        exit 1
    }

    $content = Get-Content $envFile
    foreach ($line in $content) {
        if ($line -match "^\s*$Name\s*=\s*(.+)$") {
            $value = $matches[1]
            # Remove quotes if present
            $value = $value -replace '^[''"]|[''"]$', ''
            return $value
        }
    }

    Write-Host "⚠️  Warning: $Name not found in .env file" -ForegroundColor Yellow
    return $null
}

# Read configuration from .env file (optional)
Write-Host "📖 Reading configuration from .env file..." -ForegroundColor Cyan
$CUSTOM_RESOURCE_GROUP = Get-EnvVariable "AZURE_RESOURCE_GROUP"
$CUSTOM_ENVIRONMENT = Get-EnvVariable "AZURE_ENVIRONMENT"
$CUSTOM_APP_NAME = Get-EnvVariable "AZURE_CONTAINER_APP_NAME"

# Override defaults if values exist in .env
if (![string]::IsNullOrEmpty($CUSTOM_RESOURCE_GROUP)) { $RESOURCE_GROUP = $CUSTOM_RESOURCE_GROUP }
if (![string]::IsNullOrEmpty($CUSTOM_ENVIRONMENT)) { $ENVIRONMENT = $CUSTOM_ENVIRONMENT }
if (![string]::IsNullOrEmpty($CUSTOM_APP_NAME)) { $APP_NAME = $CUSTOM_APP_NAME }

Write-Host "✅ Configuration loaded" -ForegroundColor Green
Write-Host "   Resource Group: $RESOURCE_GROUP" -ForegroundColor Cyan
Write-Host "   Environment: $ENVIRONMENT" -ForegroundColor Cyan
Write-Host "   App Name: $APP_NAME" -ForegroundColor Cyan
Write-Host "   Image: $DOCKER_IMAGE" -ForegroundColor Cyan

# Check if logged into Azure
Write-Host "`n🔐 Checking Azure CLI authentication..." -ForegroundColor Cyan
$azAccount = az account show 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Not logged into Azure CLI" -ForegroundColor Red
    Write-Host "💡 Please run: az login" -ForegroundColor Yellow
    exit 1
}
Write-Host "✅ Authenticated with Azure" -ForegroundColor Green

# Check if resource group exists
Write-Host "`n📦 Checking resource group..." -ForegroundColor Cyan
$rgExists = az group exists --name $RESOURCE_GROUP
if ($rgExists -eq "false") {
    Write-Host "❌ Resource group '$RESOURCE_GROUP' does not exist" -ForegroundColor Red
    Write-Host "💡 Create it with: az group create --name $RESOURCE_GROUP --location germanywestcentral" -ForegroundColor Yellow
    exit 1
}
Write-Host "✅ Resource group exists" -ForegroundColor Green

# Check if Container Apps environment exists
Write-Host "`n🌍 Checking Container Apps environment..." -ForegroundColor Cyan
$envExists = az containerapp env show --name $ENVIRONMENT --resource-group $RESOURCE_GROUP 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Container Apps environment '$ENVIRONMENT' does not exist" -ForegroundColor Red
    Write-Host "💡 Create it with:" -ForegroundColor Yellow
    Write-Host "   az containerapp env create --name $ENVIRONMENT --resource-group $RESOURCE_GROUP --location germanywestcentral" -ForegroundColor Yellow
    exit 1
}
Write-Host "✅ Container Apps environment exists" -ForegroundColor Green

# Check if the container app already exists
Write-Host "`n🔍 Checking if Container App exists..." -ForegroundColor Cyan
$appExists = az containerapp show --name $APP_NAME --resource-group $RESOURCE_GROUP 2>$null
$isUpdate = $LASTEXITCODE -eq 0

if ($isUpdate) {
    Write-Host "📝 Container App exists - will update" -ForegroundColor Yellow
    
    # Update existing container app
    Write-Host "`n🔄 Updating Container App..." -ForegroundColor Cyan
    az containerapp update `
        --name $APP_NAME `
        --resource-group $RESOURCE_GROUP `
        --image $DOCKER_IMAGE `
        --cpu 1.0 `
        --memory 2.0Gi
} else {
    Write-Host "✨ Container App does not exist - will create new" -ForegroundColor Green
    
    # Create new container app
    Write-Host "`n🔧 Creating Container App..." -ForegroundColor Cyan
    az containerapp create `
        --name $APP_NAME `
        --resource-group $RESOURCE_GROUP `
        --environment $ENVIRONMENT `
        --image $DOCKER_IMAGE `
        --target-port 8080 `
        --ingress external `
        --cpu 1.0 `
        --memory 2.0Gi `
        --min-replicas 1 `
        --max-replicas 3
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n❌ Failed to $(if ($isUpdate) { 'update' } else { 'create' }) Container App" -ForegroundColor Red
    exit 1
}

Write-Host "`n✅ Deployment complete!" -ForegroundColor Green

# Get the app URL
Write-Host "`n🌐 Retrieving application URL..." -ForegroundColor Cyan
$fqdn = az containerapp show `
    --name $APP_NAME `
    --resource-group $RESOURCE_GROUP `
    --query "properties.configuration.ingress.fqdn" `
    --output tsv

if (![string]::IsNullOrEmpty($fqdn)) {
    $appUrl = "https://$fqdn"
    Write-Host "✅ Application URL: $appUrl" -ForegroundColor Green
    Write-Host "📝 API Documentation: $appUrl/docs" -ForegroundColor Cyan
    
    # Test the endpoint
    Write-Host "`n🧪 Testing application endpoint..." -ForegroundColor Cyan
    try {
        $response = Invoke-RestMethod -Uri $appUrl -Method Get -TimeoutSec 30
        Write-Host "✅ Application is responding!" -ForegroundColor Green
        Write-Host "   Response: $($response | ConvertTo-Json -Compress)" -ForegroundColor Cyan
    } catch {
        Write-Host "⚠️  Application may still be starting up. Try again in a few moments." -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠️  Could not retrieve application URL" -ForegroundColor Yellow
}

Write-Host "`n📋 Next steps:" -ForegroundColor Cyan
Write-Host "  1. Visit Azure Portal: https://portal.azure.com/#@/resource/subscriptions/.../resourceGroups/$RESOURCE_GROUP/providers/Microsoft.App/containerApps/$APP_NAME" -ForegroundColor White
Write-Host "  2. Test your API: $appUrl" -ForegroundColor White
Write-Host "  3. View logs: az containerapp logs show --name $APP_NAME --resource-group $RESOURCE_GROUP --follow" -ForegroundColor White
Write-Host ""
