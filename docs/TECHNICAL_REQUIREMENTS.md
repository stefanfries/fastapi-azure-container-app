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
- ✅ Asset-class-specific detail models (`app/models/instrument_details.py`)
  - 9 Pydantic models: `StockDetails`, `BondDetails`, `ETFDetails`, `FondsDetails`, `WarrantDetails`, `CertificateDetails`, `IndexDetails`, `CommodityDetails`, `CurrencyDetails`
  - Discriminated union `InstrumentDetails` keyed on `asset_class` literal
  - Optional `details` field on `Instrument` model
- ✅ Stock details parser — `StandardAssetParser._parse_stock_details()` extracts:
  - `Wertpapiertyp`, `Marktsegment`, `Branche` (full name from `<span title>`), `Geschäftsjahr` (as DD-MM)
  - `Marktkapital.` (with Bil./Mrd./Mio. + currency), `Streubesitz`, `Nennwert`, `Stücke`
- ✅ Warrant details parser — `WarrantParser._parse_warrant_details()` extracts:
  - `Typ` (full exercise style from `<span title>`, e.g. "Call (Amerikanisch)")
  - `Basiswert` full name from `<span title>` + `underlying_link` from `<a href>`
  - `Basispreis` (split into value + currency), `Bezugsverhältnis`, `Fälligkeit`, `letzter Handelstag`
  - `Emittent` full name from `<a title>`
- ✅ `clean_float_value()` and `Bil.` (10^12) support added to `parsing_utils.py`
- ✅ Shared parsing utilities in `parsing_utils.py` (used by all parsers and `quotes.py`)
- ✅ All legacy parsing code removed from `instruments.py`; no fallback path exists
- ✅ MongoDB Atlas integration using PyMongo `AsyncMongoClient`
- ✅ FastAPI routers: welcome, instruments, quotes, history, depots, warrants, indices
- ✅ Custom `JSONResponse` with UTF-8 charset for German umlauts
- ✅ CI/CD via GitHub Actions (lint + tests on PR; build + push + deploy to Azure on main)
- ✅ CORS middleware added (`allow_origins=["*"]`, `allow_methods=["GET"]`)
- ✅ API key protection on all data endpoints (`X-API-Key` header)
- ✅ 104 unit tests passing

# Open / Future Work

- Bond, ETF, Fonds, Certificate, Index, Commodity, Currency details parsers not yet implemented (models exist, parsers return `None`)
- Integration tests for parsers / scrapers not yet added
- DB initialization script (WKN/ISIN indexes on instruments collection) not yet created
