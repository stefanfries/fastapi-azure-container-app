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

## Current State

All original technical requirements are met. The following has been implemented:

- ✅ Plugin system covering all 9 asset classes (STOCK, BOND, ETF, FONDS, CERTIFICATE, WARRANT, INDEX, COMMODITY, CURRENCY)
  - `StockParser`, `BondParser`, `ETFParser`, `FondsParser`, `CertificateParser` (all extend `StandardAssetParser`) — STOCK, BOND, ETF, FONDS, CERTIFICATE
  - `WarrantParser` (extends `StandardAssetParser`) — WARRANT
  - `SpecialAssetParser` — INDEX, COMMODITY, CURRENCY (non-tradeable, no venues)
- ✅ Asset-class-specific detail models (`app/models/instrument_details.py`)
  - 9 Pydantic models: `StockDetails`, `BondDetails`, `ETFDetails`, `FondsDetails`, `WarrantDetails`, `CertificateDetails`, `IndexDetails`, `CommodityDetails`, `CurrencyDetails`
  - Discriminated union `InstrumentDetails` keyed on `asset_class` literal
  - Optional `details` field on `Instrument` model
- ✅ Stock details parser — `StockParser._parse_stock_details()` extracts:
  - `Wertpapiertyp`, `Marktsegment`, `Branche` (full name from `<span title>`), `Geschäftsjahr` (as DD-MM)
  - `Marktkapital.` (with Bil./Mrd./Mio. + currency), `Streubesitz`, `Nennwert`, `Stücke`
- ✅ Bond details parser — `BondParser._parse_bond_details()` extracts:
  - `Emittent`, `Kupon`, `Kupontyp`, `Emissionsdatum`, `Fälligkeit`, `Nennwert`, `Anleihetyp`, `Rating Moody's`, `Rating S&P`, `Währung`
- ✅ ETF details parser — `ETFParser._parse_etf_details()` extracts:
  - `Referenzindex`, `Gesamtkostenquote (TER)`, `Replikationsmethode`, `Ertragsverwendung`, `Fondsdomizil`, `Auflagedatum`, `Fondswährung`, `Fondsvermögen`
- ✅ Fonds details parser — `FondsParser._parse_fonds_details()` extracts:
  - `Fondstyp`, `Fondsgesellschaft`, `Auflagedatum`, `Fondsdomizil`, `Ertragsverwendung`, `Gesamtkostenquote (TER)`, `Fondswährung`, `Fondsvermögen`
- ✅ Certificate details parser — `CertificateParser._parse_certificate_details()` extracts:
  - `Zertifikatstyp`, `Basiswert`, `Cap`, `Barriere`, `Partizipationsrate`, `Fälligkeit`, `Emittent`, `Währung`
- ✅ Shared helpers `_parse_date()` and `_split_value_currency()` in `StandardAssetParser` (inherited by all concrete parsers)
- ✅ Warrant details parser — `WarrantParser._parse_warrant_details()` extracts:
  - `Typ` (full exercise style from `<span title>`, e.g. "Call (Amerikanisch)")
  - `Basiswert` full name from `<span title>` + `underlying_link` from `<a href>`
  - `Basispreis` (split into value + currency), `Bezugsverhältnis`, `Fälligkeit`, `letzter Handelstag`
  - `Emittent` from visible `<td>` display text (`get_text()`)
- ✅ Index details parser — `SpecialAssetParser._parse_index_details()` extracts:
  - `Land` → `country`, `Landeswährung` → `currency`, `Enthaltene Werte` → `num_constituents`
  - `ISIN` / `WKN` from Stammdaten table → `constituents_url` (e.g. `/v1/indices/DE0008469008`)
- ✅ Commodity details parser — `SpecialAssetParser._parse_commodity_details()` extracts:
  - `Landeswährung` → `currency`, `Symbol` → `symbol`, `Land` → `country`
- ✅ Currency details parser — `SpecialAssetParser._parse_currency_details()` extracts:
  - `Wechselkurs` (e.g. `EUR/USD`) split into `base_currency` / `quote_currency`, `Land` → `country`
- ✅ `SpecialAssetParser.parse_isin()` reads ISIN from Stammdaten table (previously hardcoded `None`)
- ✅ `SpecialAssetParser.parse_wkn()` returns `None` gracefully for instruments without WKN (e.g. L&S Brent Oil)
- ✅ `parse_symbol()` in `instruments.py` reads Symbol from Stammdaten for non-STOCK asset classes
- ✅ `IndexMember` model includes `instrument_url` (e.g. `/v1/instruments/DE0007164600`)
- ✅ `GET /v1/indices/{name|isin|wkn}` accepts name, WKN, or ISIN — including tracking ISINs not in comdirect catalogue (cross-ISIN fallback)
- ✅ `clean_float_value()` and `Bil.` (10^12) support added to `parsing_utils.py`
- ✅ Shared parsing utilities in `parsing_utils.py` (used by all parsers and `quotes.py`)
- ✅ All legacy parsing code removed from `instruments.py`; no fallback path exists
- ✅ MongoDB Atlas integration using PyMongo `AsyncMongoClient`
- ✅ FastAPI routers: welcome, instruments, quotes, history, depots, warrants, indices, health
- ✅ Custom `JSONResponse` with UTF-8 charset for German umlauts
- ✅ CI/CD via GitHub Actions (lint + tests on PR; build + push + deploy to Azure on main)
- ✅ CORS middleware added (`allow_origins=["*"]`, `allow_methods=["GET"]`)
- ✅ API key protection on all data endpoints (`X-API-Key` header)
  - Open mode when `API_KEY` env var is unset; startup error when `API_KEY` is an empty string
- ✅ `GET /v1/instruments/` list endpoint — optional `?asset_class=` query param, validated via `AssetClass` enum
- ✅ Sparse unique indexes on `wkn` and `isin` created in `connect_to_database()` at startup (idempotent)
- ✅ `InstrumentRepository.save()` falls back to ISIN key for foreign instruments where `wkn=None`
- ✅ `Instrument` model validator: every instrument must have at least a WKN or an ISIN (`model_validator`)
- ✅ 388 unit tests passing; 82% code coverage (exceeds 80% target)
- ✅ Warrant Finder endpoint (`GET /v1/warrants/`) with full Greek/analytics filter support
  - All 14 comdirect filter dimensions exposed with independent `_min` / `_max` bounds:
    `delta`, `omega` (GEARING), `moneyness`, `premium_per_annum`, `implied_volatility`,
    `leverage`, `spread_ask_pct`, `theta_day`, `present_value`, `theoretical_value`,
    `intrinsic_value`, `break_even`, `vega`, `gamma`
  - Dual bounds encoded as repeated query parameters (Strategy C, confirmed via probe script):
    `DELTA_VALUE=0.5&DELTA_COMPARATOR=gt&DELTA_VALUE=0.8&DELTA_COMPARATOR=lt`
  - `_greek_filter_pairs(prefix, min_val, max_val)` helper builds the pair list; disabled filter emitted
    as empty value + `gt` comparator to satisfy comdirect's required parameter structure
  - Comparators supported: `gt` (greater than) and `lt` (less than).
    `eq` (equal) was evaluated and rejected — returns 0 results for all continuous analytics values
    because comdirect applies exact float matching server-side
  - **Sentinel value caveat**: warrants without published analytics are assigned a sentinel ≥ 1.0 by
    comdirect; combining `issuer_action=true` with upper-bound Greek filters may exclude them
    unexpectedly — documented in the `issuer_action` / `issuer_no_fee_action` Query param descriptions

## Open / Future Work

- Integration tests for parsers / scrapers not yet added
- E2E tests not yet added
- Coverage threshold enforcement (`--cov-fail-under`) not yet configured in CI
