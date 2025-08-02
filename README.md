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
├── workflows/                # ML pipeline scripts (Prefect, batch, etc.)
├── terraform/                # IaC scripts, Lambda handler, Dockerfile, requirements
├── tests/                    # Unit and integration tests
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

- `.env.dev-user` — Development environment variables
- `.env.prod-user` — Production environment variables
- `template.yaml` — AWS SAM template
- `terraform/vars/stg.tfvars` — Terraform dev variables
- `terraform/vars/prod.tfvars` — Terraform prod variables
- `.github/workflows/cd.yaml` — CI/CD pipeline
- `sam-env.json` — Local SAM testing

Switch environments by copying the appropriate file to `.env` and exporting variables:
```bash
cp .env.dev-user .env   # For development/localstack
cp .env.prod-user .env  # For production/AWS
export $(grep -v '^#' .env | xargs)
```

---

## To run or reproduce the project

### 1. Clone the repository

```bash
git clone <repo-url>
cd taxi-duration-prediction
```

### 2. (Optional) Run the setup script

```bash
chmod +x setup_project.sh
./setup_project.sh
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 4. Set up environment variables

Copy `.env.dev-user` or `.env.prod-user` to `.env` and fill in your secrets and configuration.

---

## LocalStack Training and Testing Workflow (Manual)

1. **Build Docker images**
    ```bash
    docker-compose --env-file .env.dev -f docker-compose.local.yaml build
    ```

2. **Start LocalStack and services**
    ```bash
    docker-compose --env-file .env.dev-user -f docker-compose.local.yaml up -d
    ```

3. **Create AWS resources in LocalStack**
    ```bash
    aws --endpoint-url=http://localhost:4566 s3 mb s3://rll-models-prod --region eu-north-1
    aws --endpoint-url=http://localhost:4566 kinesis create-stream --stream-name prod_taxi_predictions --shard-count 1 --region eu-north-1
    aws --endpoint-url=http://localhost:4566 kinesis create-stream --stream-name prod_taxi_trip_events --shard-count 1 --region eu-north-1
    ```

4. **Run training and tests inside the backend container**
    ```bash
    docker exec -it taxi-duration-prediction-backend-1 bash
    export $(grep -v '^#' /var/task/.env.dev | xargs)
    python -m src.models.train
    pytest /var/task/tests/unit/
    pytest /var/task/tests/integration
    exit
    ```

5. **Automate and run all tests and code checks**
    ```bash
    make full-test
    ```

6. **Shutdown and clean up LocalStack**
    ```bash
    docker-compose --env-file .env.dev -f docker-compose.local.yaml down
    docker-compose --env-file .env.dev -f docker-compose.local.yaml down -v
    sudo rm -rf ./localstack-data
    ```

---

## AWS SAM Deployment (Production/Cloud)

> **Warning:**  
> AWS resources such as Lambda, S3, Kinesis, and ECR may incur charges.  
> Always delete unused resources after testing or deployment to avoid unexpected costs.

### 1. Switch to production environment

```bash
cp .env.prod-user .env
export $(grep -v '^#' .env | xargs)
```

### 2. Build and push Lambda Docker image

```bash
docker build -f terraform/Dockerfile -t taxi-duration-lambda:latest .
docker tag taxi-duration-lambda:latest 887329216606.dkr.ecr.eu-north-1.amazonaws.com/taxi-duration-lambda:latest
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin 887329216606.dkr.ecr.eu-north-1.amazonaws.com
docker push 887329216606.dkr.ecr.eu-north-1.amazonaws.com/taxi-duration-lambda:latest
```

### 3. Deploy with AWS SAM

```bash
sam deploy --guided
```
- Follow the prompts to set stack name, region, S3 bucket, and parameters.
- Confirm that the correct image URI is used for your Lambda function.

### 4. Create and configure AWS resources

- Ensure your S3 bucket, Kinesis streams, and IAM roles are created and configured as required by your SAM template.
- You can use the AWS Console or CLI for verification.

### 5. Invoke and test Lambda

- Prepare a valid Kinesis event (`event.json`) with base64-encoded data.
- Invoke your Lambda function:
  ```bash
  aws lambda invoke --function-name prod_taxi_duration_prediction --payload file://event.json output.json --region eu-north-1
  ```
- Check `output.json` for results.
- Review CloudWatch logs for errors and debugging.

### 6. Monitor and clean up AWS resources

- **To avoid charges, delete resources when finished:**
  - **Delete Lambda function:**
    ```bash
    aws lambda delete-function --function-name prod_taxi_duration_prediction --region eu-north-1
    ```
  - **Delete Kinesis streams:**
    ```bash
    aws kinesis delete-stream --stream-name prod_taxi_predictions --region eu-north-1 --enforce-consumer-deletion
    aws kinesis delete-stream --stream-name prod_taxi_trip_events --region eu-north-1 --enforce-consumer-deletion
    ```
  - **Delete S3 buckets and objects:** 
    ```bash
    aws s3 rm s3://rll-models-prod --recursive --region eu-north-1
    aws s3api delete-bucket --bucket rll-models-prod --region eu-north-1
    ```
  - **Delete ECR repository:**
    ```bash
    aws ecr delete-repository --repository-name taxi-duration-lambda --region eu-north-1 --force
    ```
  - **Delete CloudFormation/SAM stack:**
    ```bash
    aws cloudformation delete-stack --stack-name <your-stack-name> --region eu-north-1
    ```

  - **Optional: Remove unused Docker volumes and networks**
    ```bash
    docker volume prune -f
    docker network prune -f
    ```

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