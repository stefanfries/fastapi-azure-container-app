install: #Install commands
	pip install --upgrade pip &&\
	pip install -r requirements.txt
format: #Format the code
	#format code
lint: #Lint the code
	#flake8 or pylint
	#flake8 $(APP_NAME)
test: ## Run tests
	#test commands
deploy: ## Deploy the FastAPI application
	#deploy commands
all: install lint test deploy ## Run all commands
	#run: ## Run the FastAPI application
	#uvicorn $(APP_NAME).main:app --reload
	#test: ## Run tests
	#pytest
	#lint: ## Lint the code
	#flake8 $(APP_NAME)
	#docker-build: ## Build the Docker image
	#docker build -t $(DOCKER_IMAGE):$(DOCKER_TAG) .
	#docker-run: ## Run the Docker container
	#docker run -p 8000:8000 $(DOCKER_IMAGE):$(DOCKER_TAG)
