# Makefile for local development
# Docker build/push/deploy is handled by GitHub Actions CI/CD

.PHONY: help install format lint test check run-local clean all

# Define variables
APP_DIR = app
TEST_DIR = tests

help: ## Show this help message
	@echo Available commands:
	@echo   install     Install Python dependencies
	@echo   format      Format code with ruff (auto-fix)
	@echo   lint        Run ruff linter
	@echo   test        Run tests with coverage
	@echo   check       Run lint, tests, and ruff format check
	@echo   run-local   Run FastAPI app locally
	@echo   clean       Remove Python cache files
	@echo   all         Install dependencies and run all checks

install: ## Install Python dependencies
	uv sync

format: ## Format code with ruff (auto-fix)
	uv run ruff format $(APP_DIR) $(TEST_DIR)
	uv run ruff check --fix $(APP_DIR) $(TEST_DIR)

lint: ## Run ruff linter
	uv run ruff check $(APP_DIR) $(TEST_DIR)

test: ## Run tests with coverage
	uv run pytest --verbose --cov=app tests/

check: lint test ## Run lint, tests, and format check
	uv run ruff format --check $(APP_DIR) $(TEST_DIR)

run-local: ## Run FastAPI app locally
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

clean: ## Remove Python cache files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".coverage" -exec rm -rf {} + 2>/dev/null || true

all: install check ## Install dependencies and run all checks
