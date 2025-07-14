# Streaming: Taxi Data → Kinesis Input → Lambda (ML Model) → Kinesis Output → Monitoring
variable "aws_region" {
  description = "AWS region to create resources"
  default = "eu-north-1"
}

variable "project_id" {
  description = "project_id"
  default = "mlops-capstone"
}

# Streaming-specific variables (end-to-end streaming)
variable "source_stream_name" { # Incoming taxi data
  description = "Input Kinesis stream for taxi trip data"
  default = "taxi-trip-events"
}

variable "output_stream_name" { # Prediction results
  description = "Output Kinesis stream for predictions"
  default = "taxi-predictions"
}

variable "retention_period" {
  description = "Kinesis stream retention period in hours"
  type = number
  default = 48
}

variable "shard_count" {
  description = "Number of shards for Kinesis streams"
  type = number
  default = 2
}

variable "model_bucket" {
  description = "s3_bucket for storing ML models"
  default = "mlflow-models-rll"
}

variable "lambda_function_local_path" { # Lambda paths points to project structure
  description = "Local path to lambda function code"
  default = "../lambda_function.py"
}

variable "docker_image_local_path" {
  description = "Local path to Dockerfile"
  default = "../Dockerfile"
}

variable "ecr_repo_name" {
  description = "ECR repository name for Lambda container"
  default = "taxi-duration-predictor"
}

variable "lambda_function_name" {
  description = "Lambda function name for streaming predictions"
  default = "taxi-duration-prediction"
}
