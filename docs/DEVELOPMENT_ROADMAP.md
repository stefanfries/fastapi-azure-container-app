# Development Roadmap: FinHub API

## Executive Summary

Based on a comprehensive review of the codebase against business and technical requirements, this plan outlines a phased approach to complete the application. **FinHub API** is a financial data aggregator using web scraping to provide unified, structured access to financial instruments data. The project has a solid foundation (CI/CD, basic API structure, plugin system), but critical gaps exist in database integration, authentication, testing, and parser completeness.

---

## Current State Assessment

### ✅ Completed Components

- FastAPI application structure with routers (welcome, users, basedata, depots, pricedata, history)
- Plugin-based parser system architecture (factory pattern)
- Parsers for STOCK and WARRANT asset classes
- Web scraping infrastructure (httpx + BeautifulSoup)
- Basic data models (BaseData, User, Depot, History, PriceData)
- CRUD operations for users, depots, and instruments
- Docker containerization
- CI/CD pipeline with GitHub Actions (quality checks + Azure deployment)
- Basic logging configuration
- ID notation system for trading venues

### ⚠️ Partially Completed

- **Plugin System**: Only 2 of 9 asset classes have parsers (STOCK, WARRANT)
- **Data Models**: BaseData only contains common attributes, no asset-class-specific fields
- **Testing**: Only 3 basic tests (test_main.py, test_users.py, test_welcome.py)
- **Logging**: Configuration exists but print() statements still used in code
- **Error Handling**: Basic middleware exists, needs enhancement
- **API Documentation**: Auto-generated OpenAPI only, no detailed endpoint docs

### ❌ Missing Components

- **MongoDB Integration**: No database driver or connection code (despite technical requirements)
- **Authentication/Authorization**: No implementation (routes unprotected)
- **Data Persistence**: No repository layer for basedata/pricedata caching
- **Asset-Class-Specific Models**: Missing extended models for each asset class
- **Parsers for Special Asset Classes**: INDEX, COMMODITY, CURRENCY not implemented
- **Integration Tests**: No tests for parsers, scrapers, or end-to-end flows
- **Load Testing**: No performance or scalability verification
- **User Role Model**: No RBAC or role definitions
- **API Versioning**: No route versioning (e.g., /v1/, /v2/) implemented
- **Software Release Versioning**: No semantic versioning or version endpoint

---

## Prioritized Development Plan

### Phase 1: Foundation & Code Quality (Week 1-2)

**Priority: HIGH - Required for reliable development**

#### 1.1 Clean Up Technical Debt

- [ ] Replace all `print()` statements with `logger` calls
  - Files affected: `app/scrapers/scrape_url.py`, `app/parsers/history.py`, `app/parsers/pricedata.py`
  - Quality impact: Consistent logging across application
  
- [ ] Remove legacy backward compatibility code (if any identified)
  - Review parser plugins for deprecated patterns
  
- [ ] Add comprehensive logging to all modules
  - Ensure all functions log entry/exit for debugging
  - Log errors with full context

#### 1.2 Database Integration

- [ ] Add MongoDB dependencies
  - Add `motor` (async MongoDB driver) or `pymongo` to pyproject.toml
  - Add connection pool configuration
  
- [ ] Create database configuration module
  - Connection string management (via environment variables)
  - Database and collection definitions
  - Connection lifecycle management
  
- [ ] Implement repository pattern
  - Create `app/repositories/` directory
  - BaseData repository (CRUD + caching logic)
  - User repository (migrate from in-memory to DB)
  - Depot repository
  - Instrument repository
  
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
  - Add version prefix to all routes (e.g., `/v1/basedata`, `/v1/pricedata`)
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
  - Apply authentication to basedata, pricedata, history routes
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
  
- [ ] Update BaseData model
  - Add optional `details` field (Union of all specific models)
  - Ensure backward compatibility
  
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

- [ ] Enhance `/basedata/{instrument_id}` response
  - Include asset-class-specific details in response
  - Update response model to include details union type
  
- [ ] Add asset class filtering
  - GET `/basedata?asset_class={asset_class}`
  
- [ ] Add bulk operations (if needed)
  - POST `/basedata/bulk` for multiple instruments

**Deliverables:**

- All 9 asset classes supported
- Asset-class-specific data models
- Complete parser plugin system
- Updated API with extended data

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
  - User registration → login → fetch basedata
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

- [ ] Implement basedata caching
  - Cache parsed basedata in MongoDB
  - TTL-based cache invalidation
  - Cache hit/miss logging
  
- [ ] Implement pricedata caching
  - Short-lived cache (5-15 minutes)
  - Update strategy for real-time data

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
  - High-volume basedata requests
  
- [ ] Run load tests
  - Use `locust` or `k6`
  - Identify bottlenecks
  
- [ ] Establish performance baselines
  - Target: p95 latency < 500ms
  - Target: Handle 100+ concurrent requests

**Deliverables:**

- Robust error handling
- Application monitoring
- Performance benchmarks
- Load test results

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
  - Document version in URL path (`/v1/basedata`)
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

### Phase 4 (Testing)

- 80%+ code coverage
- 100+ tests passing
- CI pipeline includes all tests

### Phase 5 (Performance)

- p95 latency < 500ms
- Handles 100+ concurrent users
- Comprehensive error handling

### Phase 6 (Documentation)

- Complete API documentation
- Architecture diagrams
- Developer onboarding guide

### Phase 7 (MCP Server)

- MCP server successfully wraps all FastAPI endpoints
- Resources, tools, and prompts all functional
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
├── models/            # Data models (basedata, users, depots, history, pricedata)
├── parsers/           # Parsing logic
│   └── plugins/       # Parser plugin system (stock, warrant)
├── routers/           # API routes (basedata, users, depots, pricedata, history, welcome)
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

- `app/config/database.py`
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
  - **Resources**: Browsable data sources (instruments, depots, price data)
  - **Tools**: Executable functions for analysis/computation
  - **Prompts**: Pre-defined workflows for common tasks

#### 7.2 Implement MCP Resources

Resources expose browsable, hierarchical data for AI to discover and read.

- [ ] Add MCP dependency
  - Add `mcp` SDK to pyproject.toml
  - Install development dependencies

- [ ] Create resource structure
  - File: `mcp_server/resources.py`
  - Implement resource URI scheme:
    - `mcp://instruments/{instrument_id}/basedata`
    - `mcp://instruments/{instrument_id}/pricedata`
    - `mcp://instruments/{instrument_id}/history`
    - `mcp://depots/{depot_id}/instruments`
    - `mcp://depots/{depot_id}/performance`

- [ ] Implement resource handlers
  - Each resource fetches data from FastAPI endpoints
  - Use httpx for async HTTP calls
  - Handle authentication/authorization
  - Cache responses appropriately

- [ ] Add resource discovery
  - List available instruments by asset class
  - List available depots for authenticated user
  - Generate resource templates

**Example Resource Implementation:**

```python
from mcp.server import Server
from mcp.types import Resource
import httpx

mcp = Server("financial-data-mcp")

@mcp.resource("instruments/{instrument_id}/basedata")
async def get_instrument_basedata(uri: str) -> Resource:
    """Get base information for a financial instrument"""
    instrument_id = extract_id_from_uri(uri)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://localhost:8080/v1/basedata/{instrument_id}",
            headers={"Authorization": f"Bearer {get_token()}"}
        )
        data = response.json()
    
    return Resource(
        uri=uri,
        mimeType="application/json",
        text=json.dumps(data, indent=2)
    )
```

#### 7.3 Implement MCP Tools

Tools enable AI to perform computations, analysis, and complex queries.

- [ ] Create tools module
  - File: `mcp_server/tools.py`
  
- [ ] Implement analysis tools
  - `calculate_portfolio_performance(depot_id, start_date, end_date)`
    - Fetch depot instruments
    - Get historical data for each
    - Calculate returns, volatility
    - Return aggregated metrics
  
  - `compare_instruments(instrument_ids, metrics)`
    - Fetch basedata and pricedata for each
    - Compare specified metrics (price, performance, risk)
    - Return comparison table
  
  - `search_instruments(asset_class, filters)`
    - Search instruments by criteria
    - Return matching instruments with key data
  
  - `analyze_diversification(depot_id)`
    - Analyze asset allocation
    - Calculate diversification metrics
    - Identify concentration risks
  
  - `get_instrument_details(instrument_id)`
    - Comprehensive instrument lookup
    - Combine basedata, pricedata, history
    - Return unified view

**Example Tool Implementation:**

```python
@mcp.tool()
async def calculate_portfolio_performance(
    depot_id: str,
    start_date: str,
    end_date: str
) -> dict:
    """
    Calculate portfolio performance metrics for a depot over a time period.
    
    Args:
        depot_id: The depot identifier
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    
    Returns:
        Dictionary with performance metrics (total_return, volatility, sharpe_ratio)
    """
    # Fetch depot instruments
    instruments = await fetch_depot_instruments(depot_id)
    
    # Get historical data for each
    histories = await asyncio.gather(*[
        fetch_instrument_history(i, start_date, end_date)
        for i in instruments
    ])
    
    # Calculate metrics
    returns = calculate_returns(histories)
    volatility = calculate_volatility(returns)
    sharpe = calculate_sharpe_ratio(returns, volatility)
    
    return {
        "depot_id": depot_id,
        "period": f"{start_date} to {end_date}",
        "total_return": returns,
        "volatility": volatility,
        "sharpe_ratio": sharpe,
        "instruments_count": len(instruments)
    }
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
  - Register all resources, tools, and prompts
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
    
    # Register components
    register_resources(server)
    register_tools(server)
    register_prompts(server)
    
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
  - File: `tests/mcp/test_resources.py`
  - Test resource URI parsing
  - Test resource data retrieval
  - Mock API responses

- [ ] Tool function tests
  - File: `tests/mcp/test_tools.py`
  - Test each tool independently
  - Validate output schemas
  - Test error handling

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
