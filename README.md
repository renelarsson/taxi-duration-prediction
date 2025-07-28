# Taxi Duration Prediction: End-to-End MLOps Pipeline

## Objective

Apply MLOps best practices to build, deploy, and monitor a machine learning model for predicting taxi ride durations.
This project demonstrates experiment tracking, reproducible pipelines, cloud deployment, monitoring, and automation using AWS and LocalStack.

---

## Problem Statement

Predict the duration of taxi rides using historical trip data.
The project covers:
- Data selection and preprocessing
- Model training and experiment tracking
- Automated deployment to AWS Lambda (streaming inference)
- Model monitoring and alerting (automated)
- Infrastructure as code and CI/CD

---

## Technologies Used

- **Cloud:** AWS (Lambda, S3, Kinesis, ECR), LocalStack (AWS emulation)
- **Experiment Tracking & Model Registry:** MLflow
- **Workflow Orchestration:** Prefect
- **Monitoring:** Evidently (automated)
- **CI/CD:** GitHub Actions
- **Infrastructure as Code:** Terraform, AWS SAM
- **Containerization:** Docker
- **Code Quality:** Black, isort, pylint, pytest, pre-commit
- **Visualization/Monitoring:** Grafana (via config, not manual use)

---

## Project Structure

```
taxi-duration-prediction/
├── src/                      # Source code for data, models, deployment, monitoring
│   ├── data/                 # Data extraction and preprocessing
│   ├── deployment/           # Lambda and Kinesis consumer code
│   ├── models/               # Model training and prediction
│   └── monitoring/           # Model/data drift monitoring (Evidently)
├── workflows/                # ML pipeline scripts (Prefect, batch, etc.)
├── terraform/                # IaC scripts, Lambda handler, Dockerfile, requirements
│   ├── Dockerfile            # Lambda container image definition
│   ├── lambda_function.py    # Lambda entry point
│   ├── model.py              # Core ML logic for Lambda
│   ├── requirements.txt      # Lambda dependencies
│   ├── backend-dev.conf      # Terraform backend config (dev)
│   ├── backend-prod.conf     # Terraform backend config (prod)
│   ├── main.tf               # Main Terraform configuration
│   ├── variables.tf          # Terraform variables
│   ├── modules/              # Terraform modules (ecr, kinesis, lambda, s3)
│   └── vars/                 # Environment-specific tfvars files
│       ├── prod.tfvars
│       └── stg.tfvars
├── tests/                    # Unit and integration tests
│   ├── integration/          # End-to-end pipeline tests
│   └── unit/                 # Model unit tests
├── model/                    # Model artifacts and configs (not versioned)
├── scripts/                  # Automation and deployment scripts
├── config/                   # Configuration files (e.g., Grafana dashboards)
├── .github/workflows/        # CI/CD automation
├── requirements-dev.txt      # Dev dependencies
├── Makefile                  # Automation commands
├── README.md                 # Project documentation
└── setup_project.sh          # One-step environment setup script
```

---

## Environment Separation

This project supports **environment separation** for development and production:

- **Key Files for Environment Separation:**
  - `.env.dev-user` — Development environment variables
  - `.env.prod-user` — Production environment variables
  - `template.yaml` — AWS SAM template (parameters for buckets, streams, etc.)
  - `terraform/vars/stg.tfvars` — Terraform dev variables
  - `terraform/vars/prod.tfvars` — Terraform prod variables
  - `.github/workflows/cd.yaml` — CI/CD pipeline, uses correct bucket per environment
  - `sam-env.json` — Local SAM testing, update values for dev/prod as needed

- **Development:**
  - Use `.env.dev-user` for local development and testing.
  - Example: `MODEL_BUCKET=<your-dev-s3-bucket>`
  - Streams: `<dev-taxi-trip-events>`, `<dev-taxi-predictions>`
  - S3 endpoint: LocalStack or AWS dev resources.

- **Production:**
  - Use `.env.prod-user` for real AWS deployment.
  - Example: `MODEL_BUCKET=<your-prod-s3-bucket>`
  - Streams: `<prod-taxi-trip-events>`, `<prod-taxi-predictions>`
  - S3 endpoint: AWS production resources.

All code loads environment variables using `os.getenv` or equivalent, so you can switch environments by changing the `.env` file or deployment configuration.
No bucket, stream, or run_id values are hardcoded in production logic.

---

## Environment Setup Guidelines

- Use `.env.dev-user` for local/dev/LocalStack.
- Use `.env.prod-user` for production/AWS.
- Load environment variables in your shell with:
  ```bash
  export $(grep -v '^#' <your-env-file> | xargs)
  ```
- Use Docker Compose for LocalStack, Terraform for infra, SAM for serverless, and Docker exec for debugging.

---

## Usage

1. **Set up your environment:**
   - Copy `.env.dev-user` or `.env.prod-user` to `.env` as needed.
   - Export environment variables or use a tool like `python-dotenv`.

2. **Development:**
   - Train and test locally using `.env.dev-user`.
   - Use LocalStack for AWS emulation if desired.

3. **Production:**
   - Deploy using `.env.prod-user` and real AWS resources.
   - Use `sam deploy --parameter-overrides ModelBucket=<your-prod-s3-bucket> ...` for production.

4. **Switching environments:**
   - Change the `.env` file or deployment parameters.
   - No code changes required—just update environment variables.

---

## To run or reproduce the project:

1. **Clone the repository**
2. **(Optional) Run the setup script:**
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
   - Copy `.env.dev-user` or `.env.prod-user` to `.env` as needed and fill in your secrets and configuration.
   - All code loads buckets, streams, and run IDs from environment variables.
5. **Start services:**
   ```bash
   docker-compose --env-file .env.dev-user -f docker-compose.local.yaml up -d
   ```
6. **Provision infrastructure:**
   - Use Terraform scripts in `terraform/` to deploy AWS resources:
     ```bash
     cd terraform
     terraform init -backend-config=backend-dev.conf
     terraform apply -var-file=vars/dev.tfvars
     ```
7. **Train and register your model:**
   - Run workflows in `workflows/` or scripts in `src/`:
     ```bash
     python src/train.py
     ```
8. **Automate and run tests:**
   ```bash
   make full-test
   ```
   *Full workflow: start services, ensure S3/Kinesis exist, train, test, shutdown, clean LocalStack data. Runs all unit and integration tests with code quality checks (Black, isort, pylint, pytest, pre-commit).*
9. **Deploy the model:**
   - Use scripts in `scripts/` or CI/CD pipeline.
   - For Lambda, build and push Docker image, then deploy with SAM:
     ```bash
     docker build -f terraform/Dockerfile -t taxi-duration-lambda:latest .
     docker tag taxi-duration-lambda:latest <your-account-id>.dkr.ecr.<your-region>.amazonaws.com/taxi-duration-lambda:latest
     aws ecr get-login-password --region <your-region> | docker login --username AWS --password-stdin <your-account-id>.dkr.ecr.<your-region>.amazonaws.com
     docker push <your-account-id>.dkr.ecr.<your-region>.amazonaws.com/taxi-duration-lambda:latest
     sam deploy --guided
     ```
10. **Invoke and test Lambda:**
    - Prepare a valid Kinesis event (`event.json`) and invoke:
      > **Note:**
      > Before deploying or testing on AWS, update the `eventSourceARN` in `tests/integration/event.json` to match your actual AWS account ID and Kinesis stream name (e.g., replace `<your-account-id>` and `<prod-stream-name>` with your deployed values).
      ```bash
      aws lambda invoke --function-name <your-lambda-function-name> --payload file://event.json output.json
      ```
    - Check CloudWatch logs for output and errors.
11. **Monitor and clean up AWS resources:**
    - Delete Kinesis streams, ECR repos, S3 objects, Lambda functions, and CloudFormation stacks as needed to avoid charges.

---

## Reproducibility & Best Practices

- All dependencies are versioned in `requirements.txt`.
- Environment separation via `.env.dev-user` and `.env.prod-user`.
- Infrastructure as code with Terraform and AWS SAM.
- CI/CD pipeline with GitHub Actions.
- Unit and integration tests in `tests/`.
- Code quality enforced with Black, isort, pylint, and pre-commit hooks.
- Makefile for automation.

---

## References

- [MLOps Zoomcamp](https://github.com/DataTalksClub/mlops-zoomcamp)
- [LocalStack Documentation](https://docs.localstack.cloud/)
- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/)
- [Terraform Documentation](https://www.terraform.io/docs/)
- [MLflow Documentation](https://mlflow.org/docs/latest/index.html)
- [Evidently Documentation](https://docs.evidentlyai.com/)
- [Grafana Documentation](https://grafana.com/docs/)

---

**For any questions or issues, please open an issue in this repository.**
