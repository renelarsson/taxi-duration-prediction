# Capstone Project: End-to-End MLOps Pipeline

## Overview

This repository contains the capstone project for the MLOps Zoomcamp course.  
The goal is to apply all course modules to build a robust, production-grade machine learning pipeline, covering data ingestion, model training, deployment, monitoring, and automation.

**Demo Video:**  
[Project Walkthrough](https://www.loom.com/share/8f99d25893de4fb8aaa95c0395c740b6)

---

## Problem Statement

This project demonstrates how to build, deploy, and monitor an ML model using modern MLOps best practices.  
You will:

- Select a dataset (see [Datasets](#datasets))
- Train and track a model using experiment tracking tools
- Build a reproducible training pipeline
- Deploy the model (batch, web service, or streaming)
- Monitor model performance and data drift
- Automate everything with CI/CD and Infrastructure as Code

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
├── lambda_function.py         # Lambda entry point
├── model.py                   # Core ML logic
├── Dockerfile                 # Container image definition
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

To run or reproduce the project:

1. **Clone the repository**
2. **(Optional) Install dependencies:**  
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```
3. **Set up environment variables:**  
   Copy `.env.example` to `.env` and fill in your secrets and configuration. Example variables:

   ```env
   # AWS Configuration
   AWS_REGION=your-aws-region
   AWS_ACCESS_KEY_ID=your-aws-access-key-id
   AWS_SECRET_ACCESS_KEY=your-secret-aws-access-key
   AWS_ACCOUNT_ID=your-aws-account-id

   # MLflow Configuration
   MLFLOW_TRACKING_URI=http://localhost:5000
   MLFLOW_S3_ENDPOINT_URL=https://s3.your-aws-region.amazonaws.com

   # Database Configuration
   DB_HOST=your-db-host
   DB_USER=your-db-user
   DB_PASSWORD=your-db-password
   DB_NAME=your-db-name

   # Streaming and Model Deployment
   OUTPUT_STREAM_NAME=your-output-stream-name
   PREDICTIONS_STREAM_NAME=your-predictions-stream-name
   MODEL_BUCKET=your-model-bucket
   INPUT_STREAM_NAME=your-input-stream-name
   ```
4. **Provision infrastructure:**  
   Use Terraform scripts in `infrastructure/` to deploy AWS resources.
5. **Train and register your model:**  
   Run workflows in `workflows/` or scripts in `src/`.
6. **Deploy the model:**  
   Use scripts in `scripts/` or CI/CD pipeline.
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
