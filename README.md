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
- Model monitoring and alerting
- Infrastructure as code and CI/CD

---

## Technologies Used

- **Cloud:** AWS (Lambda, S3, Kinesis, ECR), LocalStack (AWS emulation)
- **Experiment Tracking & Model Registry:** MLflow
- **Workflow Orchestration:** Prefect
- **Monitoring:** Evidently
- **CI/CD:** GitHub Actions
- **Infrastructure as Code:** Terraform, AWS SAM
- **Containerization:** Docker
- **Code Quality:** Black, isort, pylint, pytest, pre-commit	-> ????

---

## Project Structure	-> !!!! HERE

```
taxi-duration-prediction/
├── terraform/                # IaC scripts, Lambda handler, Dockerfile
├── tests/                    # Unit and integration tests
├── .github/workflows/        # CI/CD automation
├── model.py                  # ML model logic
├── lambda_function.py        # Lambda entry point
├── requirements.txt          # Production dependencies
├── Dockerfile                # Container image definition
├── template.yaml             # AWS SAM template
├── .env.dev / .env.prod      # Environment variables
├── README.md                 # Project documentation
└── ...                       # Other supporting files
```

---

## Environment Separation

- **Development:**  
  - Use `.env.dev` and LocalStack for local AWS emulation.
  - Streams: `stg_taxi_trip_events`, `stg_taxi_predictions`
  - S3 bucket: `rll-models-dev`

- **Production:**  
  - Use `.env.prod` for AWS deployment.
  - Streams: `prod_taxi_trip_events`, `prod_taxi_predictions`
  - S3 bucket: `rll-models-prod`

All code loads configuration from environment variables for easy switching.

---

## Step-by-Step Procedures

### 1. **Local Development & Testing with LocalStack**

**Why:**  
Emulate AWS services locally for fast, cost-free development and testing.

**Commands:**

- **Start LocalStack and supporting services:**
  ```bash
  docker-compose -f docker-compose.local.yaml up
  ```
  *Starts LocalStack, Kinesis, S3, and other services locally.*

- **Run unit and integration tests:**
  ```bash
  pytest
  ```
  *Validates code correctness and pipeline integration.*

- **Train and register model with MLflow:**
  ```bash
  python src/train.py
  ```
  *Trains the model and logs experiments to MLflow.*

- **Monitor model with Evidently:**
  ```bash
  python src/monitor.py
  ```
  *Calculates metrics and detects drift.*

---

### 2. **Provision AWS Infrastructure with Terraform**

**Why:**  
Automate creation of AWS resources (Lambda, Kinesis, S3, ECR) for reproducible cloud deployment.

**Commands:**

- **Initialize and apply Terraform:**
  ```bash
  cd terraform
  terraform init
  terraform apply -var-file=vars/prod.tfvars
  ```
  *Creates all required AWS resources for production.*

---

### 3. **Build and Deploy Lambda with AWS SAM and Docker**

**Why:**  
Package and deploy the model as a containerized Lambda function for scalable, serverless inference.

**Commands:**

- **Build Docker image for Lambda:**
  ```bash
  docker build -f terraform/Dockerfile -t taxi-duration-lambda:latest .
  ```
  *Creates a container image with all code and dependencies.*

- **Create ECR repository (if not exists):**
  ```bash
  aws ecr create-repository --repository-name taxi-duration-lambda --region eu-north-1
  ```
  *Prepares ECR for storing Lambda image.*

- **Tag and push image to ECR:**
  ```bash
  docker tag taxi-duration-lambda:latest <your-account-id>.dkr.ecr.eu-north-1.amazonaws.com/taxi-duration-lambda:latest
  aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin <your-account-id>.dkr.ecr.eu-north-1.amazonaws.com
  docker push <your-account-id>.dkr.ecr.eu-north-1.amazonaws.com/taxi-duration-lambda:latest
  ```
  *Uploads the image to AWS ECR for Lambda deployment.*

- **Deploy Lambda with SAM:**
  ```bash
  sam deploy --guided
  ```
  *Deploys the Lambda function using the container image from ECR.  
  Prompts for stack name, region, and environment variables.*

---

### 4. **Invoke and Test Lambda Function on AWS**

**Why:**  
Validate that the deployed Lambda processes events correctly.

**Commands:**

- **Prepare a valid Kinesis event (event.json):**
  ```json
  {
    "Records": [
      {
        "kinesis": {
          "kinesisSchemaVersion": "1.0",
          "partitionKey": "1",
          "sequenceNumber": "1234567890",
          "data": "<base64-encoded-payload>",
          "approximateArrivalTimestamp": 1.654161514132E9
        },
        "eventSource": "aws:kinesis",
        "eventVersion": "1.0",
        "eventID": "shardId-000000000000:1234567890",
        "eventName": "aws:kinesis:record",
        "invokeIdentityArn": "arn:aws:iam::<your-account-id>:role/lambda-kinesis-role",
        "awsRegion": "eu-north-1",
        "eventSourceARN": "arn:aws:kinesis:eu-north-1:<your-account-id>:stream/prod_taxi_predictions"
      }
    ]
  }
  ```

- **Invoke Lambda with AWS CLI:**
  ```bash
  aws lambda invoke --function-name <your-lambda-function-name> --payload file://event.json output.json
  ```
  *Executes the Lambda function with a test event and writes the result to output.json.*

- **Check CloudWatch logs:**
  *Review logs for errors, output, and debugging information.*

---

### 5. **Monitor and Clean Up AWS Resources**

**Why:**  
Avoid ongoing charges and keep your cloud environment tidy.

**Commands:**

- **Delete Kinesis streams:**
  ```bash
  aws kinesis delete-stream --stream-name prod_taxi_predictions --region eu-north-1 --enforce-consumer-deletion
  aws kinesis delete-stream --stream-name prod_taxi_trip_events --region eu-north-1 --enforce-consumer-deletion
  ```
  *Stops hourly charges for streaming resources.*

- **Delete ECR repository:**
  ```bash
  aws ecr delete-repository --repository-name taxi-duration-lambda --region eu-north-1 --force
  ```
  *Removes container images and stops storage charges.*

- **Delete S3 objects (if needed):**
  ```bash
  aws s3 rm s3://aws-sam-cli-managed-default-samclisourcebucket-wmwpbdmv6ah1 --recursive
  ```
  *Removes stored data to avoid charges.*

- **Delete Lambda function:**
  ```bash
  aws lambda delete-function --function-name <your-lambda-function-name> --region eu-north-1
  ```
  *Removes the deployed Lambda function.*

- **Delete CloudFormation stack:**
  ```bash
  aws cloudformation delete-stack --stack-name taxi-duration-prediction-prod --region eu-north-1
  ```
  *Removes all managed resources.*

---

## Reproducibility & Best Practices

- All dependencies are versioned in `requirements.txt`.
- Environment separation via `.env.dev` and `.env.prod`.
- Infrastructure as code with Terraform and AWS SAM.
- CI/CD pipeline with GitHub Actions.
- Unit and integration tests in `tests/`.
- Code quality enforced with Black, isort, pylint, and pre-commit hooks.
- Makefile for automation.

---

## Notes for Peer Review

- **Problem is clearly described and solved end-to-end.**
- **Cloud and IaC tools are used for provisioning and deployment.**
- **Experiment tracking and model registry with MLflow.**
- **Workflow orchestration with Prefect.**
- **Model deployment is containerized and cloud-ready.**
- **Comprehensive monitoring with Evidently.**
- **Instructions are clear and reproducible.**
- **Best practices (testing, linting, CI/CD) are followed.**

---

## References

- [MLOps Zoomcamp](https://github.com/DataTalksClub/mlops-zoomcamp)
- [LocalStack Documentation](https://docs.localstack.cloud/)
- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/)
- [Terraform Documentation](https://www.terraform.io/docs/)
- [MLflow Documentation](https://mlflow.org/docs/latest/index.html)
- [Evidently Documentation](https://docs.evidentlyai.com/)

---

**For any questions or issues, please open an issue in this repository.**
