#!/usr/bin/env bash
# Docker image publishing script for taxi duration prediction
# Based on MLOps Zoomcamp Module 6 publish patterns (app. 70 files for complete MLOps system)

# Exit immediately if any command exits with a non-zero status
set -e

# Configuration
AWS_REGION=${AWS_REGION:-"eu-north-1"}
ENVIRONMENT=${ENVIRONMENT:-"stg"}
PROJECT_NAME="taxi-duration-prediction"

# ECR repository configuration
ECR_REPO_NAME="${ENVIRONMENT}-${PROJECT_NAME}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
ECR_REPO_URI="${ECR_URI}/${ECR_REPO_NAME}"

# Image configuration
LOCAL_TAG=${LOCAL_TAG:-$(date +"%Y-%m-%d-%H-%M")}
LOCAL_IMAGE_NAME=${LOCAL_IMAGE_NAME:-"${PROJECT_NAME}:${LOCAL_TAG}"}
REMOTE_IMAGE_NAME="${ECR_REPO_URI}:${LOCAL_TAG}"
LATEST_IMAGE_NAME="${ECR_REPO_URI}:latest"

echo "Publishing image ${LOCAL_IMAGE_NAME} to ECR..."
echo "Environment: ${ENVIRONMENT}"
echo "AWS Region: ${AWS_REGION}"
echo "ECR Repository: ${ECR_REPO_NAME}"
echo "ECR URI: ${ECR_REPO_URI}"
echo "Local Image: ${LOCAL_IMAGE_NAME}"
echo "Remote Image: ${REMOTE_IMAGE_NAME}"

# Check if local image exists
if ! docker image inspect ${LOCAL_IMAGE_NAME} > /dev/null 2>&1; then
    echo "ERROR: Local image ${LOCAL_IMAGE_NAME} not found"
    echo "Build the image first with: docker build -t ${LOCAL_IMAGE_NAME} ."
    exit 1
fi

echo "Local image ${LOCAL_IMAGE_NAME} found"

# Login to ECR
echo "Logging in to ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_URI}

if [ $? -eq 0 ]; then
    echo "ECR login successful"
else
    echo "ERROR: ECR login failed"
    exit 1
fi

# Check if ECR repository exists, create if not
echo "Checking ECR repository..."
if aws ecr describe-repositories --repository-names ${ECR_REPO_NAME} --region ${AWS_REGION} > /dev/null 2>&1; then
    echo "ECR repository ${ECR_REPO_NAME} exists"
else
    echo "Creating ECR repository ${ECR_REPO_NAME}..."
    aws ecr create-repository --repository-name ${ECR_REPO_NAME} --region ${AWS_REGION}
    
    if [ $? -eq 0 ]; then
        echo "ECR repository created successfully"
    else
        echo "ERROR: Failed to create ECR repository"
        exit 1
    fi
fi

# Tag image for ECR
echo "Tagging image for ECR..."
docker tag ${LOCAL_IMAGE_NAME} ${REMOTE_IMAGE_NAME}
docker tag ${LOCAL_IMAGE_NAME} ${LATEST_IMAGE_NAME}

if [ $? -eq 0 ]; then
    echo "Image tagged successfully"
    echo "Tagged as: ${REMOTE_IMAGE_NAME}"
    echo "Tagged as: ${LATEST_IMAGE_NAME}"
else
    echo "ERROR: Failed to tag image"
    exit 1
fi

# Push image to ECR
echo "Pushing image to ECR..."
docker push ${REMOTE_IMAGE_NAME}
docker push ${LATEST_IMAGE_NAME}

if [ $? -eq 0 ]; then
    echo "Image pushed successfully to ECR"
else
    echo "ERROR: Failed to push image to ECR"
    exit 1
fi

# Verify the push
echo "Verifying image in ECR..."
aws ecr list-images --repository-name ${ECR_REPO_NAME} --region ${AWS_REGION} --output table

if [ $? -eq 0 ]; then
    echo "Image verification successful"
else
    echo "WARNING: Image verification failed, but push may have succeeded"
fi

# Cleanup local tags (optional)
if [ "$CLEANUP_LOCAL_TAGS" = "true" ]; then
    echo "Cleaning up local ECR tags..."
    docker rmi ${REMOTE_IMAGE_NAME} ${LATEST_IMAGE_NAME} || true
    echo "Local ECR tags cleaned up"
fi

echo ""
echo "Image publishing completed successfully!"
echo ""
echo "Publishing Summary:"
echo "Environment: ${ENVIRONMENT}"
echo "Local Image: ${LOCAL_IMAGE_NAME}"
echo "ECR Repository: ${ECR_REPO_URI}"
echo "Image Tag: ${LOCAL_TAG}"
echo "Latest Tag: latest"
echo ""
echo "Next steps:"
echo "1. Update your Lambda function to use the new image"
echo "2. Deploy with: ./scripts/deploy_manual.sh"
echo "3. Test the deployment with: TEST_DEPLOYMENT=true ./scripts/deploy_manual.sh"
echo ""
echo "ECR Image URI for deployment:"
echo "${REMOTE_IMAGE_NAME}"
