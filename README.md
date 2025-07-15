# Taxi Duration Prediction: End-to-End MLOps Pipeline

## Overview

This repository contains the capstone project for the MLOps Zoomcamp course. It is a production-ready MLOps project for predicting taxi ride durations. It demonstrates modern MLOps best practices: data ingestion, model training, deployment, monitoring, and automation.

**Demo Video:**  
[Project Walkthrough](https://www.loom.com/share/8f99d25893de4fb8aaa95c0395c740b6)

---

## Problem Statement

Build, deploy, and monitor an ML model using:
- Experiment tracking (MLflow)
- Reproducible training pipelines
- Automated deployment (AWS Lambda, S3, Kinesis, ECR)
- Monitoring (Evidently, Grafana)
- CI/CD and Infrastructure as Code (Terraform, GitHub Actions)

---

## Project Structure

```
taxi-duration-prediction/
├── config/                    # Service and monitoring configuration (Grafana, etc.)
├── infrastructure/            # Terraform infrastructure as code (AWS: Lambda, S3, Kinesis, ECR)
│   ├── terraform/             # Main Terraform scripts and modules
│   └── vars/                  # Environment-specific variable files
├── src/                       # ML application code
│   ├── data/                  # Data extraction and preprocessing
│   ├── deployment/            # Lambda and Kinesis consumer code
│   ├── models/                # Model training and prediction
│   └── monitoring/            # Model/data drift monitoring (Evidently)
├── workflows/                 # Prefect workflow orchestration
├── tests/                     # Unit and integration tests
│   ├── integration/           # End-to-end pipeline tests
│   └── unit/                  # Model unit tests
├── scripts/                   # Deployment and cloud testing automation
├── integration-test/          # LocalStack and Docker-based integration testing
│   └── model/                 # MLflow model artifacts and environment files
├── model/                     # Production model artifacts (model.pkl, etc.)
├── data/                      # Data storage
├── output/                    # Output artifacts
├── lambda_function.py         # Lambda entry point
├── model.py                   # Core ML logic
├── Dockerfile                 # Container image definition
├── docker-compose.yaml        # Service orchestration
├── requirements.txt           # Production dependencies
├── requirements-dev.txt       # Development dependencies
├── Makefile                   # Automation commands
├── pyproject.toml             # Code quality tools
├── .pre-commit-config.yaml    # Pre-commit hooks
├── .gitignore                 # Git ignore patterns
├── plan.md                    # Project planning checklist
├── setup_project.sh           # One-step environment setup script
└── README.md                  # Project documentation
```

---

## Technologies Used

- **Cloud:** AWS (Lambda, S3, Kinesis, ECR), LocalStack for local AWS emulation
- **Experiment Tracking:** MLflow
- **Workflow Orchestration:** Prefect
- **Monitoring:** Evidently, Grafana
- **CI/CD:** GitHub Actions
- **Infrastructure as Code:** Terraform
- **Containerization:** Docker
- **Code Quality:** Black, isort, pylint, pytest, pre-commit

---


## How to Reproduce / Setup

All files required for review are already present in the repository. **Peer reviewers do not need to run the setup script.**

If you do want to use the setup script, make sure it is executable:
```bash
chmod +x setup_project.sh
```
Then you can run:
```bash
./setup_project.sh
```

## AWS SAM Template Configuration

Before deploying, edit `template.yaml` to set the following values for your project:

- `ImageUri`: Set to your own Docker image URI.
- `MODEL_BUCKET`: Set to your own S3 bucket for MLflow model artifacts.

Example:
```yaml
ImageUri: your-image:latest
Environment:
  Variables:
    MODEL_BUCKET: your-mlflow-bucket
```

Alternatively, you can parameterize these values in `template.yaml` for easier customization (see AWS SAM documentation).

To run or reproduce the project:

1. **Clone the repository**
2. **Run the setup script** (optional for reviewers):
   ```bash
   chmod +x setup_project.sh
   ./setup_project.sh
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```
4. **Set up environment variables:**
   - Copy `.env.example` to `.env` and fill in your secrets and configuration.
5. **Start services:**
   ```bash
   docker-compose up
   ```
6. **Provision infrastructure:**
   - Use Terraform scripts in `infrastructure/` to deploy AWS resources.
7. **Train and register your model:**
   - Run workflows in `workflows/` or scripts in `src/`.
8. **Deploy the model:**
   - Use scripts in `scripts/` or CI/CD pipeline.
7. **Run tests:**  
   ```bash
   pytest
   ```
   for unit/integration tests.
8. **Monitor:**  
   Use Grafana dashboards and Evidently monitoring.

---

## Datasets

See [datasets](https://github.com/DataTalksClub/data-engineering-zoomcamp/blob/main/projects/datasets.md) for ideas.

---

## Resources

- [Projects Gallery](https://datatalksclub-projects.streamlit.app/)

---

## License

This project is part of the DataTalksClub MLOps Zoomcamp course.

---

**Note:**  
For reproducibility, always use the `setup_project.sh` script to initialize your environment. This ensures all dependencies and configurations are set up correctly.
