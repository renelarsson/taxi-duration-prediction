# Make sure to create state bucket beforehand
terraform {
  required_version = ">= 1.0"
  backend "s3" {
    # For dev, use: your-dev-bucket -> .env.local-me, stg.tfvars, deploy_manual.sh
    # For prod, use: your-prod-bucket -> template.yaml (prod stack), GitHub Actions deploy steps
    bucket  = "your-dev-bucket"
    key     = "mlops-capstone-prod.tfstate"
    region  = "eu-north-1"
    encrypt = true
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current_identity" {}

locals {
  account_id = data.aws_caller_identity.current_identity.account_id
}

# Kinesis taxi_trip_events - input stream for taxi data
module "source_kinesis_stream" {
  source = "./modules/kinesis"
  stream_name = var.source_stream_name
  shard_count = var.shard_count
  retention_period = var.retention_period
  shard_level_metrics = var.shard_level_metrics
  tags = { CreatedBy = var.project_id }
}

# Kinesis taxi_predictions - output stream for prediction results
module "output_kinesis_stream" {
  source = "./modules/kinesis"
  stream_name = var.output_stream_name
  shard_count = var.shard_count
  retention_period = var.retention_period
  shard_level_metrics = var.shard_level_metrics
  tags = { CreatedBy = var.project_id }
}

# s3 model bucket for storing ML models
# module "s3_bucket" {
#   source = "./modules/s3"
#   bucket_name = "${var.model_bucket}-${var.project_id}"
# }

# ECR image registry for Lambda container
module "ecr_image" {
   source = "./modules/ecr"
   ecr_repo_name = "${var.ecr_repo_name}_${var.project_id}"
   account_id = local.account_id
   lambda_function_local_path = var.lambda_function_local_path
   docker_image_local_path = var.docker_image_local_path
   region = var.aws_region
}

# Lambda function for streaming predictions
module "lambda_function" {
  source = "./modules/lambda"
  image_uri = module.ecr_image.image_uri
  lambda_function_name = "${var.lambda_function_name}_${var.project_id}"
  model_bucket = var.model_bucket
  output_stream_name = "${var.output_stream_name}-${var.project_id}"
  output_stream_arn = module.output_kinesis_stream.stream_arn
  source_stream_name = "${var.source_stream_name}-${var.project_id}"
  source_stream_arn = module.source_kinesis_stream.stream_arn
}

# Output values for CI/CD pipeline
output "lambda_function" {
  value     = "${var.lambda_function_name}_${var.project_id}"
}

output "model_bucket" {
  value = var.model_bucket
}

output "predictions_stream_name" {
  value     = "${var.output_stream_name}-${var.project_id}"
}

output "ecr_repo" {
  value = "${var.ecr_repo_name}_${var.project_id}"
}
