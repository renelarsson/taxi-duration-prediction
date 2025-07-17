#!/bin/bash 

# =============================
# User Settings (Change These!)
# =============================
# Set your project name below. This will be the root folder for your project.
# Example: PROJECT_NAME="my-project-name"
# New users should change PROJECT_NAME to match their own project/repo name.
PROJECT_NAME="taxi-duration-prediction" # <-- Change this to your desired project name

# =============================
# Environment Separation
# =============================
# Choose environment: dev or prod
# Usage: ./setup_project.sh dev   OR   ./setup_project.sh prod
ENVIRONMENT=${1:-dev}

if [ "$ENVIRONMENT" == "prod" ]; then
    cp .env.prod .env
    echo "Using production environment (.env.prod)"
else
    cp .env.dev .env
    echo "Using development environment (.env.dev)"
fi

# Create the main project directory and move into it
mkdir -p $PROJECT_NAME && cd $PROJECT_NAME

# =============================
# Directory Structure Creation
# =============================
# The following commands create the recommended folder structure for the project.
# You can modify or extend these as needed for your use case.

# Root structure
mkdir -p model                # Production model artifacts
mkdir -p data                 # Data storage
mkdir -p output               # Output artifacts
mkdir -p .github/workflows    # CI/CD workflows
mkdir -p config               # Configuration files (Grafana, etc.)
mkdir -p scripts              # Deployment and automation scripts
mkdir -p integration-test     # Integration testing
mkdir -p integration-test/model
mkdir -p tests/unit           # Unit tests
mkdir -p tests/integration    # Integration tests
mkdir -p .vscode              # VSCode settings

# Infrastructure (hierarchical order)
mkdir -p infrastructure/vars   # Terraform variable files
mkdir -p infrastructure/terraform/modules/kinesis
mkdir -p infrastructure/terraform/modules/s3  
mkdir -p infrastructure/terraform/modules/ecr
mkdir -p infrastructure/terraform/modules/lambda

# Application code (logical order)
mkdir -p src/data              # Data extraction and preprocessing
mkdir -p src/models            # Model training and prediction
mkdir -p src/monitoring        # Model/data drift monitoring
mkdir -p src/deployment        # Lambda and Kinesis consumer code
mkdir -p workflows             # Prefect workflow orchestration

# =============================
# File Creation
# =============================
# The following block creates empty files for your project structure.
# You should fill these files with your own code, configuration, and documentation.
# Some files (like .env.example) contain example settings and should be updated with your own secrets and credentials.
# New users should update secrets, passwords, and sensitive config in .env.example, tfvars, and config files.

cat > .gitkeep_structure << 'EOF'
README.md
.gitignore
.env
.env.example
.env.dev
.env.prod
requirements.txt
requirements-dev.txt
.pre-commit-config.yaml
pyproject.toml
Makefile
config/grafana_datasources.yaml
config/grafana_dashboards.yaml
infrastructure/vars/stg.tfvars
infrastructure/vars/prod.tfvars
infrastructure/terraform/variables.tf
infrastructure/terraform/main.tf
infrastructure/terraform/modules/kinesis/variables.tf
infrastructure/terraform/modules/kinesis/main.tf
infrastructure/terraform/modules/s3/variables.tf
infrastructure/terraform/modules/s3/main.tf
infrastructure/terraform/modules/ecr/variables.tf
infrastructure/terraform/modules/ecr/main.tf
infrastructure/terraform/modules/lambda/variables.tf
infrastructure/terraform/modules/lambda/main.tf
infrastructure/terraform/modules/lambda/iam.tf
lambda_function.py
model.py
Dockerfile
docker-compose.yaml
model/MLmodel
model/README.txt
model/conda.yaml
model/model.pkl
model/python_env.yaml
model/requirements-test.txt
data/.gitkeep
output/.gitkeep
src/data/extract.py
src/data/preprocess.py
src/models/train.py
src/models/predict.py
src/monitoring/evidently_monitor.py
src/deployment/lambda_handler.py
src/deployment/kinesis_consumer.py
workflows/training_pipeline.py
workflows/inference_pipeline.py
workflows/monitoring_pipeline.py
tests/__init__.py
tests/data.b64
tests/unit/__init__.py
tests/unit/model_test.py
tests/integration/__init__.py
tests/integration/test_pipeline_e2e.py
tests/integration/test_workflow.py
scripts/deploy_manual.sh
scripts/publish.sh
scripts/test_cloud_e2e.sh
integration-test/run.sh
integration-test/event.json
integration-test/test_docker.py
integration-test/test_kinesis.py
integration-test/model/MLmodel
integration-test/model/conda.yaml
integration-test/model/model.pkl
integration-test/model/README.txt
integration-test/model/python_env.yaml
integration-test/model/requirements-test.txt
.github/workflows/ci.yaml
.github/workflows/cd.yaml
plan.md
.vscode/settings.json
EOF

# Create all files listed above
xargs touch < .gitkeep_structure
rm .gitkeep_structure

# =============================
# Git Initialization
# =============================
# Initializes a new git repository in your project folder.
git init

echo "Project structure created successfully with environment separation!"