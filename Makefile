# Load environment variables from .env file
ifneq (,$(wildcard .env))
    include .env
    export
endif

# Define variables
APP_NAME = app
APP_DIR  = app
TEST_DIR = tests
DOCKER_IMAGE=fastapi-container
DOCKER_TAG=latest
DOCKER_REGISTRY=ghcr.io
DOCKER_REPOSITORY=fastapi-azure-container-app

# Define commands
# help: #List available commands
#	@echo "Available commands:"
# 	@awk 'BEGIN {FS = ":.*?#"}; /^[a-zA-Z0-9_-]+:.*?#/ {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)	
#	@grep -E '^[a-zA-Z0-9_-]+:.*?#.*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?#"}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'


install: #Install commands
	pip install --upgrade pip && \
	pip install -r requirements.txt

format: #Format the code
	black $(APP_DIR)/*.py $(APP_DIR)/**/*.py $(TEST_DIR)/*.py
	@echo "Code formatted successfully"

lint: #Lint the code
	pylint --disable=R,C $(APP_DIR)/*.py $(APP_DIR)/**/*.py $(TEST_DIR)/*.py

test: #Run tests
	python -m pytest --verbose --cov=app

build: #Build Docker container image
	docker buildx build -t $(DOCKER_REGISTRY)/$(DOCKER_OWNER)/$(DOCKER_REPOSITORY)/$(DOCKER_IMAGE):$(DOCKER_TAG) .

push: #Push Docker container image to GitHub Container Registry
	docker login --username $(DOCKER_OWNER) --password $(DOCKER_PASSWORD) $(DOCKER_REGISTRY)
	docker push $(DOCKER_REGISTRY)/$(DOCKER_OWNER)/$(DOCKER_REPOSITORY)/$(DOCKER_IMAGE):$(DOCKER_TAG)

pull: #Pull Docker container image from GitHub Container Registry
	docker pull $(DOCKER_REGISTRY)/$(DOCKER_OWNER)/$(DOCKER_REPOSITORY)/$(DOCKER_IMAGE):$(DOCKER_TAG)

run: #Run Docker container
	docker run -p 8080:8080 $(DOCKER_REGISTRY)/$(DOCKER_OWNER)/$(DOCKER_REPOSITORY)/$(DOCKER_IMAGE):$(DOCKER_TAG)

deploy: #Deploy the FastAPI application
#	deploy commands

all: install lint test deploy #Run all commands
	#test: ## Run tests
	#pytest
	#lint: ## Lint the code
	#flake8 app
	#docker-build: ## Build the Docker image
	#docker build -t $(DOCKER_IMAGE):$(DOCKER_TAG) .
	#docker-run: ## Run the Docker container
	#docker run -p 8000:8000 $(DOCKER_IMAGE):$(DOCKER_TAG)
