# integration-test/test_docker.py
# This script tests the Docker setup for the taxi duration prediction model.
# It sends a test event to the Kinesis stream and checks the response from the Lambda function
# to ensure the prediction is as expected.
# Environment separation: Uses .env.dev for development, .env.prod for production.
# All endpoint, bucket, and related values are loaded from environment variables for flexibility.

# pylint: disable=duplicate-code
import os
import json
import requests
from deepdiff import DeepDiff

# Load endpoint from environment variable, fallback to local default
LAMBDA_ENDPOINT = os.getenv('LAMBDA_ENDPOINT', 'http://localhost:8080/2015-03-31/functions/function/invocations')

# If you need to pass bucket, stream, or run_id, load them from environment as well
MODEL_BUCKET = os.getenv('MODEL_BUCKET', 'rll-models-dev')
RUN_ID = os.getenv('RUN_ID', 'Test123')

with open('event.json', 'rt', encoding='utf-8') as f_in:
    event = json.load(f_in)

actual_response = requests.post(LAMBDA_ENDPOINT, json=event).json()
print('actual response:')
print(json.dumps(actual_response, indent=2))

expected_response = {
    'predictions': [
        {
            'model': 'ride_duration_prediction_model',
            'version': RUN_ID,
            'prediction': {
                'ride_duration': 21.3,
                'ride_id': 256,
            },
        }
    ]
}

diff = DeepDiff(actual_response, expected_response, significant_digits=1)
print(f'diff={diff}')

assert 'type_changes' not in diff
assert 'values_changed' not in diff