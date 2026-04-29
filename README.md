# FastAPI Azure Container App

[![CI - Code Quality](https://github.com/stefanfries/fastapi-azure-container-app/actions/workflows/ci-quality.yml/badge.svg)](https://github.com/stefanfries/fastapi-azure-container-app/actions/workflows/ci-quality.yml)
[![CD - Build and Deploy](https://github.com/stefanfries/fastapi-azure-container-app/actions/workflows/cd-deploy.yml/badge.svg)](https://github.com/stefanfries/fastapi-azure-container-app/actions/workflows/cd-deploy.yml)

A FastAPI application automatically deployed to Azure Container Apps with CI/CD pipeline.

## 🚀 Features

- **FastAPI Framework**: Modern, fast web framework for building APIs
- **All 9 Asset Classes**: STOCK, BOND, ETF, FONDS, CERTIFICATE, WARRANT, INDEX, COMMODITY, CURRENCY
- **Asset-Class-Specific Details**: `GET /v1/instruments/{wkn|isin}` returns a typed `details` block per asset class — all 9 classes fully implemented including `IndexDetails` (country, currency, num_constituents, constituents_url), `CommodityDetails` (currency, symbol, country), `CurrencyDetails` (base_currency, quote_currency, country)
- **ISIN & WKN from Stammdaten**: `SpecialAssetParser` now reads ISIN, WKN, and Symbol directly from the Stammdaten table (e.g. DAX → ISIN `DE0008469008`, symbol `DAX`)
- **Index Constituent Link**: `IndexDetails.constituents_url` carries a ready-to-use API path (e.g. `/v1/indices/DE0008469008`) linking directly to the constituent list
- **Index Members API**: `GET /v1/indices/{name|isin|wkn}` accepts a human-readable name, WKN, or ISIN — including tracking ISINs not in the comdirect index catalogue (e.g. `DE0009653386` for S&P 500)
- **Constituent Instrument Links**: Each `IndexMember` now includes `instrument_url` (e.g. `/v1/instruments/DE0007164600`) alongside the comdirect page link
- **Plugin-Based Parser System**: Extensible architecture — each asset class has a dedicated parser with full `parse_details()` support
- **MongoDB Atlas**: Async persistence via PyMongo `AsyncMongoClient` (native async, no Motor)
- **Azure Container Apps**: Serverless container deployment with auto-scaling
- **CI/CD Pipeline**: Automated testing, building, and deployment via GitHub Actions
- **Docker Support**: Containerized application for consistent deployments
- **CORS Support**: `GET` requests permitted from any origin (suitable for browser-based clients)

## 📋 Quick Start

### Local Development

1. **Clone the repository**:

   ```bash
   git clone https://github.com/stefanfries/fastapi-azure-container-app.git
   cd fastapi-azure-container-app
   ```

2. **Create and activate virtual environment**:

   ```bash
   uv sync
   ```

3. **Run the application**:

   ```bash
   uv run uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
   ```

4. **Access the API**:
   - Application: <http://localhost:8080>
   - API Documentation: <http://localhost:8080/docs>
   - Alternative docs: <http://localhost:8080/redoc>

### Using Make / PowerShell Commands

```bash
# Install dependencies
make install   # Linux/Mac
.\make.ps1 install   # Windows

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

388 unit tests passing with 82% code coverage.

```bash
# Run all tests
uv run pytest tests/

# Run with coverage
uv run pytest tests/ --cov

# Run specific test file
uv run pytest tests/unit/parsers/plugins/test_stock_parser.py
```

## 📁 Project Structure

```text
fastapi-azure-container-app/
├── app/
│   ├── clients/              # External API clients (e.g. OpenFIGI)
│   ├── core/                 # Settings, database connection, constants, logging
│   ├── models/               # Pydantic response models
│   ├── parsers/              # Data parsing logic
│   │   ├── base_parser.py    # InstrumentParser abstract base class
│   │   ├── standard_asset_parser.py  # Shared base for tradeable asset parsers
│   │   ├── special_asset_parser.py   # Parser for INDEX, COMMODITY, CURRENCY
│   │   └── plugins/          # Concrete parsers: Stock, Bond, ETF, Fonds, Certificate, Warrant
│   ├── repositories/         # Database access layer
│   ├── routers/              # API route handlers
│   ├── scrapers/             # Web scraping utilities (httpx + BeautifulSoup)
│   ├── services/             # Business logic services
│   ├── main.py               # Application entry point + lifespan hooks
│   └── middleware.py         # Client IP logging middleware
├── tests/                    # Test suite
├── docs/                     # Documentation
├── scripts/                  # Utility and deployment scripts
│   └── deploy-to-azure.ps1   # Manual Azure deployment script
├── .github/workflows/
│   ├── ci-quality.yml        # Lint + tests on pull requests
│   └── cd-deploy.yml         # Build → push → deploy to Azure on main
├── Dockerfile
├── pyproject.toml            # Dependencies managed with uv
├── Makefile / make.ps1       # Development commands
└── README.md
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

- **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Deployment guide
- **[docs/PLUGIN_SYSTEM_DOCUMENTATION.md](docs/PLUGIN_SYSTEM_DOCUMENTATION.md)** - Plugin architecture, asset-class coverage, and detail models
- **[docs/QUICK_START_NEW_PARSER.md](docs/QUICK_START_NEW_PARSER.md)** - Adding new parsers and detail models
- **[docs/TECHNICAL_REQUIREMENTS.md](docs/TECHNICAL_REQUIREMENTS.md)** - Technical requirements and current implementation state
- **[docs/DEVELOPMENT_ROADMAP.md](docs/DEVELOPMENT_ROADMAP.md)** - Prioritized development plan and progress tracking

## 🔐 Security

- ✅ `.env` files are git-ignored
- ✅ Secrets managed via Azure Key Vault / GitHub Secrets
- ✅ OIDC authentication for GitHub Actions
- ✅ No hardcoded credentials in code
- ✅ API key protection on all data endpoints (`X-API-Key` header); omitting `API_KEY` enables open mode for local dev; setting `API_KEY=""` (empty string) is rejected at startup

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
