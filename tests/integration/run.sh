# integration-test/run.sh
# This script sets up the local environment for testing the taxi duration prediction model.
# It builds the Docker image, starts the necessary services, and runs integration tests.
# Environment separation: Uses .env.dev for development, .env.prod for production.
# All stream names, bucket names, and related values are loaded from environment variables for flexibility.
# Ensure you have Docker and AWS CLI installed and configured for local testing.

#!/usr/bin/env bash

# Load environment variables from .env (which should be .env.dev or .env.prod)
if [ -f ../.env ]; then
    export $(grep -v '^#' ../.env | xargs)
fi

if [[ -z "${GITHUB_ACTIONS}" ]]; then
  cd "$(dirname "$0")"
fi

if [ -z "${LOCAL_IMAGE_NAME}" ]; then
    LOCAL_TAG=$(date +"%Y-%m-%d-%H-%M")
    export LOCAL_IMAGE_NAME="stream-model-duration:${LOCAL_TAG}"
    echo "LOCAL_IMAGE_NAME is not set, building a new image with tag ${LOCAL_IMAGE_NAME}"
    docker build -t ${LOCAL_IMAGE_NAME} ..
else
    echo "no need to build image ${LOCAL_IMAGE_NAME}"
fi

# Use stream name from environment, fallback to default
export PREDICTIONS_STREAM_NAME="${PREDICTIONS_STREAM_NAME:-ride_predictions}"

docker-compose up -d

sleep 5

aws --endpoint-url=http://localhost:4566 \
    kinesis create-stream \
    --stream-name "${PREDICTIONS_STREAM_NAME}" \
    --shard-count 1

python test_docker.py

ERROR_CODE=$?

if [ ${ERROR_CODE} != 0 ]; then
    docker-compose logs
    docker-compose down
    exit ${ERROR_CODE}
fi

python test_kinesis.py

ERROR_CODE=$?

if [ ${ERROR_CODE} != 0 ]; then
    docker-compose logs
    docker-compose down
    exit ${ERROR_CODE}
fi

docker-compose down
