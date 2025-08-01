# ECR repository for storing the Lambda Docker image
resource "aws_ecr_repository" "repo" {
  name                 = var.ecr_repo_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = false
  }

  force_delete = true
}

# Build and push the Docker image to ECR using local-exec provisioner
# NOTE: The Docker build context is set to the project root so all files are available.
resource "null_resource" "ecr_image" {
#  triggers = {
#    python_file = md5(file(var.lambda_function_local_path))
#    docker_file = md5(file(var.docker_image_local_path))
#  }

  provisioner "local-exec" {
    command = <<EOF
      aws ecr get-login-password --region ${data.aws_region.current.name} | docker login --username AWS --password-stdin ${aws_ecr_repository.repo.repository_url}
      docker build -f ../terraform/Dockerfile -t ${aws_ecr_repository.repo.repository_url}:latest ..
      docker push ${aws_ecr_repository.repo.repository_url}:latest
EOF
  }
  depends_on = [aws_ecr_repository.repo]
}

# Get the image URI after pushing to ECR
data "aws_ecr_image" "lambda_image" {
  depends_on      = [null_resource.ecr_image]
  repository_name = var.ecr_repo_name
  image_tag       = var.ecr_image_tag
}

# Output the image URI for use in Lambda or other modules
output "image_uri" {
  value = "${aws_ecr_repository.repo.repository_url}:${data.aws_ecr_image.lambda_image.image_tag}"
}
