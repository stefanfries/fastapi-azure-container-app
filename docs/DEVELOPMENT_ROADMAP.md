# Development Roadmap: FinHub API

## Executive Summary

Based on a comprehensive review of the codebase against business and technical requirements, this plan outlines a phased approach to complete the application. **FinHub API** is a financial data aggregator using web scraping to provide unified, structured access to financial instruments data. The project has a solid foundation (CI/CD, basic API structure, plugin system), but critical gaps exist in database integration, authentication, testing, and parser completeness.

---

## Current State Assessment

### ✅ Completed Components

- FastAPI application structure with routers (root, instruments, quotes, history, depots, warrants, indices, health)
- Plugin-based parser system — **all 9 asset classes fully covered** (no legacy fallback):
  - `StandardAssetParser` — STOCK, BOND, ETF, FONDS, CERTIFICATE
  - `WarrantParser` — WARRANT (id_notation refetch mechanism)
  - `SpecialAssetParser` — INDEX, COMMODITY, CURRENCY (non-tradeable, no venues)
- Shared parsing utilities in `parsing_utils.py` used by all parsers and `quotes.py`
- All legacy parsing code removed from `instruments.py`
- Web scraping infrastructure (httpx + BeautifulSoup)
- Data models (Instrument, Depot, History, Quote)
- CRUD operations for depots and instruments
- MongoDB Atlas integration using PyMongo `AsyncMongoClient`
- Docker containerization
- CI/CD pipeline with GitHub Actions (quality checks + Azure deployment)
- Logging configuration
- ID notation system for trading venues
- API terminology aligned with financial domain (instruments, quotes, history)
- Repository pattern implemented for data entities (`InstrumentRepository`, `DepotRepository`)
- All API routes versioned under `/v1/` (instruments, quotes, history, warrants, indices, depots)
- `GET /` root endpoint returns structured app metadata (name, version, api_version, data_sources, docs, health)
- `GET /health` liveness probe and `GET /health/ready` readiness probe implemented
- Test infrastructure set up: `tests/unit/`, `tests/integration/`, `pytest-asyncio`, `pytest-mock`, `conftest.py`
- 26 unit tests passing; coverage reporting enabled (~45%)
- `app/core/security.py` — API key protection (`X-API-Key` header) on all data endpoints
- Toolchain: `ruff` for linting and formatting (replaced `black` + `pylint`)

### ⚠️ Partially Completed

- **Testing**: 388 unit tests passing; no parser/scraper integration tests yet
- **Error Handling**: Basic middleware exists, could be enhanced
- **API Documentation**: Auto-generated OpenAPI; no detailed endpoint docs beyond auto-generation

### ❌ Missing Components

- **Integration Tests**: No tests for parsers, scrapers, or end-to-end flows
- **Load Testing**: No performance or scalability verification
- **DB Initialization Script**: WKN/ISIN indexes not yet created on instruments collection
- **Software Release Versioning**: No dedicated version module; version set via `app_version` in settings

---

## Prioritized Development Plan

### Phase 0: API Terminology Refactoring ✅ COMPLETED

All renaming from legacy `basedata`/`pricedata` terminology to financial domain terminology (`instruments`, `quotes`) has been completed. The plugin system now covers all 9 asset classes.

---

### Phase 1: Foundation & Code Quality (Week 1-2)

Priority: HIGH - Required for reliable development

#### 1.1 Clean Up Technical Debt

- [x] Replace all `print()` statements with `logger` calls ✅
  - No `print()` statements found anywhere in `app/`
  - All modules use `logger` from `app.core.logging`
  
- [x] Logging module implemented ✅ (`app/core/logging.py`, `api_logger`)
  - [ ] Add comprehensive entry/exit logging to parsers and scrapers (still partial)

#### 1.2 Database Integration

- [x] Add MongoDB dependencies ✅ (`pymongo>=4.16.0` in `pyproject.toml`)
  
- [x] Create database configuration module ✅ (`app/core/database.py`)
  - `AsyncMongoClient` with lifespan hooks in `main.py`
  - `Collections` constants class
  - Connection string via environment variable (`MONGODB_URI`)
  
- [x] Implement repository pattern ✅
  - [x] `app/repositories/` directory created ✅
  - [x] **InstrumentRepository** implemented ✅ (find_by_wkn, find_by_isin, caching)
  - [x] **DepotRepository** implemented ✅ (find_all, find_by_id, create, update, delete)
  - ~~UserRepository~~ — removed; user management belongs in the consuming application
  - [ ] **QuoteRepository** (optional - for quote caching if needed)
  
- [ ] Add database initialization script
  - Index creation for performance (WKN, ISIN indexes on instruments collection)
  - Schema validation setup

#### 1.3 Testing Foundation

- [x] Set up comprehensive test structure ✅
  - [x] `tests/unit/` and `tests/integration/` directories created ✅
  - [x] `tests/conftest.py` with `mock_database` and `client` fixtures ✅
  - [ ] `tests/e2e/` directory (deferred to Phase 4)
  
- [x] Add pytest plugins ✅
  - [x] `pytest-asyncio` installed (`asyncio_mode = "auto"`) ✅
  - [x] `pytest-mock` installed ✅
  - [ ] `pytest-env` for environment management (not yet needed)
  
- [ ] Establish test coverage targets
  - [x] Coverage reporting configured in `pyproject.toml` ✅ (currently ~38%)
  - [ ] Reach minimum 80% coverage for new code

#### 1.4 API & Software Versioning

- [x] Implement API route versioning ✅
  - [x] `/v1/` prefix on all data routers: `instruments`, `quotes`, `history`, `warrants`, `indices`, `depots` ✅
  - [ ] Consider restructuring into `app/api/v1/` if versioning beyond v1 is needed
  
- [x] Add software release versioning ✅
  - `app_version` field in `app/core/settings.py` (default `"0.1.0"`)
  - Version exposed via `FastAPI(version=...)` in `main.py` and in `GET /health/ready` response
  - [ ] No dedicated `app/version.py` module; version set via `APP_VERSION` env var
  
- [x] Improve root endpoint (`/`) ✅ (`app/routers/root.py`)
  - Returns structured response:

    ```json
    {
      "application": "FinHub API",
      "version": "0.1.0",
      "api_version": "v1",
      "data_sources": ["comdirect"],
      "docs": "/docs",
      "health": "/health"
    }
    ```

- [x] Implement liveness health endpoint (`/health`) ✅ (`app/routers/health.py`)
  - Returns `{"status": "healthy", "timestamp": "..."}` immediately
  - Used as Azure Container Apps **liveness probe**

- [x] Implement readiness health endpoint (`/health/ready`) ✅
  - Checks MongoDB ping + comdirect.de reachability (via `robots.txt` HEAD request)
  - Returns 200 with check results when all pass, 503 if any fail
  - Used as Azure Container Apps **readiness probe**
  
- [ ] Update deployment pipeline
  - Auto-increment version on releases
  - Tag Docker images with version numbers
  - Add version to CI/CD workflow outputs
  
- [ ] Add version to logs and error responses
  - Include version in structured logs
  - Add `X-API-Version` header to all responses

**Deliverables:**

- ✅ No print() statements — all modules use structured logger
- ✅ MongoDB connected and configured (`app/core/database.py`, lifespan hooks)
- ✅ Repositories implemented: `InstrumentRepository`, `DepotRepository`
- ✅ All routes under `/v1/` (instruments, quotes, history, warrants, indices, depots)
- ✅ API key protection on all data endpoints (`app/core/security.py`, `X-API-Key` header)
- ✅ `app_version` in settings and FastAPI metadata
- ✅ Test infrastructure: `tests/unit/`, `tests/integration/`, `pytest-asyncio`, `pytest-mock`, `conftest.py`
- ✅ Root `/` returns structured app metadata (`app/routers/root.py`)
- ✅ Health endpoints implemented (`/health`, `/health/ready`) in `app/routers/health.py`
- ✅ 388 unit tests passing; coverage reporting active
- ✅ Toolchain: `ruff` for linting and formatting
- [ ] DB initialization script (WKN/ISIN indexes on instruments collection)
- [ ] Docker image version tagging in CD pipeline

---

### Phase 2: Complete Asset Class Support (Week 3-5)

Priority: HIGH - Core business requirement

#### 2.1 Extend Data Models ✅ COMPLETED

- [x] Create asset-class-specific model extensions (`app/models/instrument_details.py`) ✅
  - `StockDetails` — security_type, market_segment, sector, fiscal_year_end (DD-MM), market_cap, market_cap_currency, free_float, nominal_value, nominal_value_currency, shares_outstanding
  - `BondDetails` — issuer, coupon_rate_percent, coupon_type, issue_date, maturity_date, nominal_value, bond_type, currency
  - `ETFDetails` — tracked_index, expense_ratio_percent, replication_method, distribution_policy, inception_date, fund_currency, fund_size
  - `FondsDetails` — fund_type, fund_manager, inception_date, distribution_policy, expense_ratio_percent, fund_currency, fund_size
  - `WarrantDetails` — warrant_type (full exercise style), underlying_name, underlying_link, strike, strike_currency, ratio, maturity_date, last_trading_day, issuer
  - `CertificateDetails` — certificate_type, underlying_name, cap, cap_currency, barrier, barrier_currency, participation_rate, maturity_date, issuer, currency
  - `IndexDetails` — index_type, index_provider, country, base_value, base_date, num_constituents
  - `CommodityDetails` — commodity_type, unit, source_exchange
  - `CurrencyDetails` — base_currency, quote_currency
  - `InstrumentDetails` discriminated union keyed on `asset_class` literal

- [x] Update `Instrument` model ✅
  - Optional `details: InstrumentDetails | None` field added
  - Fully backward-compatible (field is `None` when parser not yet implemented)

- [ ] Update database schema
  - MongoDB stores `details` as embedded subdocument; verify `InstrumentRepository` handles it

#### 2.2 Implement Asset-Class-Specific Parsers

- [x] All 9 asset classes registered in plugin system ✅
  - `StockParser`, `BondParser`, `ETFParser`, `FondsParser`, `CertificateParser` (all extend `StandardAssetParser`) — STOCK, BOND, ETF, FONDS, CERTIFICATE
  - `WarrantParser` (extends `StandardAssetParser`) — WARRANT
  - `SpecialAssetParser` — INDEX, COMMODITY, CURRENCY
- [x] `parse_details()` default implementation in `InstrumentParser` base class returns `None` ✅
- [x] `StockDetails` parser implemented in `StockParser._parse_stock_details()` ✅
  - Reads "Aktieninformationen" table; handles `<span title>` for Branche, `Bil.`/`Mrd.`/`Mio.` for market cap
- [x] `BondDetails` parser implemented in `BondParser._parse_bond_details()` ✅
  - Reads "Anleiheinformationen" table; extracts coupon, maturity, credit ratings
- [x] `ETFDetails` parser implemented in `ETFParser._parse_etf_details()` ✅
  - Reads "ETF-Informationen" table; extracts TER, replication method, fund size
- [x] `FondsDetails` parser implemented in `FondsParser._parse_fonds_details()` ✅
  - Reads "Fondsinformationen" table; extracts fund manager, distribution policy, fund size
- [x] `CertificateDetails` parser implemented in `CertificateParser._parse_certificate_details()` ✅
  - Reads "Zertifikatinformationen" table; extracts type, cap, barrier, participation rate
- [x] `WarrantDetails` parser implemented in `WarrantParser._parse_warrant_details()` ✅
  - `Typ`: reconstructs full exercise style from `<span title>` ("Call (Amerikanisch)")
  - `Basiswert`: full name from `<span title>`, `underlying_link` from `<a href>`
  - `Emittent`: visible `<td>` display text (`get_text()`)
  - Tests in `tests/unit/parsers/plugins/test_warrant_parser.py`
- [x] Tests restructured to mirror `app/` directory layout ✅
  - `tests/unit/parsers/test_standard_asset_parser.py` — shared helpers (`_parse_date`, `_split_value_currency`)
  - `tests/unit/parsers/test_special_asset_parser.py` — `SpecialAssetParser` interface
  - `tests/unit/parsers/plugins/` — one test file per concrete parser
- [ ] Remaining `parse_details()` implementations (models exist, return `None`): ~~SpecialAssetParser: IndexDetails, CommodityDetails, CurrencyDetails~~ ✅ COMPLETED
- [x] `SpecialAssetParser._parse_index_details()` — `country`, `currency`, `num_constituents`, `constituents_url` (ISIN/WKN → `/v1/indices/{id}`) ✅
- [x] `SpecialAssetParser._parse_commodity_details()` — `currency`, `symbol`, `country` ✅
- [x] `SpecialAssetParser._parse_currency_details()` — `base_currency`, `quote_currency` (split from `Wechselkurs`), `country` ✅
- [x] `SpecialAssetParser.parse_isin()` reads from Stammdaten table (no longer hardcoded `None`) ✅
- [x] `SpecialAssetParser.parse_wkn()` returns `None` gracefully instead of raising for missing WKN ✅
- [x] `parse_symbol()` in `instruments.py` handles all asset classes via Stammdaten `"Symbol"` row ✅
- [x] `IndexMember.instrument_url` added (e.g. `/v1/instruments/DE0007164600`) ✅
- [x] `GET /v1/indices/{isin}` cross-ISIN fallback — works for tracking ISINs not in comdirect catalogue ✅

#### 2.3 Update API Endpoints ✅ COMPLETED

- [x] `GET /v1/instruments/{wkn}` response includes `details` field with asset-class-specific data ✅
- [x] `GET /v1/instruments/` list endpoint wired ✅ — optional `?asset_class=` query param, validated via `AssetClass` enum, delegated to `InstrumentRepository.find_all()`

#### 2.4 Remove Legacy Parsing Code ✅ COMPLETED

- [x] All legacy functions removed from `app/parsers/instruments.py` ✅
- [x] `quotes.py` uses shared `parsing_utils` functions ✅
- [x] No legacy fallback path in plugin system ✅

- ✅ All 9 asset classes supported by plugin system
- ✅ Asset-class-specific data models defined and integrated into `Instrument`
- ✅ `GET /v1/instruments/{wkn|isin}` returns enriched `details` for ALL 9 asset classes (STOCK, BOND, ETF, FONDS, CERTIFICATE, WARRANT, INDEX, COMMODITY, CURRENCY)
- ✅ `IndexDetails`: `country`, `currency`, `num_constituents`, `constituents_url`
- ✅ `CommodityDetails`: `currency`, `symbol`, `country`
- ✅ `CurrencyDetails`: `base_currency`, `quote_currency`, `country`
- ✅ `IndexMember.instrument_url` cross-links to `/v1/instruments/{isin}`
- ✅ `GET /v1/indices/{name|isin|wkn}` accepts ISIN directly with cross-ISIN fallback
- ✅ 388 unit tests; test layout mirrors `app/` directory structure

---

### Phase 3: Security & Authentication ✅ COMPLETED

**Decision:** This API is a private financial data service. User management (registration, login, roles, RBAC) belongs in the consuming application — not here.

- [x] API key protection implemented ✅
  - `app/core/security.py` — `require_api_key` FastAPI dependency
  - All 6 data routers protected: `instruments`, `quotes`, `history`, `warrants`, `indices`, `depots`
  - Key passed via `X-API-Key` request header
  - Configured via `API_KEY` environment variable / Azure Container App secret
  - Open mode when `API_KEY` is unset (safe for local development)
  - **Empty string `API_KEY=""` is rejected at startup** with a validation error (prevents accidental open access)
- [x] Public endpoints remain unprotected: `/`, `/docs`, `/health`, `/health/ready`
- [x] `UserRepository`, `UserModel`, `/v1/users` router removed

---

### Phase 4: Comprehensive Testing (Week 8-9)

Priority: MEDIUM-HIGH - Ensure reliability

#### 4.1 Unit Tests

- [ ] Test all parser plugins
  - Mock HTTP responses
  - Test each asset class parser independently
  - Edge cases: missing fields, malformed HTML
  
- [ ] Test all CRUD operations
  - Repository layer tests
  - Mock database interactions
  
- [ ] Test data models
  - Pydantic validation
  - Field constraints

#### 4.2 Integration Tests

- [ ] Test complete API flows
  - User registration → login → fetch instrument data
  - Test with real comdirect scraping (sandboxed)
  
- [ ] Test database interactions
  - Repository layer with test database
  - Data persistence and retrieval
  
- [ ] Test parser factory
  - Dynamic parser selection based on asset class

#### 4.3 End-to-End Tests

- [ ] Test deployment flow
  - Build Docker image
  - Deploy to test environment
  - Verify all endpoints
  
- [ ] Test error scenarios
  - Invalid authentication
  - Instrument not found
  - Network failures

#### 4.4 Coverage Targets

- [ ] Achieve minimum 80% code coverage
- [ ] Generate coverage reports in CI
- [ ] Enforce coverage thresholds

**Deliverables:**

- Comprehensive test suite (100+ tests)
- 80%+ code coverage
- Automated test execution in CI

---

### Phase 5: Performance & Production Readiness (Week 10-11)

Priority: MEDIUM - Optimize for production

#### 5.1 Caching Strategy

- [ ] Implement instrument data caching
  - Cache parsed instrument data in MongoDB
  - TTL-based cache invalidation (instruments rarely change)
  - Cache hit/miss logging
  
- [ ] Implement quote caching
  - Short-lived cache (5-15 minutes for real-time quotes)
  - Update strategy for real-time data
  - Consider WebSocket updates for real-time scenarios

#### 5.2 Error Handling Enhancement

- [ ] Create custom exception hierarchy
  - `InstrumentNotFoundException`
  - `ParserException`
  - `AuthenticationException`
  
- [ ] Implement global exception handlers
  - Standardized error responses
  - Error logging with context
  - User-friendly error messages
  
- [ ] Add retry logic
  - Retry failed HTTP requests (with exponential backoff)
  - Circuit breaker pattern for external dependencies

#### 5.3 Monitoring & Observability

- [ ] Add structured logging
  - JSON log format for parsing
  - Request ID tracking across logs
  
- [ ] Add application metrics
  - Request count, latency
  - Parser success/failure rates
  - Cache hit rates
  - Health check response times
  
- [ ] Enhance health endpoint monitoring (building on Phase 1 implementation)
  - Add metrics collection from `/health/ready` checks
  - Monitor dependency health trends
  - Alert on repeated health check failures
  - Add more detailed dependency checks (comdirect availability, etc.)
  - Configure Azure Container Apps health probe settings
    - Liveness probe: `/health`
    - Readiness probe: `/health/ready`
    - Startup probe configuration

#### 5.4 Performance Optimization

- [ ] Profile critical paths
  - Parser performance
  - Database query performance
  
- [ ] Add database indexes
  - Index on WKN, ISIN for fast lookups
  - Composite indexes for common queries
  
- [ ] Optimize scraping
  - Connection pooling
  - Request batching where possible

#### 5.5 Load Testing

- [ ] Create load test scenarios
  - Concurrent user simulation
  - High-volume instrument data requests
  - Real-time quote streaming scenarios
  
- [ ] Run load tests
  - Use `locust` or `k6`
  - Identify bottlenecks
  
- [ ] Establish performance baselines
  - Target: p95 latency < 500ms for instrument lookups
  - Target: p95 latency < 1000ms for quote fetching (scraping involved)
  - Target: Handle 100+ concurrent requests

#### 5.6 Robots.txt Compliance & Transparency

Implement automated checking of comdirect.de's robots.txt before making requests to ensure responsible web scraping and maintain transparency.

- [ ] Create robots.txt parser module
  - File: `app/scrapers/robots_checker.py`
  - Parse robots.txt from comdirect.de
  - Cache robots.txt with TTL (refresh every 24 hours)
  - Support for User-agent specific rules
  - Support for Allow/Disallow patterns with wildcards

- [ ] Implement URL compliance checker
  - Check if URL path matches Allow patterns
  - Check if URL path matches Disallow patterns
  - Handle wildcard patterns (`/inf/*/detail/`)
  - Return compliance status (ALLOWED, DISALLOWED, NOT_SPECIFIED)

- [ ] Integrate checker into fetch functions
  - Add robots.txt check before every `fetch_one()` call
  - Log INFO when URL is ALLOWED
  - Log WARNING when URL is DISALLOWED
  - **Still proceed with request** even if disallowed (for transparency/logging only)
  - Include URL path and rule matched in logs

- [ ] Add robots.txt endpoint to API
  - GET `/robots-compliance/{path}` - Check if a path is allowed
  - GET `/robots-compliance/report` - Summary of recent checks
  - Include in root endpoint (`/`) response

- [ ] Review and document current compliance
  - **ALLOWED**: `/inf/*/detail/uebersicht.html` (all asset classes) ✓
  - **ISSUE**: `/inf/search/all.html` conflicts with `Disallow: /inf/search/`
  - **ALLOWED**: `/inf/kursdaten/historic.csv` (not explicitly disallowed) ✓
  - Document findings in `docs/ROBOTS_COMPLIANCE.md`

- [ ] Address identified issues
  - Consider alternative approach for search functionality
  - Evaluate if search endpoint is necessary
  - If needed, contact comdirect for permission or clarification

- [ ] Add configuration option
  - Environment variable `OBEY_ROBOTS_TXT` (default: `false` for logging only)
  - **If `false`**: Log WARNING and proceed with request (transparency mode)
  - **If `true`**: Log ERROR and raise exception if URL is disallowed
    - Check for alternative URLs/endpoints first
    - Only raise error if no compliant alternative exists
    - Raise `RobotsTxtViolationError` with details
  - Allow override for testing/development

- [ ] Implement fallback/alternative URL logic
  - Define alternative endpoints for disallowed paths
  - Example: If `/inf/search/all.html` is blocked, use allowed alternative
  - Document which endpoints have alternatives
  - Automatically try alternative before failing

**Example Log Output:**

```log
# When OBEY_ROBOTS_TXT=false (default - transparency mode)
2026-02-16 10:45:58 api_logger INFO [robots_checker:check_url:45] 
  Checking robots.txt compliance for: /inf/aktien/detail/uebersicht.html
  Result: ALLOWED (matches: Allow: /inf/*/detail/uebersicht.html)
  User-agent: * | Proceeding with request
  
2026-02-16 10:46:10 api_logger WARNING [robots_checker:check_url:48]
  Checking robots.txt compliance for: /inf/search/all.html
  Result: DISALLOWED (matches: Disallow: /inf/search/)
  User-agent: * | Proceeding anyway (OBEY_ROBOTS_TXT=false)

# When OBEY_ROBOTS_TXT=true (enforcement mode)
2026-02-16 10:46:10 api_logger ERROR [robots_checker:check_url:52]
  Checking robots.txt compliance for: /inf/search/all.html
  Result: DISALLOWED (matches: Disallow: /inf/search/)
  User-agent: * | OBEY_ROBOTS_TXT=true
  No alternative endpoint available
  Raising RobotsTxtViolationError

# When OBEY_ROBOTS_TXT=true with alternative
2026-02-16 10:46:15 api_logger WARNING [robots_checker:check_url:55]
  Checking robots.txt compliance for: /inf/search/all.html
  Result: DISALLOWED (matches: Disallow: /inf/search/)
  User-agent: * | OBEY_ROBOTS_TXT=true
  Using alternative endpoint: /inf/search/general.html (ALLOWED)
```

**Benefits:**

- Demonstrates responsible web scraping practices
- Transparency about compliance status
- Easy to identify potential issues with comdirect
- Provides audit trail for compliance
- Can be enforced if needed without code changes

**Deliverables:**

- Robust error handling
- Application monitoring
- Performance benchmarks
- Load test results
- Robots.txt compliance checker
- Transparency logging for all requests

---

### Phase 6: Documentation & API Enhancement (Week 12)

Priority: MEDIUM - Improve developer experience

#### 6.1 API Documentation

- [ ] Enhance OpenAPI documentation
  - Add detailed descriptions to all endpoints
  - Add request/response examples
  - Document error responses
  
- [ ] Create API usage guide
  - Authentication flow examples
  - Common use cases
  - Code samples (Python, JavaScript)
  
- [ ] Document API versioning strategy (already implemented in Phase 1.4)
  - Document version in URL path (`/v1/instruments`)
  - Create deprecation policy for future versions
  - Document migration guide for version upgrades
  - Add versioning best practices to API guide

#### 6.2 Technical Documentation

- [ ] Create architecture diagram
  - System components
  - Data flow diagrams
  
- [ ] Document parser plugin system
  - How to add new asset class parsers
  - Parser interface contract
  
- [ ] Document deployment process
  - Azure Container Apps setup
  - Environment variable configuration
  - Secrets management

#### 6.3 Developer Onboarding

- [ ] Update README.md
  - Prerequisites
  - Setup instructions
  - Common commands
  
- [ ] Create CONTRIBUTING.md
  - Code style guidelines
  - PR process
  - Testing requirements
  
- [ ] Add inline code documentation
  - Docstrings for all public functions
  - Type hints everywhere

**Deliverables:**

- Comprehensive API documentation
- Architecture and system docs
- Developer onboarding guide

---

## Success Metrics

### Phase 1 (Foundation)

- ✅ Zero print() statements — all modules use structured logger
- ✅ MongoDB connection established and all repositories implemented
- ✅ Repository pattern for all entities (Instrument, User, Depot)
- ✅ Test infrastructure: `tests/unit/`, `tests/integration/`, `conftest.py`, pytest-asyncio
- ✅ All routes versioned under `/v1/`
- ✅ Root endpoint (`/`) returns structured app metadata
- ✅ Health endpoints (`/health`, `/health/ready`) implemented
- ✅ 28 unit tests passing; coverage reporting active
- [ ] DB initialization script (WKN/ISIN indexes)
- [ ] Azure Container Apps health probe configuration in deployment pipeline

### Phase 2 (Asset Classes)

- All 9 asset classes parseable
- Asset-class-specific data models defined and integrated into `Instrument`
- Parsers extended to extract asset-class-specific fields
- `GET /v1/instruments/{wkn}` returns full enriched data per asset class

### Phase 3 (Security)

- All routes protected with authentication
- JWT-based login/registration working
- Role-based access control implemented

### Phase 4 (Testing)

- 80%+ code coverage
- 100+ tests passing
- CI pipeline includes all tests

### Phase 5 (Performance)

- p95 latency < 500ms
- Handles 100+ concurrent users
- Comprehensive error handling
- Robots.txt compliance checker implemented
- All web scraping requests logged for transparency

### Phase 6 (Documentation)

- Complete API documentation
- Architecture diagrams
- Developer onboarding guide

### Phase 7 (MCP Server)

- MCP server successfully wraps all FastAPI endpoints
- Core MCP tools implemented (get_instrument, get_quote, get_history)
- Analysis tools functional (portfolio performance, comparison, etc.)
- Prompts guide common workflows
- Optional metadata resources for reference data
- Claude Desktop integration working
- <15 minutes setup time for new users
- Comprehensive MCP documentation

---

## Risk Mitigation

### Technical Risks

1. **Web Scraping Fragility**: Comdirect may change HTML structure
   - Mitigation: Comprehensive tests, monitoring for failures, abstraction layer

2. **Database Performance**: MongoDB performance at scale
   - Mitigation: Proper indexing, query optimization, load testing

3. **Authentication Complexity**: Security implementation errors
   - Mitigation: Use battle-tested libraries, security audit

### Process Risks

1. **Scope Creep**: Too many features at once
   - Mitigation: Phased approach, clear deliverables per phase

2. **Technical Debt**: Rushing implementation
   - Mitigation: Code reviews, test coverage requirements

---

## Next Steps

1. **Finish Phase 1** — DB initialization script (WKN/ISIN indexes on instruments collection) is the only remaining item
2. **Start Phase 2** — Asset-class-specific data models and extended parsers
3. **Raise test coverage** towards 80% as Phase 2 work lands

## Questions for Stakeholders

1. **Authentication**: Do we need to support external auth providers (Google, Microsoft) or is username/password sufficient?
2. **Asset Classes**: Which asset classes are highest priority? Can we phase them?
3. **Data Persistence**: What's the expected data retention policy for scraped data?
4. **Performance**: What are acceptable latency targets for API responses?
5. **Deployment**: Do we need multiple environments (dev, staging, prod)?

---

## Appendix: File Inventory

### Current File Structure

```text
app/
├── core/              # Settings, database, logging, constants, security
├── models/            # Pydantic models (instruments, instrument_details, depots,
│                      #                  history, quotes, indices, warrants, types)
├── parsers/           # Parsing logic
│   └── plugins/       # Parser plugin system (standard, warrant, special)
├── repositories/      # MongoDB repository layer (instruments, depots)
├── routers/           # API routes (root, health, instruments, quotes, history,
│                      #             depots, warrants, indices)
├── scrapers/          # Web scraping utilities
├── services/          # Business logic (identifier enrichment)
├── clients/           # External API clients (OpenFIGI)
├── static/            # Static files
├── main.py            # Application entry point with lifespan hooks
└── middleware.py      # Request middleware

tests/
├── conftest.py                         # Shared fixtures (mock_database, client)
├── unit/
│   ├── test_main.py                    # App startup tests
│   ├── core/
│   │   └── test_security.py            # API key security tests
│   ├── models/
│   │   └── test_instrument_details.py  # InstrumentDetails union tests
│   ├── parsers/
│   │   ├── test_standard_asset_parser.py  # _parse_date, _split_value_currency
│   │   ├── test_special_asset_parser.py   # SpecialAssetParser interface
│   │   └── plugins/
│   │       ├── test_parsing_utils.py      # clean_float_value, clean_numeric_value
│   │       ├── test_stock_parser.py
│   │       ├── test_bond_parser.py
│   │       ├── test_etf_parser.py
│   │       ├── test_fonds_parser.py
│   │       ├── test_certificate_parser.py
│   │       ├── test_warrant_parser.py
│   │       └── test_factory.py
│   ├── repositories/
│   │   └── test_depot_repository.py    # DepotRepository unit tests
│   └── routers/
│       └── test_root.py                # Root endpoint tests
└── integration/                        # Integration tests (to be added)

docs/
├── BUSINESS_REQUIREMENTS.md
├── TECHNICAL_REQUIREMENTS.md
├── DEPLOYMENT.md
├── PLUGIN_SYSTEM_DOCUMENTATION.md
└── [other documentation files]

scripts/
├── deploy-to-azure.ps1
└── [various analysis scripts]

.github/workflows/
├── ci-quality.yml     # Code quality checks
└── cd-deploy.yml      # Deployment pipeline
```

### Files to Create (by Phase)

**Phase 1:** ✅ All created

- ✅ `app/core/database.py` (PyMongo `AsyncMongoClient`, lifespan hooks)
- ✅ `app/repositories/instruments.py` (InstrumentRepository)
- ✅ `app/repositories/users.py` (UserRepository)
- ✅ `app/repositories/depots.py` (DepotRepository)
- ✅ `app/routers/health.py` (liveness + readiness endpoints)
- ✅ `app/routers/root.py` (renamed from welcome.py, returns structured metadata)
- ✅ `tests/conftest.py` (mock_database and client fixtures)
- ✅ `tests/unit/test_user_repository.py`
- ✅ `tests/unit/test_depot_repository.py`
- [ ] `app/version.py` (dedicated version module — deferred)
- [ ] DB initialization script (indexes — still open)

**Phase 2:**

- `app/models/stock_details.py`
- `app/models/bond_details.py`
- `app/models/etf_details.py`
- [plus 6 more detail models]
- `tests/unit/test_parsers.py`

**Phase 3:**

- `app/auth/__init__.py`
- `app/auth/security.py`
- `app/auth/models.py`
- `app/routers/auth.py`
- `tests/unit/test_auth.py`
- `tests/integration/test_auth_flow.py`

**Phase 4:**

- `tests/integration/test_api_flows.py`
- `tests/e2e/test_deployment.py`
- `tests/conftest.py` (enhanced fixtures)

**Phase 5:**

- `app/core/exceptions.py`
- `app/middleware/error_handler.py`
- `app/core/metrics.py`
- `loadtest/locustfile.py`

**Phase 6:**

- `docs/API_GUIDE.md`
- `docs/ARCHITECTURE.md`
- `docs/CONTRIBUTING.md`
- `docs/PARSER_PLUGIN_GUIDE.md`

---

### Phase 7: MCP Server Integration (Week 13-14)

Priority: LOW-MEDIUM - AI Assistant Enhancement

Enable AI assistants (Claude Desktop, IDEs, etc.) to interact with the financial data API through the Model Context Protocol (MCP).

**Design Decision**: This API performs active operations (web scraping, HTML parsing, real-time calculations) rather than serving static data. Therefore, MCP **Tools** are the primary interface for basedata, pricedata, and history endpoints. Resources are only used for static metadata (asset class lists, schemas) if needed.

#### 7.1 MCP Architecture Design

- [ ] Decide on integration approach
  - **Option A**: Standalone MCP server (recommended)
    - Separate Python process wrapping API calls
    - No changes to existing FastAPI code
    - Independent deployment and scaling
  - **Option B**: Integrated MCP endpoints
    - Add MCP protocol handling to FastAPI app
    - Single deployment artifact
  - **Recommendation**: Option A for separation of concerns

- [ ] Design MCP component types
  - **Tools** (Primary): Executable functions for data retrieval and computation
    - Main API operations: get_basedata(), get_pricedata(), get_history()
    - Rationale: API endpoints perform active operations (scraping, parsing, computing)
    - Not static data - each call triggers HTTP requests and transformations
  - **Resources** (Optional): Static metadata and reference data
    - Asset class lists, API schemas, supported ISINs
    - Only for data that exists at rest, not computed per request
  - **Prompts**: Pre-defined workflows for common tasks

#### 7.2 Implement MCP Tools (Primary)

Tools enable AI to perform data retrieval, computations, and analysis.

- [ ] Add MCP dependency
  - Add `mcp` SDK to pyproject.toml
  - Install development dependencies

- [ ] Create tools module
  - File: `mcp_server/tools.py`

- [ ] Implement core data retrieval tools
  - `get_basedata(isin: str)` - Fetch instrument base data
  - `get_pricedata(isin: str, venue: Optional[str])` - Fetch current prices
  - `get_history(isin: str, from_date: str, to_date: str)` - Fetch historical data
  - Each tool wraps FastAPI endpoint with parameter validation

- [ ] Implement analysis tools
  - `calculate_portfolio_performance(depot_id, start_date, end_date)`
  - `compare_instruments(instrument_ids, metrics)`
  - `search_instruments(asset_class, filters)`
  - `analyze_diversification(depot_id)`

**Example Tool Implementation:**

```python
from mcp.server import Server
import httpx

mcp = Server("financial-data-mcp")

@mcp.tool()
async def get_basedata(isin: str) -> dict:
    """
    Get base information for a financial instrument.
    Actively scrapes and parses data from comdirect.de.
    
    Args:
        isin: The ISIN identifier (e.g., 'BASF11', 'DE0005140008')
    
    Returns:
        Dictionary with instrument details, trading venues, and identifiers
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://localhost:8080/v1/basedata/{isin}",
            headers={"Authorization": f"Bearer {get_token()}"}
        )
        response.raise_for_status()
        return response.json()

@mcp.tool()
async def get_pricedata(isin: str, venue: str = None) -> dict:
    """
    Get current price data for a financial instrument.
    Actively fetches real-time pricing from comdirect.de.
    
    Args:
        isin: The ISIN identifier
        venue: Optional trading venue code (e.g., 'XETRA', 'FSE')
    
    Returns:
        Dictionary with bid, ask, spread, timestamp, and venue
    """
    params = {"venue": venue} if venue else {}
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://localhost:8080/v1/pricedata/{isin}",
            headers={"Authorization": f"Bearer {get_token()}"},
            params=params
        )
        response.raise_for_status()
        return response.json()
```

#### 7.3 Implement MCP Resources (Optional)

Resources provide static metadata and reference information.

- [ ] Create resources module
  - File: `mcp_server/resources.py`

- [ ] Implement metadata resources (optional)
  - `finance://schema/basedata` - Pydantic model as JSON schema
  - `finance://schema/pricedata` - Price data schema
  - `finance://asset-classes` - List of supported asset classes
  - Only for static reference data, not computed results

**Example Resource Implementation:**

```python
from mcp.server import Server
from mcp.types import Resource
import json

@mcp.resource("finance://asset-classes")
async def get_asset_classes(uri: str) -> Resource:
    """
    Get list of supported asset classes.
    This is static metadata, not computed per request.
    """
    asset_classes = [
        {"code": "STOCK", "name": "Stocks", "plugin": true},
        {"code": "WARRANT", "name": "Warrants", "plugin": true},
        {"code": "BOND", "name": "Bonds", "plugin": false},
        {"code": "ETF", "name": "ETFs", "plugin": false},
        {"code": "FONDS", "name": "Funds", "plugin": false},
        # ... etc
    ]
    
    return Resource(
        uri=uri,
        mimeType="application/json",
        text=json.dumps(asset_classes, indent=2)
    )
```

#### 7.4 Implement MCP Prompts

Prompts guide AI through common workflows and analysis tasks.

- [ ] Create prompts module
  - File: `mcp_server/prompts.py`

- [ ] Define workflow prompts
  - **"Portfolio Analysis"**
    - Guide through depot selection
    - Fetch all instruments and prices
    - Calculate key metrics
    - Generate narrative report
  
  - **"Instrument Comparison"**
    - Select instruments to compare
    - Choose comparison dimensions
    - Generate side-by-side analysis
  
  - **"Risk Assessment"**
    - Analyze portfolio risk characteristics
    - Identify high-risk positions
    - Suggest diversification improvements
  
  - **"Market Overview"**
    - Get current market data for a list of instruments
    - Show price movements and trends
    - Highlight significant changes
  
  - **"Depot Performance Report"**
    - Complete performance analysis
    - Historical trends
    - Individual position performance

**Example Prompt Implementation:**

```python
@mcp.prompt()
async def portfolio_analysis_prompt() -> str:
    """
    Interactive workflow for comprehensive portfolio analysis.
    Guides the user through analyzing their depot performance.
    """
    return """
# Portfolio Analysis Workflow

Let me help you analyze your portfolio performance. I'll guide you through several steps:

1. **Select Depot**: Which depot would you like to analyze?
   - Use: search_instruments or list available depots

2. **Time Period**: What time period should we analyze?
   - Suggested: Last month, quarter, year, or custom range

3. **Fetch Data**: I'll gather:
   - All instruments in the depot
   - Current prices and values
   - Historical performance data

4. **Calculate Metrics**:
   - Total return and performance
   - Asset allocation breakdown
   - Risk metrics (volatility, drawdown)
   - Individual position performance

5. **Generate Report**: I'll provide:
   - Summary of key findings
   - Performance attribution
   - Risk assessment
   - Recommendations (if requested)

What depot would you like to start with?
"""
```

#### 7.5 MCP Server Configuration

- [ ] Create server entry point
  - File: `mcp_server/server.py`
  - Initialize MCP server
  - Register tools (required), prompts (recommended), resources (optional)
  - Configure authentication
  - Set up logging

- [ ] Add configuration management
  - File: `mcp_server/config.py`
  - API endpoint URL (configurable for dev/prod)
  - Authentication credentials
  - Cache settings
  - Rate limiting

- [ ] Create MCP server startup script
  - File: `run_mcp_server.py`
  - Command-line interface
  - Support for different transports (stdio, HTTP)

**Example Server Setup:**

```python
# mcp_server/server.py
from mcp.server import Server
from mcp.server.stdio import stdio_server
from .resources import register_resources
from .tools import register_tools
from .prompts import register_prompts

def create_mcp_server() -> Server:
    """Create and configure the MCP server"""
    server = Server("finhub-mcp")
    
    # Register components (prioritize tools for data access)
    register_tools(server)  # Primary: data retrieval and analysis
    register_prompts(server)  # Guided workflows
    register_resources(server)  # Optional: metadata only
    
    return server

async def main():
    """Run the MCP server"""
    server = create_mcp_server()
    
    # Run with stdio transport (for Claude Desktop, IDEs)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

#### 7.6 Testing

- [ ] Unit tests for MCP components
  - File: `tests/mcp/test_tools.py` (priority)
    - Test each tool independently
    - Validate input parameters and output schemas
    - Test error handling and edge cases
    - Mock API responses
  
  - File: `tests/mcp/test_resources.py` (optional)
    - Test resource URI parsing if implemented
    - Test metadata retrieval

- [ ] Integration tests
  - Test MCP server with actual FastAPI
  - End-to-end tool invocations
  - Resource browsing workflows

- [ ] Manual testing with Claude Desktop
  - Configure MCP server in Claude config
  - Test common workflows
  - Verify prompt interactions

#### 7.7 Documentation

- [ ] Create MCP setup guide
  - File: `docs/MCP_INTEGRATION.md`
  - Installation instructions
  - Configuration for Claude Desktop
  - Configuration for IDEs (VS Code, Cursor)
  - Available resources, tools, and prompts

- [ ] Update README.md
  - Add MCP capabilities section
  - Quick start for AI assistant integration
  - Use case examples

- [ ] Create MCP architecture diagram
  - Show MCP server → FastAPI relationship
  - Data flow for resources and tools
  - Authentication flow

- [ ] Document example interactions
  - Sample prompts and AI responses
  - Showcase portfolio analysis workflow
  - Instrument comparison examples

**Deliverables:**

- Standalone MCP server wrapping FastAPI
- Resources for all major data endpoints
- Tools for financial analysis and computation
- Prompts for common workflows
- Complete test coverage
- Integration documentation
- Claude Desktop configuration example

**Success Metrics:**

- MCP server connects successfully to FastAPI
- All resources browsable from AI assistant
- Tools execute complex analyses correctly
- Prompts guide users through workflows
- Documentation enables easy setup
- <15 minutes to configure for new users

**Use Case Examples:**

1. **Portfolio Health Check**

   ```text
   User: "How is my mega-trend depot performing?"
   AI: [Uses get_depot → fetch instruments → calculate_performance]
       "Your mega-trend depot has returned 12.3% YTD..."
   ```

2. **Instrument Research**

   ```text
   User: "Tell me about BASF11"
   AI: [Uses get_instrument_details resource]
       "BASF11 is a warrant with strike price..."
   ```

3. **Comparative Analysis**

   ```text
   User: "Compare performance of my warrants"
   AI: [Uses compare_instruments tool]
       "Here's a comparison of your 7 warrants..."
   ```

**Files to Create:**

- `mcp_server/__init__.py`
- `mcp_server/server.py`
- `mcp_server/config.py`
- `mcp_server/resources.py`
- `mcp_server/tools.py`
- `mcp_server/prompts.py`
- `mcp_server/utils.py` (parsing, authentication helpers)
- `run_mcp_server.py` (entry point)
- `tests/mcp/test_resources.py`
- `tests/mcp/test_tools.py`
- `tests/mcp/test_integration.py`
- `docs/MCP_INTEGRATION.md`
- `.claude_desktop_config.json` (example configuration)

---

*This plan is a living document and should be updated as requirements evolve or priorities change.*
