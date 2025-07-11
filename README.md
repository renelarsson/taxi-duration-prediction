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

1. **Clone the repository**
2. **Run the setup script:**  
   ```bash
   ./setup_project.sh
   ```
   This will install dependencies, set up your environment, and prepare the repo for development.
3. **(Optional) Manual dependency installation:**  
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```
4. **Set up environment variables:**  
   Copy `.env.example` to `.env` and fill in your secrets.
5. **Provision infrastructure:**  
   Use Terraform scripts in `infrastructure/` to deploy AWS resources.
6. **Train and register your model:**  
   Run workflows in `workflows/` or scripts in `src/`.
7. **Deploy the model:**  
   Use scripts in `scripts/` or CI/CD pipeline.
8. **Run tests:**  
   ```bash
   pytest
   ```
   for unit/integration tests.
9. **Monitor:**  
   Use Grafana dashboards and Evidently monitoring.

---

## Evaluation Criteria

- **Problem description:** Clearly state the ML problem and solution.
- **Cloud usage:** Use cloud services or LocalStack for infrastructure.
- **Experiment tracking & registry:** Track experiments and register models.
- **Workflow orchestration:** Automate pipelines with Prefect or similar.
- **Model deployment:** Containerize and deploy your model.
- **Model monitoring:** Monitor metrics and data drift.
- **Reproducibility:** Provide clear instructions and specify dependency versions.
- **Best practices:**  
  - Unit tests  
  - Integration tests  
  - Linter/code formatter  
  - Makefile  
  - Pre-commit hooks  
  - CI/CD pipeline

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
