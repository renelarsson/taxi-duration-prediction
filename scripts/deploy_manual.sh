#!/bin/bash
# Manual deployment script for taxi duration prediction (app. 70 files for complete MLOps system)
# Based on MLOps Zoomcamp Module 6 deployment patterns

set -e

AWS_REGION=${AWS_REGION:-"eu-north-1"}
ENVIRONMENT=${ENVIRONMENT:-"stg"}
PROJECT_NAME="taxi-duration-prediction"

# LocalStack endpoint config (set to empty for AWS)
LS_ENDPOINT=${LS_ENDPOINT:-""}
if [ "$USE_LOCALSTACK" = "true" ]; then
    LS_ENDPOINT="--endpoint-url=http://localhost:4566"
    echo "Using LocalStack endpoint: $LS_ENDPOINT"
fi

if [ "$ENVIRONMENT" = "prod" ]; then
    export MODEL_BUCKET_PROD="rll-models-prod"
    export MODEL_BUCKET_DEV="rll-models-dev"
else
    export MODEL_BUCKET_PROD="rll-models-dev"
    export MODEL_BUCKET_DEV="rll-models-dev"
fi

echo "Starting manual deployment for ${ENVIRONMENT} environment"
echo "Region: ${AWS_REGION}"
echo "Model bucket (dev): ${MODEL_BUCKET_DEV}"
echo "Model bucket (prod): ${MODEL_BUCKET_PROD}"
echo "Predictions stream: ${PREDICTIONS_STREAM_NAME}"
echo "Lambda function: ${LAMBDA_FUNCTION}"

# Get latest RUN_ID from latest S3 partition
echo "Getting latest model RUN_ID from S3..."

export RUN_ID=$(aws s3api list-objects-v2 --bucket ${MODEL_BUCKET_DEV} \
    $LS_ENDPOINT \
    --query 'sort_by(Contents, &LastModified)[-1].Key' --output=text | cut -f2 -d/)

if [ -z "$RUN_ID" ]; then
    echo "ERROR: No RUN_ID found in bucket ${MODEL_BUCKET_DEV}"
    echo "Make sure you have trained models in the dev bucket"
    exit 1
fi

echo "Found latest RUN_ID: ${RUN_ID}"

# Sync model artifacts from dev to prod bucket
echo "Syncing model artifacts from dev to prod bucket..."

aws s3 sync s3://${MODEL_BUCKET_DEV} s3://${MODEL_BUCKET_PROD} \
    $LS_ENDPOINT \
    --exclude "*" \
    --include "*${RUN_ID}*"

if [ $? -eq 0 ]; then
    echo "Model artifacts synced successfully"
else
    echo "ERROR: Failed to sync model artifacts"
    exit 1
fi

# Update Lambda function environment variables
echo "Updating Lambda function configuration..."

aws lambda update-function-configuration \
  --function-name $LAMBDA_FUNCTION \
  $LS_ENDPOINT \
  --environment "Variables={PREDICTIONS_STREAM_NAME=$PREDICTIONS_STREAM_NAME,MODEL_BUCKET=$MODEL_BUCKET_PROD,RUN_ID=$RUN_ID}" \
  --region $AWS_REGION

if [ $? -eq 0 ]; then
    echo "Lambda function configuration updated successfully"
else
    echo "ERROR: Failed to update Lambda function configuration"
    exit 1
fi

# Verify deployment
echo "Verifying deployment..."

LAMBDA_CONFIG=$(aws lambda get-function-configuration \
    --function-name ${LAMBDA_FUNCTION} \
    $LS_ENDPOINT \
    --region ${AWS_REGION} \
    --output json)

if [ $? -eq 0 ]; then
    echo "Lambda function verification successful"
    echo "Function ARN: $(echo $LAMBDA_CONFIG | jq -r '.FunctionArn')"
    echo "Runtime: $(echo $LAMBDA_CONFIG | jq -r '.Runtime')"
    echo "Environment variables:"
    echo $LAMBDA_CONFIG | jq '.Environment.Variables'
else
    echo "ERROR: Lambda function verification failed"
    exit 1
fi

# Check if Kinesis stream exists
aws kinesis describe-stream \
    --stream-name ${PREDICTIONS_STREAM_NAME} \
    $LS_ENDPOINT \
    --region ${AWS_REGION} > /dev/null

if [ $? -eq 0 ]; then
    echo "Kinesis stream verification successful"
else
    echo "WARNING: Kinesis stream ${PREDICTIONS_STREAM_NAME} not found"
    echo "Make sure the stream is created via Terraform or manually"
fi

# Test the deployed function
if [ "$TEST_DEPLOYMENT" = "true" ]; then
    echo "Testing deployed function..."
    TEST_EVENT='{"Records":[{"kinesis":{"data":"'"$(echo '{"ride":{"PULocationID":130,"DOLocationID":205,"trip_distance":3.66},"ride_id":256}' | base64 -w 0)"'"}}]}'
    aws lambda invoke \
        --function-name ${LAMBDA_FUNCTION} \
        $LS_ENDPOINT \
        --region ${AWS_REGION} \
        --payload "$TEST_EVENT" \
        /tmp/lambda_response.json

    if [ $? -eq 0 ]; then
        echo "Lambda function test successful"
        echo "Response:"
        cat /tmp/lambda_response.json | jq .
        rm -f /tmp/lambda_response.json
    else
        echo "ERROR: Lambda function test failed"
        exit 1
    fi
fi

echo ""
echo "Manual deployment completed successfully!"
echo ""
echo "Deployment Summary:"
echo "Environment: ${ENVIRONMENT}"
echo "Model RUN_ID: ${RUN_ID}"
echo "Lambda Function: ${LAMBDA_FUNCTION}"
echo "Kinesis Stream: ${PREDICTIONS_STREAM_NAME}"
echo "Model Bucket: ${MODEL_BUCKET_PROD}"
echo ""
echo "Next steps:"
echo "1. Test the deployment with: TEST_DEPLOYMENT=true USE_LOCALSTACK=true ./scripts/deploy_manual.sh"
echo "2. Monitor the Lambda function logs in CloudWatch or LocalStack"
echo "3. Verify predictions are being sent to Kinesis stream"
echo "4. Set up monitoring
