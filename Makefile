# Makefile for Taxi Duration Prediction MLOps Project
# This Makefile automates environment setup, testing, Docker builds, and cleanup.
# The 'full-test' target runs the entire workflow: starts services, trains the model,
# runs unit/integration tests, saves results, shuts down containers, and cleans up data.

LOCAL_TAG := $(shell date +"%Y-%m-%d-%H-%M")
LOCAL_IMAGE_NAME := mlops-capstone:$(LOCAL_TAG)

# Setup environment (installs dev dependencies and pre-commit hooks)
setup:
    @pip install -r requirements-dev.txt
    @pre-commit install

# Switch to development environment
env-dev:
    @cp .env.dev .env
    @echo "Switched to development environment (.env.dev)"

# Switch to production environment
env-prod:
    @cp .env.prod .env
    @echo "Switched to production environment (.env.prod)"

# Run all unit tests (host or container)
test:
    @pytest tests/

# Code quality checks
quality_checks:
    @isort .
    @black .
    @pylint --recursive=y .

# Build Docker image with environment separation
build-image:
    @docker build --build-arg MODEL_BUCKET=$$(grep MODEL_BUCKET .env | cut -d '=' -f2) \
        -t $(LOCAL_IMAGE_NAME) .

# Run integration tests (host or container)
integration-test:
    @pytest tests/integration/

# Publish Docker image (example target, update as needed)
publish-image:
    @docker tag $(LOCAL_IMAGE_NAME) your-ecr-repo/$(LOCAL_IMAGE_NAME)
    @docker push your-ecr-repo/$(LOCAL_IMAGE_NAME)

# Clean up project directory
clean:
    @find . -type d -name "__pycache__" -exec rm -rf {} +
    @find . -type f -name "*.pyc" -delete
    @rm -rf output/*

# Full workflow: start services, train, test, shutdown, clean LocalStack data
full-test:
    @echo "Activating environment and starting services..."
    conda run -n myenv docker-compose --env-file .env.dev -f docker-compose.local.yaml up -d
    sleep 5
    aws --endpoint-url=http://localhost:4566 s3 mb s3://mlflow-models-rll --region eu-north-1 || true
    @echo "Training model..."
    conda run -n myenv docker exec taxi-duration-prediction-backend-1 bash -c "export \$(grep -v '^#' /var/task/.env.dev | xargs) && python -m src.models.train"
    @echo "Running unit tests..."
    conda run -n myenv docker exec taxi-duration-prediction-backend-1 pytest /var/task/tests/unit | tee unit-test-results.txt
    @echo "Running integration tests..."
    conda run -n myenv docker exec taxi-duration-prediction-backend-1 pytest /var/task/tests/integration | tee integration-test-results.txt
    @echo "Shutting down containers..."
    conda run -n myenv docker-compose --env-file .env.dev -f docker-compose.local.yaml down
    @echo "Cleaning up LocalStack data directories..."
    rm -rf .localstack .localstack-volume localstack-data
    @echo "All done. See unit-test-results.txt and integration-test-results.txt for results."

.PHONY: setup env-dev env-prod test quality_checks build-image integration-test publish-image clean full-test