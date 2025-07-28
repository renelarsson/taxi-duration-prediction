#!/usr/bin/env bash
# End-to-end cloud testing script for taxi duration prediction
# Based on MLOps Zoomcamp Module 6 test_cloud_e2e.sh patterns (app. 70 files for complete MLOps system)

# Exit immediately if any command exits with a non-zero status
set -e

# Configuration
AWS_REGION=${AWS_REGION:-"eu-north-1"}
ENVIRONMENT=${ENVIRONMENT:-"stg"}
PROJECT_NAME="taxi-duration-prediction"

# Kinesis stream configuration (course pattern)
export KINESIS_STREAM_INPUT="${ENVIRONMENT}_ride_events_${PROJECT_NAME}"
export KINESIS_STREAM_OUTPUT="${ENVIRONMENT}_ride_predictions_${PROJECT_NAME}"

echo "Starting cloud E2E testing for ${ENVIRONMENT} environment"
echo "AWS Region: ${AWS_REGION}"
echo "Input stream: ${KINESIS_STREAM_INPUT}"
echo "Output stream: ${KINESIS_STREAM_OUTPUT}"

# Test ride data
TEST_RIDE_DATA='{
    "ride": {
        "PULocationID": 130,
        "DOLocationID": 205,
        "trip_distance": 3.66
    },
    "ride_id": 156
}'

echo "Test data: ${TEST_RIDE_DATA}"

# Put record to input stream (course pattern)
echo "Sending test record to input stream..."

SHARD_ID=$(aws kinesis put-record \
    --stream-name ${KINESIS_STREAM_INPUT} \
    --partition-key 1 \
    --cli-binary-format raw-in-base64-out \
    --data "${TEST_RIDE_DATA}" \
    --region ${AWS_REGION} \
    --query 'ShardId' \
    --output text)

if [ $? -eq 0 ]; then
    echo "Record sent successfully to shard: ${SHARD_ID}"
else
    echo "ERROR: Failed to send record to input stream"
    exit 1
fi

# Wait for processing
echo "Waiting for Lambda processing..."
sleep 10

# Get shard iterator for output stream
echo "Getting shard iterator for output stream..."

SHARD_ITERATOR=$(aws kinesis get-shard-iterator \
    --shard-id shardId-000000000000 \
    --shard-iterator-type TRIM_HORIZON \
    --stream-name ${KINESIS_STREAM_OUTPUT} \
    --region ${AWS_REGION} \
    --query 'ShardIterator' \
    --output text)

if [ $? -eq 0 ]; then
    echo "Shard iterator obtained: ${SHARD_ITERATOR:0:50}..."
else
    echo "ERROR: Failed to get shard iterator"
    exit 1
fi

# Get records from output stream
echo "Getting records from output stream..."

RECORDS_OUTPUT=$(aws kinesis get-records \
    --shard-iterator ${SHARD_ITERATOR} \
    --region ${AWS_REGION})

if [ $? -eq 0 ]; then
    echo "Records retrieved successfully"

    # Check if records exist
    RECORD_COUNT=$(echo ${RECORDS_OUTPUT} | jq '.Records | length')
    echo "Number of records found: ${RECORD_COUNT}"

    if [ "${RECORD_COUNT}" -gt "0" ]; then
        echo "SUCCESS: Found prediction records in output stream"

        # Display first record
        echo "First record data:"
        echo ${RECORDS_OUTPUT} | jq '.Records[0].Data' | base64 -d | jq .

        # Validate record structure
        FIRST_RECORD_DATA=$(echo ${RECORDS_OUTPUT} | jq -r '.Records[0].Data')
        DECODED_DATA=$(echo ${FIRST_RECORD_DATA} | base64 -d)

        # Check if prediction exists
        if echo ${DECODED_DATA} | jq -e '.prediction' > /dev/null; then
            echo "SUCCESS: Record contains prediction data"
            PREDICTION_VALUE=$(echo ${DECODED_DATA} | jq -r '.prediction.ride_duration')
            echo "Predicted ride duration: ${PREDICTION_VALUE} minutes"
        else
            echo "WARNING: Record does not contain expected prediction structure"
        fi

        # Check if ride_id matches
        RECORD_RIDE_ID=$(echo ${DECODED_DATA} | jq -r '.prediction.ride_id // .ride_id')
        if [ "${RECORD_RIDE_ID}" = "156" ]; then
            echo "SUCCESS: Ride ID matches test data"
        else
            echo "WARNING: Ride ID mismatch. Expected: 156, Got: ${RECORD_RIDE_ID}"
        fi

    else
        echo "WARNING: No records found in output stream"
        echo "This could mean:"
        echo "1. Lambda function is not triggered by input stream"
        echo "2. Lambda function has errors"
        echo "3. Processing is still in progress"
        echo "4. Output stream configuration is incorrect"
    fi
else
    echo "ERROR: Failed to get records from output stream"
    exit 1
fi

# Additional verification - check recent CloudWatch logs
echo "Checking recent Lambda function logs..."

LAMBDA_FUNCTION="${ENVIRONMENT}_prediction_lambda_${PROJECT_NAME}"
LOG_GROUP="/aws/lambda/${LAMBDA_FUNCTION}"

# Get latest log stream
LATEST_LOG_STREAM=$(aws logs describe-log-streams \
    --log-group-name ${LOG_GROUP} \
    --order-by LastEventTime \
    --descending \
    --max-items 1 \
    --region ${AWS_REGION} \
    --query 'logStreams[0].logStreamName' \
    --output text 2>/dev/null)

if [ "${LATEST_LOG_STREAM}" != "None" ] && [ -n "${LATEST_LOG_STREAM}" ]; then
    echo "Latest log stream: ${LATEST_LOG_STREAM}"

    # Get recent log events
    RECENT_LOGS=$(aws logs get-log-events \
        --log-group-name ${LOG_GROUP} \
        --log-stream-name ${LATEST_LOG_STREAM} \
        --start-time $(($(date +%s) * 1000 - 300000)) \
        --region ${AWS_REGION} \
        --query 'events[].message' \
        --output text 2>/dev/null)

    if [ -n "${RECENT_LOGS}" ]; then
        echo "Recent Lambda logs:"
        echo "${RECENT_LOGS}"
    else
        echo "No recent logs found"
    fi
else
    echo "No Lambda log streams found or logs not accessible"
fi

echo ""
echo "Cloud E2E testing completed"
echo ""
echo "Test Summary:"
echo "Input Stream: ${KINESIS_STREAM_INPUT}"
echo "Output Stream: ${KINESIS_STREAM_OUTPUT}"
echo "Test Ride ID: 156"
echo "Records Found: ${RECORD_COUNT:-0}"

if [ "${RECORD_COUNT:-0}" -gt "0" ]; then
    echo "Status: SUCCESS - End-to-end flow is working"
    exit 0
else
    echo "Status: WARNING - No output records found, check Lambda function and stream configuration"
    exit 1
fi
