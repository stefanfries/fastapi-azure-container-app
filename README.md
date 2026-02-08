[![CI - Code Quality](https://github.com/stefanfries/fastapi-azure-container-app/actions/workflows/ci-quality.yml/badge.svg)](https://github.com/stefanfries/fastapi-azure-container-app/actions/workflows/ci-quality.yml)
[![CD - Build and Deploy](https://github.com/stefanfries/fastapi-azure-container-app/actions/workflows/cd-deploy.yml/badge.svg)](https://github.com/stefanfries/fastapi-azure-container-app/actions/workflows/cd-deploy.yml)

# FastAPI Azure Container App

A FastAPI application automatically deployed to Azure Container Apps with CI/CD pipeline.

## 🚀 Features

- **FastAPI Framework**: Modern, fast web framework for building APIs
- **Plugin-Based Parser System**: Extensible architecture for data parsing
- **Azure Container Apps**: Serverless container deployment with auto-scaling
- **CI/CD Pipeline**: Automated testing, building, and deployment via GitHub Actions
- **Health Check Endpoint**: Monitoring and availability verification
- **Docker Support**: Containerized application for consistent deployments

## 📋 Quick Start

### Local Development

1. **Clone the repository**:
   ```bash
   git clone https://github.com/stefanfries/fastapi-azure-container-app.git
   cd fastapi-azure-container-app
   ```

2. **Create and activate virtual environment**:
   ```bash
   python -m venv .venv
   ./.venv/Scripts/activate  # Windows
   source .venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
   ```

5. **Access the API**:
   - Application: http://localhost:8080
   - API Documentation: http://localhost:8080/docs
   - Alternative docs: http://localhost:8080/redoc

### Using Make Commands

```bash
# Install dependencies
make install

# Format code
make format

# Lint code
make lint

# Run tests with coverage
make test

# Build Docker image locally
make build

# Run Docker container
make run
```

## 🐳 Docker

### Build and Run Locally

```bash
# Build Docker image
docker build -t fastapi-container .

# Run container
docker run -p 8080:8080 fastapi-container

# Test the application
curl http://localhost:8080
```

## ☁️ Azure Deployment

### Automated Deployment (Recommended)

Simply push to the `main` branch:

```bash
git add .
git commit -m "feat: your changes"
git push origin main
```

GitHub Actions will automatically:
1. Run tests and quality checks
2. Build Docker image
3. Push to GitHub Container Registry
4. Deploy to Azure Container Apps

### Manual Deployment

For manual deployment from your local machine:

```bash
# Copy and configure environment
cp .env.example .env
# Edit .env with your Azure details

# Run deployment script
.\scripts\deploy-to-azure.ps1
```

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed setup instructions.

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_main.py
```

## 📁 Project Structure

```
fastapi-azure-container-app/
├── app/                      # Application source code
│   ├── core/                 # Core functionality (constants, config)
│   ├── crud/                 # Database operations
│   ├── models/               # Data models
│   ├── parsers/              # Data parsing logic
│   │   └── plugins/          # Plugin-based parser system
│   ├── routers/              # API route handlers
│   ├── scrapers/             # Web scraping utilities
│   ├── static/               # Static files
│   ├── main.py               # Application entry point
│   ├── middleware.py         # Custom middleware
│   └── logging_config.py     # Logging configuration
├── tests/                    # Test suite
├── docs/                     # Documentation
│   └── DEPLOYMENT.md         # Deployment guide
├── scripts/                  # Deployment and utility scripts
│   └── deploy-to-azure.ps1   # Azure deployment script
├── .github/workflows/        # CI/CD pipelines
│   ├── ci-quality.yml        # Code quality checks
│   └── cd-deploy.yml         # Build and deploy
├── Dockerfile                # Docker configuration
├── requirements.txt          # Python dependencies
├── Makefile                  # Development commands
└── README.md                 # This file
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file from `.env.example`:

```bash
cp .env.example .env
```

Configure the following variables:

```env
# Azure Configuration
AZURE_RESOURCE_GROUP=rg-FastAPI-AzureContainerApp-dev
AZURE_CONTAINER_APP_NAME=ca-fastapi
AZURE_ENVIRONMENT=managedEnvironment-rgFastAPIAzureC-a4a6

# Docker Configuration
DOCKER_OWNER=your-github-username
```

## 📚 Documentation

- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Comprehensive deployment guide
- **[PLUGIN_SYSTEM_DOCUMENTATION.md](PLUGIN_SYSTEM_DOCUMENTATION.md)** - Plugin architecture
- **[QUICK_START_NEW_PARSER.md](QUICK_START_NEW_PARSER.md)** - Adding new parsers

## 🔐 Security

- ✅ `.env` files are git-ignored
- ✅ Secrets managed via Azure Key Vault / GitHub Secrets
- ✅ OIDC authentication for GitHub Actions
- ✅ No hardcoded credentials in code

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'feat: add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Deployed on [Azure Container Apps](https://azure.microsoft.com/en-us/services/container-apps/)
- CI/CD with [GitHub Actions](https://github.com/features/actions)

---

**Status**: Production Ready ✅  
**Last Updated**: February 8, 2026
