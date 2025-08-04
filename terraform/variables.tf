# terraform/variables.tf
# Streaming: Taxi Data → Kinesis Input → Lambda (ML Model) → Kinesis Output → Monitoring
# Environment separation: Use stg.tfvars + .env.dev for development (your-dev-bucket )
#                        Use prod.tfvars + .env.prod for production (your-prod-bucket)

variable "aws_region" {
  description = "AWS region to create resources"
  default     = "eu-north-1"
}

variable "project_id" {
  description = "Project identifier for resource naming"
  default     = "mlops-capstone"
}

# Streaming-specific variables (end-to-end streaming)
variable "source_stream_name" {
  description = "Input Kinesis stream for taxi trip data (dev: stg_taxi_trip_events, prod: prod_taxi_trip_events)"
  type        = string
  default     = "taxi-trip-events"
}

variable "output_stream_name" {
  description = "Output Kinesis stream for predictions (dev: stg_taxi_predictions, prod: prod_taxi_predictions)"
  type        = string
  default     = "taxi-predictions"
}

variable "retention_period" {
  description = "Kinesis stream retention period in hours"
  type        = number
  default     = 48
}

variable "shard_count" {
  description = "Number of shards for Kinesis streams"
  type        = number
  default     = 2
}

variable "model_bucket" {
  description = "S3 bucket for storing ML models"
  type        = string
}

variable "lambda_function_local_path" {
  description = "Local path to Lambda function code"
  type        = string
  default     = "../taxi_duration_prediction/lambda_function.py"
}

variable "docker_image_local_path" {
  description = "Local path to Dockerfile for Lambda image"
  type        = string
  default     = "../taxi_duration_prediction/Dockerfile"
}

variable "ecr_repo_name" {
  description = "ECR repository name for Lambda container (dev: stg_taxi_duration_predictor, prod: prod_taxi_duration_predictor)"
  type        = string
  default     = "taxi-duration-predictor"
}

variable "lambda_function_name" {
  description = "Lambda function name for streaming predictions (dev: stg_taxi_duration_prediction, prod: prod_taxi_duration_prediction)"
  type        = string
  default     = "taxi-duration-prediction"
}

variable "shard_level_metrics" {
  description = "List of Kinesis shard level metrics to enable for monitoring and throughput analysis"
  type        = list(string)
  default     = [
    "IncomingBytes",
    "OutgoingBytes",
    "OutgoingRecords",
    "ReadProvisionedThroughputExceeded",
    "WriteProvisionedThroughputExceeded",
    "IncomingRecords",
    "IteratorAgeMilliseconds"
  ]
}
