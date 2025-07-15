variable "source_stream_name" {
  type        = string
  description = "Source Kinesis Data Streams stream name"
}

variable "source_stream_arn" {
  type        = string
  description = "Source Kinesis Data Streams stream ARN"
}

variable "output_stream_name" {
  type        = string
  description = "Name of output stream where all the events will be passed"
}

variable "output_stream_arn" {
  type        = string
  description = "ARN of output stream where all the events will be passed"
}

variable "model_bucket" {
  type        = string
  description = "Name of the bucket"
}

variable "lambda_function_name" {
  type        = string
  description = "Name of the lambda function"
}

variable "image_uri" {
  type        = string
  description = "ECR image uri"
}