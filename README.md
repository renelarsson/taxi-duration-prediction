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
- Workflow orchestration
- Code quality and reproducibility

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
- `event.json` — Local SAM testing

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
git clone https://github.com/renelarsson/taxi-duration-prediction
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

## LocalStack Training and Testing Workflow (Automated)

You can run the manual or automated workflow or see my training and test sessions in the unit-test-results.txt and integration-test-results.txt
files. Remember to use the Dockerfile.local to build the local backend Docker image for development and testing with LocalStack.

1. **Automate and run all tests and code checks**
    ```bash
    make full-test
    ```

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
    aws --endpoint-url=http://localhost:4566 s3 mb s3://your-dev-bucket --region your-region
    aws --endpoint-url=http://localhost:4566 kinesis create-stream --stream-name stg_taxi_predictions --shard-count 1 --region your-region
    aws --endpoint-url=http://localhost:4566 kinesis create-stream --stream-name stg_taxi_trip_events --shard-count 1 --region your-region
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

5. **Shutdown and clean up LocalStack**
    ```bash
    docker-compose --env-file .env.dev -f docker-compose.local.yaml down
    docker-compose --env-file .env.dev -f docker-compose.local.yaml down -v
    sudo rm -rf ./localstack-data
    ```

---

## AWS SAM Deployment (Production/Cloud)

> **Warning:**  
> AWS resources such as Lambda, S3, Kinesis, and ECR will incur charges.  
> Always delete unused resources after testing or deployment to avoid unexpected costs.

### 1. Configure AWS Credentials

```bash
aws configure
```

### 2. Initialize an AWS SAM Project

```bash
sam init
```

### 3. Validate and Build the SAM Application

```bash
sam validate --region your-region
sam build --region your-region
```

### 4. Switch to production environment

```bash
cp .env.prod-user .env
export $(grep -v '^#' .env | xargs)
```

### 5. Build and push Lambda Docker image

```bash
docker build -f terraform/Dockerfile -t taxi-duration-lambda:latest .
docker tag taxi-duration-lambda:latest <AWS_ACCOUNT_ID>.dkr.ecr.your-region.amazonaws.com/taxi-duration-lambda:latest
aws ecr get-login-password --region your-region | docker login --username AWS --password-stdin <AWS_ACCOUNT_ID>.dkr.ecr.your-region.amazonaws.com
docker push <AWS_ACCOUNT_ID>.dkr.ecr.your-region.amazonaws.com/taxi-duration-lambda:latest
```
> The `taxi-duration-lambda` image is created during the Docker build step and can be found locally with `docker image ls` or in your ECR repository after pushing.

### 6. Deploy with AWS SAM 

```bash
sam deploy --guided
```
- Follow the prompts to set stack name, region, S3 bucket, and parameters.
- Confirm that the correct image URI is used for your Lambda function.

### 7. Create and configure AWS resources

- Ensure your S3 bucket, Kinesis streams, and IAM roles are created and configured as required by your SAM template.
- You can use the AWS Console or CLI for verification.

**Example AWS CLI commands:**
```bash
# Create S3 bucket
aws s3 mb s3://your-model-bucket --region your-region

# Create Kinesis stream
aws kinesis create-stream --stream-name your-predictions-stream --shard-count 1 --region your-region

# Create IAM role (example, use your own trust policy and permissions)
aws iam create-role --role-name your-lambda-role --assume-role-policy-document file://trust-policy.json

# Attach policy to IAM role
aws iam attach-role-policy --role-name your-lambda-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

- After deployment, verify resources in the AWS Console or with CLI commands like `aws s3 ls`, `aws kinesis list-streams`, and `aws iam list

### 8. Invoke and test Lambda

- Prepare a valid Kinesis event (`event.json`) with base64-encoded data.
- Invoke your Lambda function:
  ```bash
  aws lambda invoke --function-name prod_taxi_duration_prediction --payload file://event.json output.json --region your-region
  ```
- Check `output.json` for results.
- Review CloudWatch logs for errors and debugging.

### 9. Monitor and clean up AWS resources

- **To avoid charges, delete resources when finished:**
  - **Delete Lambda function:**
    ```bash
    aws lambda delete-function --function-name prod_taxi_duration_prediction --region your-region
    ```
  - **Delete Kinesis streams:**
    ```bash
    aws kinesis delete-stream --stream-name prod_taxi_predictions --region your-region --enforce-consumer-deletion
    aws kinesis delete-stream --stream-name prod_taxi_trip_events --region your-region --enforce-consumer-deletion
    ```
  - **Delete S3 buckets and objects:** 
    ```bash
    aws s3 rm s3://your-dev-bucket --recursive --region your-region
    aws s3api delete-bucket --bucket your-dev-bucket --region your-region
    ```
  - **Delete ECR repository:**
    ```bash
    aws ecr delete-repository --repository-name taxi-duration-lambda --region your-region --force
    ```
  - **Delete CloudFormation/SAM stack:**
    ```bash
    aws cloudformation delete-stack --stack-name <your-stack-name> --region your-region
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
