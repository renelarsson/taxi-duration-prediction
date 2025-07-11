#!/bin/bash

PROJECT_NAME="capstone-project"
mkdir $PROJECT_NAME && cd $PROJECT_NAME

# Create directory structure
# Root structure
mkdir -p .github/workflows
mkdir -p config
mkdir -p scripts
mkdir -p integration-test
mkdir -p integration-test/model
mkdir -p tests/unit
mkdir -p tests/integration
mkdir -p .vscode

# Infrastructure (hierarchical order)
mkdir -p infrastructure/vars
mkdir -p infrastructure/terraform/modules/kinesis
mkdir -p infrastructure/terraform/modules/s3  
mkdir -p infrastructure/terraform/modules/ecr
mkdir -p infrastructure/terraform/modules/lambda

# Application code (logical order)
mkdir -p src/data
mkdir -p src/models
mkdir -p src/monitoring
mkdir -p src/deployment
mkdir -p workflows

# Create files with 'heredoc' and one filename per line (.gitkeep_structure)
cat > .gitkeep_structure << 'EOF'
README.md
.gitignore
.env.example
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
integration-test/docker-compose.yaml
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

# Create all files
xargs touch < .gitkeep_structure
rm .gitkeep_structure

# Initialize git
git init

echo "Project structure created successfully!"