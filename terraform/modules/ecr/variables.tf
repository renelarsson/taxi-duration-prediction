variable "ecr_repo_name" {
    type = string
    description = "ECR repo name"
}

variable "ecr_image_tag" {
    type = string
    description = "ECR image tag"
    default = "latest"
}

variable "lambda_function_local_path" {
    type = string
    description = "Local path to lambda function / python file"
}

variable "docker_image_local_path" {
    type = string
    description = "Local path to Dockerfile"
}

variable "region" {
    type = string
    description = "region"
    default = "eu-north-1" # Will be overwritten by main
}

variable "account_id" {
    type = string
    description = "AWS account ID"
}
