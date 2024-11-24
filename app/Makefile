# Makefile for FastAPI project

# Variables
APP_NAME=app
DOCKER_IMAGE=fastapi-app
DOCKER_TAG=latest

# Commands
.PHONY: help run test lint docker-build docker-run

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

install: ## Install dependencies
	# install commands pip install -r requirements.txt

format: ## Format the code
	# format commands
	
lint: ## Lint the code
	# flake8 or pylint
	# flake8 $(APP_NAME)

test: ## Run tests
	# test commands

deploy: ## Deploy the FastAPI application
	# deploy commands

all: install lint test deploy ## Run all commands


run: ## Run the FastAPI application
	uvicorn $(APP_NAME).main:app --reload

test: ## Run tests
	pytest

lint: ## Lint the code
	flake8 $(APP_NAME)

docker-build: ## Build the Docker image
	docker build -t $(DOCKER_IMAGE):$(DOCKER_TAG) .

docker-run: ## Run the Docker container
	docker run -p 8000:8000 $(DOCKER_IMAGE):$(DOCKER_TAG)