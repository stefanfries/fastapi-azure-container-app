# FastAPI Azure Container App

FastAPI service for financial data aggregation and depot management, deployed to Azure Container Apps.
Provides unified API access to instruments, quotes, historical prices, and depot data backed by MongoDB Atlas.

## How to run

```bash
uv sync
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
# Visit http://localhost:8080/docs (Swagger UI)

# With Make
make install
make test        # Run tests with coverage
make build       # Build Docker image locally
make run         # Run Docker container
```

## Architecture

- `app/main.py` — FastAPI app with lifespan hooks for MongoDB connection management
- `app/core/database.py` — MongoDB async connection using PyMongo `AsyncMongoClient`
- `app/core/settings.py` — configuration via pydantic-settings
- `app/routers/` — modular endpoints: depots, history, instruments, quotes, users, welcome
- `app/crud/` — database access patterns
- `app/models/` — Pydantic response models
- `app/parsers/plugins/` — extensible plugin system for data parsing
- `app/scrapers/` — web scraping utilities
- `app/middleware.py` — client IP logging middleware

## MongoDB — async driver

**Use PyMongo's native async support (`AsyncMongoClient`) — do NOT use motor.**
Motor has been deprecated; PyMongo 4.9+ provides first-class async support.

```python
from pymongo import AsyncMongoClient   # correct
# NOT: from motor.motor_asyncio import AsyncIOMotorClient
```

All database operations in routers and CRUD modules must be `await`ed.

### Notable details

- Custom JSON response class with UTF-8 charset for correct German umlaut (ä/ö/ü) handling
- CI runs on PRs (lint + tests); CD auto-deploys to Azure Container Apps on push to main via GitHub Actions

## CI/CD

- `.github/workflows/ci-quality.yml` — linting + testing on pull requests
- `.github/workflows/cd-deploy.yml` — build → push to GitHub Container Registry → deploy to Azure on main
- `scripts/deploy-to-azure.ps1` — manual local deployment script

## Infrastructure

- **MongoDB Atlas** — primary database (PyMongo `AsyncMongoClient`)
- **Azure Container Apps** — runtime
- **GitHub Container Registry** — Docker image storage

## Testing

```bash
uv run pytest tests/ --cov    # 4 test files
```
