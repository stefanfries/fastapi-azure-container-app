# Technical Requirements

- Clean and modular architecture
- Factory pattern for parsers to enable future extension for new asset classes and data sources
- Scrape financial instrument data from comdirect using BeautifulSoup
- Plugin system for all asset classes (fully implemented — see [PLUGIN_SYSTEM_DOCUMENTATION.md](PLUGIN_SYSTEM_DOCUMENTATION.md))
- Async code only: httpx for HTTP, PyMongo `AsyncMongoClient` for database
- Strict data validation with Pydantic v2
- MongoDB Atlas as document database (via PyMongo native async — **do not use Motor**)
- Unit and integration tests via pytest
- Deploy to Azure Container Apps via GitHub Actions CI/CD

# Current State

All original technical requirements are met. The following has been implemented:

- ✅ Plugin system covering all 9 asset classes (STOCK, BOND, ETF, FONDS, CERTIFICATE, WARRANT, INDEX, COMMODITY, CURRENCY)
  - `StandardAssetParser` — STOCK, BOND, ETF, FONDS, CERTIFICATE
  - `WarrantParser` — WARRANT (with id_notation refetch mechanism)
  - `SpecialAssetParser` — INDEX, COMMODITY, CURRENCY (non-tradeable, no venues)
- ✅ Shared parsing utilities in `parsing_utils.py` (used by all parsers and `quotes.py`)
- ✅ All legacy parsing code removed from `instruments.py`; no fallback path exists
- ✅ MongoDB Atlas integration using PyMongo `AsyncMongoClient`
- ✅ FastAPI routers: welcome, instruments, quotes, history, depots, users, warrants, indices
- ✅ Custom `JSONResponse` with UTF-8 charset for German umlauts
- ✅ CI/CD via GitHub Actions (lint + tests on PR; build + push + deploy to Azure on main)

# Open / Future Work

- Authentication/Authorization not yet implemented (routes unprotected)
- Asset-class-specific extended data models not yet implemented
- Integration tests for parsers / scrapers not yet added
- User role model (RBAC) not yet defined
- API versioning (`/v1/`) not yet applied to routes
- `print()` statements may still exist in older modules (should be replaced with `logger`)

