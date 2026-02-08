# Makefile for local development
# Docker build/push/deploy is handled by GitHub Actions CI/CD

.PHONY: help install format lint test check run-local clean all

# Define variables
APP_DIR = app
TEST_DIR = tests

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install Python dependencies
	uv sync

format: ## Format code with black
	black $(APP_DIR) $(TEST_DIR)

lint: ## Run pylint checks
	pylint --disable=R,C $(APP_DIR) $(TEST_DIR)

test: ## Run tests with coverage
	python -m pytest --verbose --cov=app tests/

check: format lint test ## Run format, lint, and tests

run-local: ## Run FastAPI app locally
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

clean: ## Remove Python cache files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".coverage" -exec rm -rf {} + 2>/dev/null || true

all: install check ## Install dependencies and run all checks
