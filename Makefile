# Makefile for MLOps Capstone Project
# This Makefile defines targets for setting up the environment, running tests,
# performing code quality checks, building a Docker image, running integration tests,
# publishing the image, and cleaning up the project directory.
# Variables
LOCAL_TAG:=$(shell date +"%Y-%m-%d-%H-%M")
LOCAL_IMAGE_NAME:=mlops-capstone:${LOCAL_TAG}

# Setup environment
setup:
    pip install -r requirements-dev.txt # pip instead of pipenv given requirements.txt-based setup 
    pre-commit install

# Run tests
test:
    pytest tests/

# Code quality checks
quality_checks:
    isort .
    black .
    pylint --recursive=y .

# Build Docker image
build: quality_checks test
    docker build -t ${LOCAL_IMAGE_NAME} .

# Integration tests (depends on build)
integration_test: build
    LOCAL_IMAGE_NAME=${LOCAL_IMAGE_NAME} bash integration-test/run.sh

# Publish image (depends on build and integration_test)
publish: build integration_test
    LOCAL_IMAGE_NAME=${LOCAL_IMAGE_NAME} bash scripts/publish.sh

# Clean up
clean:
    find . -type f -name "*.pyc" -delete #  Finds all .pyc files (compiled Python)
    find . -type d -name "__pycache__" -delete # Finds all __pycache__ directories

# Provide 'phony targets' to Make (command names, not files)
.PHONY: setup test quality_checks build integration_test publish clean
