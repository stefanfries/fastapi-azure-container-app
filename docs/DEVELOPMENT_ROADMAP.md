# Development Roadmap: FinHub API

## Executive Summary

Based on a comprehensive review of the codebase against business and technical requirements, this plan outlines a phased approach to complete the application. **FinHub API** is a financial data aggregator using web scraping to provide unified, structured access to financial instruments data. The project has a solid foundation (CI/CD, basic API structure, plugin system), but critical gaps exist in database integration, authentication, testing, and parser completeness.

---

## Current State Assessment

### ✅ Completed Components

- FastAPI application structure with routers (welcome, users, instruments, depots, quotes, history)
- Plugin-based parser system architecture (factory pattern)
- Parsers for STOCK and WARRANT asset classes
- Web scraping infrastructure (httpx + BeautifulSoup)
- Basic data models (Instrument, User, Depot, History, Quote)
- CRUD operations for users, depots, and instruments
- Docker containerization
- CI/CD pipeline with GitHub Actions (quality checks + Azure deployment)
- Basic logging configuration
- ID notation system for trading venues

### ⚠️ Partially Completed

- **Plugin System**: Only 2 of 9 asset classes have parsers (STOCK, WARRANT)
- **Data Models**: Instrument model only contains common attributes, no asset-class-specific fields
- **Testing**: Only 3 basic tests (test_main.py, test_users.py, test_welcome.py)
- **Logging**: Configuration exists but print() statements still used in code
- **Error Handling**: Basic middleware exists, needs enhancement
- **API Documentation**: Auto-generated OpenAPI only, no detailed endpoint docs

### ❌ Missing Components

- **MongoDB Integration**: No database driver or connection code (despite technical requirements)
- **Authentication/Authorization**: No implementation (routes unprotected)
- **Data Persistence**: No repository layer for instruments/quotes caching
- **Asset-Class-Specific Models**: Missing extended models for each asset class
- **Parsers for Special Asset Classes**: INDEX, COMMODITY, CURRENCY not implemented
- **Integration Tests**: No tests for parsers, scrapers, or end-to-end flows
- **Load Testing**: No performance or scalability verification
- **User Role Model**: No RBAC or role definitions
- **API Versioning**: No route versioning (e.g., /v1/, /v2/) implemented
- **Software Release Versioning**: No semantic versioning or version endpoint
- **API Terminology**: Current endpoints use technical names (basedata, pricedata) instead of financial domain terms (instruments, quotes)

---

## Prioritized Development Plan

### Phase 0: API Terminology Refactoring (Week 0 - Before Starting Phase 1)

**Priority: CRITICAL - Foundation for all future development**

**Rationale**: The current API uses technical implementation names (`basedata`, `pricedata`) instead of standard financial industry terminology. Refactoring now prevents technical debt accumulation and ensures the API speaks the financial domain language correctly.

#### 0.1 Financial Domain Terminology

**Industry Standard Terms:**
- **Instrument** = Any tradeable financial asset (stocks, bonds, ETFs, warrants, commodities, currencies, indices)
- **Quote** = Current market price data (bid/ask prices, timestamp, volume)
- **History/OHLC** = Historical price data (Open, High, Low, Close, Volume over time)

**Why NOT "Equity"?** Equity only refers to stocks/shares. Since this API supports 9 asset classes, "instrument" is the correct, broader term.

**Industry References:**
- Bloomberg API: `/instruments`, `/quotes`, `/historical-data`
- Alpha Vantage: `/quote`, `/time-series`
- IEX Cloud: `/stock`, `/quote`, `/chart`

#### 0.2 Refactoring Plan

**Target API Structure:**
```
/                                    # Application info (existing /welcome)
/health                              # Liveness probe
/health/ready                        # Readiness probe
/docs                                # OpenAPI documentation

/v1/instruments/{wkn}                # Instrument master data (was /basedata/{wkn})
/v1/instruments/{wkn}/quote          # Current quote (was /pricedata/{wkn})
/v1/instruments/{wkn}/history        # Historical OHLC (was /history/{wkn})
/v1/instruments?asset_class=STOCK    # Filter instruments

/v1/auth/register                    # User registration
/v1/auth/login                       # User login
/v1/auth/me                          # Current user

/v1/depots                           # User portfolios (existing)
/v1/depots/{depot_id}                # Depot details
```

#### 0.3 File Renaming Checklist

- [ ] **Models**
  - Rename `app/models/basedata.py` → `app/models/instruments.py`
  - Rename class `BaseData` → `Instrument` within the file
  - Rename `app/models/pricedata.py` → `app/models/quotes.py`
  - Rename class `PriceData` → `Quote` within the file
  - Update all imports across the codebase

- [ ] **Parsers**
  - Rename `app/parsers/basedata.py` → `app/parsers/instruments.py`
  - Rename function `parse_base_data()` → `parse_instrument_data()`
  - Rename `app/parsers/pricedata.py` → `app/parsers/quotes.py`
  - Rename function `parse_price_data()` → `parse_quote()`
  - Update all parser plugin references

- [ ] **Routers**
  - Rename `app/routers/basedata.py` → `app/routers/instruments.py`
  - Update router prefix: `@router = APIRouter(prefix="/v1/instruments")`
  - Rename `app/routers/pricedata.py` → `app/routers/quotes.py`
  - Update router prefix: `@router = APIRouter(prefix="/v1/quotes")`
  - Alternative: Keep quotes nested under instruments (`/v1/instruments/{wkn}/quote`)
  - Update `app/routers/welcome.py` → integrate into root `/` endpoint
  - Update `app/routers/history.py` to nest under instruments if desired

- [ ] **CRUD Operations**
  - Rename `app/crud/instruments.py` (currently empty, will handle instrument CRUD)
  - Update function names: any references to "basedata" → "instrument"
  - Update function names: any references to "pricedata" → "quote"

- [ ] **Update main.py**
  - Update router includes with new import paths
  - Update API version tags in OpenAPI metadata

- [ ] **Update Tests**
  - Rename test files to match new naming
  - Update import statements
  - Update API endpoint paths in integration tests

- [ ] **Update Documentation**
  - Update all `.md` files in `docs/` with new terminology
  - Update code comments with correct terminology
  - Update OpenAPI descriptions

#### 0.4 Migration Strategy

**Option A: Big Bang Refactoring (Recommended)**

- Complete all renaming in one PR
- Ensures consistency immediately
- Easier to track changes
- Minimizes confusion
- **Estimated time: 2-4 hours**

**Option B: Gradual Migration**

- Support both old and new endpoints temporarily
- Add deprecation warnings to old endpoints
- Migrate over multiple PRs
- More complex, higher maintenance burden
- **Not recommended** for this stage (no production users yet)

#### 0.5 Validation Checklist

After refactoring, verify:

- [ ] All tests pass
- [ ] No broken imports
- [ ] OpenAPI docs reflect new endpoint names
- [ ] Docker build succeeds
- [ ] All endpoints accessible at new paths
- [ ] No references to old terminology in code or docs

**Deliverables:**

- Codebase uses financial domain terminology throughout
- API endpoints follow industry standards
- Models, parsers, and routers renamed consistently
- Documentation updated
- All tests passing
- Clean foundation for Phase 1 work

---

### Phase 1: Foundation & Code Quality (Week 1-2)

**Priority: HIGH - Required for reliable development**

#### 1.1 Clean Up Technical Debt

- [ ] Replace all `print()` statements with `logger` calls
  - Files affected: `app/scrapers/scrape_url.py`, `app/parsers/history.py`, `app/parsers/quotes.py`
  - Quality impact: Consistent logging across application
  
- [ ] Remove legacy backward compatibility code (if any identified)
  - Review parser plugins for deprecated patterns
  
- [ ] Add comprehensive logging to all modules
  - Ensure all functions log entry/exit for debugging
  - Log errors with full context

#### 1.2 Database Integration

- [ ] Add MongoDB dependencies
  - Add `pymongo>=4.6.0` to pyproject.toml (native async support)
  - **Note**: PyMongo 4.x+ has native async/await support - Motor is no longer needed
  - MongoDB officially recommends PyMongo for new projects
  - Add connection pool configuration
  
- [ ] Create database configuration module
  - Connection string management (via environment variables)
  - Database and collection definitions
  - Connection lifecycle management
  
**Example PyMongo 4.x Async Usage:**

```python
# app/config/database.py
from pymongo import AsyncMongoClient
from typing import AsyncGenerator

DATABASE_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "finance_db")

client: AsyncMongoClient | None = None

async def get_database():
    """Get database instance"""
    global client
    if client is None:
        client = AsyncMongoClient(DATABASE_URL)
    return client[DATABASE_NAME]

async def close_database():
    """Close database connection"""
    global client
    if client:
        client.close()

# Usage in repository
async def get_user(user_id: str):
    db = await get_database()
    user = await db.users.find_one({"_id": user_id})
    return user
```
  
- [ ] Implement repository pattern
  - Create `app/repositories/` directory
  - **InstrumentRepository** (CRUD + caching logic for financial instruments)
    - Handles instrument master data (WKN, ISIN, name, asset class, id_notations)
    - Manages asset-class-specific extended data (StockDetails, WarrantDetails, etc.)
    - Caching strategy for instrument data
  - **UserRepository** (migrate from in-memory to DB)
  - **DepotRepository** (user portfolios management)
  - **QuoteRepository** (optional - for quote caching if needed)
  
- [ ] Add database initialization script
  - Schema validation setup
  - Index creation for performance
  - Seed data for testing

#### 1.3 Testing Foundation

- [ ] Set up comprehensive test structure
  - Create `tests/unit/`, `tests/integration/`, `tests/e2e/` directories
  - Add pytest fixtures for database mocking
  - Add test data fixtures
  
- [ ] Add pytest plugins
  - `pytest-asyncio` for async tests
  - `pytest-mock` for mocking
  - `pytest-env` for environment management
  
- [ ] Establish test coverage targets
  - Minimum 80% coverage for new code
  - Configure coverage reporting in CI

#### 1.4 API & Software Versioning

- [ ] Implement API route versioning
  - Add version prefix to all routes (e.g., `/v1/instruments`, `/v1/quotes`)
  - Create API version router structure in `app/api/v1/`
  - Migrate existing routers to versioned structure
  - Keep root `/` and `/docs` endpoints unversioned
  
- [ ] Add software release versioning
  - Implement semantic versioning (MAJOR.MINOR.PATCH)
  - Create `app/__version__.py` or `app/version.py` module
  - Define version constant (e.g., `__version__ = "1.0.0"`)
  - Version increments:
    - MAJOR: Breaking API changes
    - MINOR: New features, backward compatible
    - PATCH: Bug fixes, backward compatible
  
- [ ] Implement root welcome endpoint (`/`)
  - Rename/migrate `/welcome` to root `/` endpoint
  - Return application info and version details
  - Response structure:
    ```json
    {
      "application": "FinHub API",
      "description": "Financial data aggregator using web scraping",
      "version": "1.0.0",
      "api_version": "v1",
      "data_sources": ["comdirect"],
      "method": "web_scraping",
      "docs": "/docs",
      "timestamp": "2026-02-15T10:30:00Z"
    }
    ```
  - Always returns 200 OK
  - Quick reference for developers
  - Shows transparency about scraping methodology

- [ ] Implement liveness health endpoint (`/health`)
  - Fast health check without dependency validation
  - Used by Azure Container Apps liveness probe
  - Response structure:
    ```json
    {
      "status": "healthy",
      "timestamp": "2026-02-15T10:30:00Z"
    }
    ```
  - Returns 200 if application is running
  - Returns 503 if application cannot serve requests
  - Should respond in < 100ms

- [ ] Implement readiness health endpoint (`/health/ready`)
  - Comprehensive health check with dependency validation
  - Used by Azure Container Apps readiness probe
  - Checks database connection, external service availability
  - Response structure:

    ```json
    {
      "status": "ready",
      "version": "1.0.0",
      "checks": {
        "database": "healthy",
        "comdirect_access": "healthy"
      },
      "timestamp": "2026-02-15T10:30:00Z"
    }
    ```

  - Returns 200 if all services are operational
  - Returns 503 if any critical dependency is unavailable
  - Returns detailed check results for debugging
  - Should respond in < 1000ms
  
- [ ] Update deployment pipeline
  - Auto-increment version on releases
  - Tag Docker images with version numbers
  - Add version to CI/CD workflow outputs
  
- [ ] Add version to logs and error responses
  - Include version in structured logs
  - Add `X-API-Version` header to all responses

**Deliverables:**

- All print() statements removed
- MongoDB connected and configured
- Repository layer implemented
- Test infrastructure ready
- API route versioning implemented (all routes under /v1/)
- Software version tracking in place
- Root endpoint (`/`) returns comprehensive application and version info
- Health endpoints (`/health` and `/health/ready`) implemented
- Azure Container Apps health probes configured

---

### Phase 2: Security & Authentication (Week 3-4)

**Priority: HIGH - Required before production**

#### 2.1 Authentication Design Decision

- [ ] Choose authentication approach
  - **Option A**: FastAPI built-in security (OAuth2 + JWT)
  - **Option B**: Auth0 integration
  - **Recommendation**: Start with FastAPI OAuth2 for simplicity, migrate to Auth0 if needed
  
#### 2.2 Implement Authentication

- [ ] Add security dependencies
  - `python-jose[cryptography]` for JWT
  - `passlib[bcrypt]` for password hashing
  - `python-multipart` for form data
  
- [ ] Create authentication module
  - `app/auth/` directory
  - Password hashing utilities
  - JWT token generation/validation
  - User authentication logic
  
- [ ] Implement user registration/login endpoints
  - POST `/auth/register`
  - POST `/auth/login` (returns JWT)
  - GET `/auth/me` (current user info)
  
- [ ] Add authentication middleware
  - JWT validation on protected routes
  - User context injection into requests

#### 2.3 Authorization & Roles

- [ ] Define user role model
  - Roles: `admin`, `user`, `readonly`
  - Store roles in User model
  
- [ ] Implement role-based access control (RBAC)
  - Create permission decorators
  - Protect routes based on roles
  
- [ ] Document security model
  - Authentication flow diagrams
  - Role permission matrix

#### 2.4 Secure Existing Routes

- [ ] Protect all API endpoints
  - Apply authentication to instruments, quotes, history routes
  - Public: `/`, `/docs`, `/auth/login`, `/auth/register`
  - Protected: All other endpoints
  
- [ ] Add rate limiting (optional but recommended)
  - Use `slowapi` library
  - Limit requests per user/IP

**Deliverables:**

- Working JWT-based authentication
- User registration and login
- All routes protected appropriately
- Role-based access control

---

### Phase 3: Complete Asset Class Support (Week 5-7)

**Priority: HIGH - Core business requirement**

#### 3.1 Extend Data Models

- [ ] Create asset-class-specific model extensions
  - `StockDetails` model with fields:
    - Market cap, sector, industry, dividend yield, P/E ratio, etc.
  - `BondDetails` model:
    - Coupon rate, maturity date, credit rating, issuer, etc.
  - `ETFDetails` model:
    - Expense ratio, tracking index, AUM, distribution policy, etc.
  - `FondsDetails` model:
    - Fund type, manager, inception date, NAV, etc.
  - `WarrantDetails` model (extend existing):
    - Strike price, expiry, underlying, warrant type (call/put)
  - `CertificateDetails` model:
    - Certificate type, participation rate, cap, floor
  - `IndexDetails` model:
    - Constituent count, weighting method, base value
  - `CommodityDetails` model:
    - Commodity type, unit, contract specs
  - `CurrencyDetails` model:
    - Currency pair, exchange rate source
  
- [ ] Update Instrument model
  - Add optional `details` field (Union of all specific models)
  - Ensure backward compatibility
  - Note: Currently named `BaseData`, will be renamed to `Instrument` in refactoring phase
  
- [ ] Update database schemas
  - Ensure MongoDB can store extended models

#### 3.2 Implement Missing Parsers

- [ ] Create INDEX parser
  - File: `app/parsers/plugins/index_parser.py`
  - Extract index-specific data from comdirect
  - Register in factory
  
- [ ] Create COMMODITY parser
  - File: `app/parsers/plugins/commodity_parser.py`
  - Extract commodity-specific data
  - Register in factory
  
- [ ] Create CURRENCY parser
  - File: `app/parsers/plugins/currency_parser.py`
  - Extract currency pair data
  - Register in factory
  
- [ ] Extend existing parsers
  - Update StockParser to extract StockDetails
  - Update WarrantParser to extract WarrantDetails
  - Add parsers for BOND, ETF, FONDS, CERTIFICATE
  
- [ ] Test all parsers with sample data
  - Use test data from BUSINESS_REQUIREMENTS.md:
    - test_warrants, test_indizes, test_bonds, test_etfs, test_commodities, test_currencies

#### 3.3 Update API Endpoints

- [ ] Enhance `/v1/instruments/{wkn}` response
  - Include asset-class-specific details in response
  - Update response model to include details union type
  
- [ ] Add asset class filtering
  - GET `/v1/instruments?asset_class={asset_class}`
  
- [ ] Add bulk operations (if needed)
  - POST `/v1/instruments/bulk` for multiple instruments

#### 3.4 Remove Legacy Parsing Code

Once all 9 asset classes have been migrated to the plugin system, remove the legacy parsing infrastructure to simplify the codebase.

- [ ] Remove legacy parsing functions from `app/parsers/instruments.py` (currently `basedata.py`)
  - Delete `parse_name()` function (legacy)
  - Delete `parse_wkn()` function (legacy)
  - Delete `parse_isin()` function (legacy)
  - Delete `parse_id_notations()` function (legacy)
  - Delete `parse_preferred_notation_id_life_trading()` function
  - Delete `parse_preferred_notation_id_exchange_trading()` function
  - Delete `_parse_base_data_legacy()` function
  - Remove legacy fallback logic from `parse_instrument_data()` function

- [ ] Remove legacy constants from `app/core/constants.py`
  - Delete `standard_asset_classes` list
  - Delete `special_asset_classes` list
  - Update `asset_classes` to use `AssetClass` enum directly

- [ ] Update imports in dependent modules
  - Remove legacy function imports from `app/parsers/quotes.py` (currently `pricedata.py`)
  - Update any other modules importing legacy functions

- [ ] Verify all asset classes work with plugin system
  - Test each asset class with real instruments
  - Confirm no regressions compared to legacy behavior
  - Validate all fields are correctly extracted

- [ ] Update documentation
  - Remove references to legacy parsing in comments
  - Update PLUGIN_SYSTEM_DOCUMENTATION.md if needed
  - Add migration notes to DEVELOPMENT_ROADMAP.md

**Benefits of removing legacy code:**

- Simplified codebase (removes ~200+ lines of duplicate logic)
- Single source of truth for parsing (plugin system only)
- Easier to maintain and extend
- Consistent behavior across all asset classes
- No confusion about which parsing path is used

**Deliverables:**

- All 9 asset classes supported
- Asset-class-specific data models
- Complete parser plugin system
- Updated API with extended data
- Legacy parsing code completely removed
- Cleaner, more maintainable codebase

---

### Phase 4: Comprehensive Testing (Week 8-9)

**Priority: MEDIUM-HIGH - Ensure reliability**

#### 4.1 Unit Tests

- [ ] Test all parser plugins
  - Mock HTTP responses
  - Test each asset class parser independently
  - Edge cases: missing fields, malformed HTML
  
- [ ] Test all CRUD operations
  - Repository layer tests
  - Mock database interactions
  
- [ ] Test authentication/authorization
  - Token generation/validation
  - Role permission checks
  
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

**Priority: MEDIUM - Optimize for production**

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

**Priority: MEDIUM - Improve developer experience**

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

- Zero print() statements in code
- MongoDB connection established
- Repository pattern implemented for all entities
- Test infrastructure ready
- API route versioning implemented (all routes under /v1/)
- Software release versioning in place
- Root endpoint (`/`) returns comprehensive version and application info
- Health endpoints (`/health` and `/health/ready`) implemented and tested
- Azure Container Apps health probes configured

### Phase 2 (Security)

- All routes protected with authentication
- JWT-based login/registration working
- Role-based access control implemented

### Phase 3 (Asset Classes)

- All 9 asset classes parseable
- Asset-class-specific data models created
- Parser plugin system complete
- Legacy parsing code removed
- Single parsing architecture (plugin system only)

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

1. **Review and approve** this plan
2. **Prioritize phases** based on business urgency
3. **Assign resources** if working in a team
4. **Start Phase 1** with foundation and code quality improvements

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
├── core/              # Constants, configuration
├── crud/              # CRUD operations (users, depots, instruments)
├── models/            # Data models (instruments, users, depots, history, quotes)
├── parsers/           # Parsing logic
│   └── plugins/       # Parser plugin system (stock, warrant)
├── routers/           # API routes (instruments, users, depots, quotes, history, welcome)
├── scrapers/          # Web scraping utilities
├── static/            # Static files
├── logging_config.py  # Logging setup
├── main.py            # Application entry point
└── middleware.py      # Request middleware

tests/
├── test_main.py       # Basic app tests
├── test_users.py      # User endpoint tests
└── test_welcome.py    # Welcome endpoint tests

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

**Phase 1:**

- `app/config/database.py` (use `pymongo.AsyncMongoClient` for async operations)
- `app/repositories/base.py`
- `app/repositories/basedata_repository.py`
- `app/repositories/user_repository.py`
- `app/__version__.py` or `app/version.py`
- `app/api/v1/__init__.py`
- `app/api/v1/routers/` (move existing routers here)
- `app/routers/health.py` (health and readiness endpoints)
- Update `app/routers/welcome.py` to root `/` endpoint
- `tests/unit/test_repositories.py`
- `tests/unit/test_versioning.py`
- `tests/unit/test_health.py`
- `tests/fixtures/test_data.py`

**Phase 2:**

- `app/auth/__init__.py`
- `app/auth/security.py`
- `app/auth/models.py`
- `app/routers/auth.py`
- `tests/unit/test_auth.py`
- `tests/integration/test_auth_flow.py`

**Phase 3:**

- `app/models/stock_details.py`
- `app/models/bond_details.py`
- `app/models/etf_details.py`
- [plus 6 more detail models]
- `app/parsers/plugins/index_parser.py`
- `app/parsers/plugins/commodity_parser.py`
- `app/parsers/plugins/currency_parser.py`
- [plus parsers for bond, etf, fonds, certificate]
- `tests/unit/test_parsers.py`

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

**Priority: LOW-MEDIUM - AI Assistant Enhancement**

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
