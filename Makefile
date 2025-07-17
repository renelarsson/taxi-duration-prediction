# Makefile for Taxi Duration Prediction MLOps Project
# This Makefile defines targets for setting up the environment, running tests,
# performing code quality checks, building a Docker image, running integration tests,
# publishing the image, and cleaning up the project directory.
# Environment separation: Uses .env.dev for development, .env.prod for production.
# All bucket, stream, and credential values are loaded from environment variables for flexibility.
# Switch environments by copying .env.dev or .env.prod to .env before running targets 

LOCAL_TAG := $(shell date +"%Y-%m-%d-%H-%M")
LOCAL_IMAGE_NAME := mlops-capstone:$(LOCAL_TAG)

# Setup environment (installs dev dependencies and pre-commit hooks)
setup:
    pip install -r requirements-dev.txt
    pre-commit install

# Switch to development environment
env-dev:
    cp .env.dev .env
    @echo "Switched to development environment (.env.dev)"

# Switch to production environment
env-prod:
    cp .env.prod .env
    @echo "Switched to production environment (.env.prod)"

# Run tests (uses current .env for environment separation)
test:
    pytest tests/

# Code quality checks
quality_checks:
    isort .
    black .
    pylint --recursive=y .

# Build Docker image with environment separation
build-image:
    docker build --build-arg MODEL_BUCKET=$$(grep MODEL_BUCKET .env | cut -d '=' -f2) \
        -t $(LOCAL_IMAGE_NAME) .

# Run integration tests (uses current .env for environment separation)
integration-test:
    pytest tests/integration/

# Publish Docker image (example target, update as needed)
publish-image:
    docker tag $(LOCAL_IMAGE_NAME) your-ecr-repo/$(LOCAL_IMAGE_NAME)
    docker push your-ecr-repo/$(LOCAL_IMAGE_NAME)

# Clean up project directory
clean:
    find . -type d -name "__pycache__" -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete
    rm -rf output/*

.PHONY: setup env-dev env-prod test quality_checks build-image integration-test publish-image clean