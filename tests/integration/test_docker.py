"""
Integration test for the Docker backend of the taxi duration prediction model.
This test sends a sample event to the backend and checks the response format and prediction values.
It is designed to work with LocalStack and the local Docker setup.
"""

import os
import json

import requests

# Load endpoint from environment variable, fallback to local default 
LAMBDA_ENDPOINT = os.getenv(
    'LAMBDA_ENDPOINT', 'http://localhost:8080/2015-03-31/functions/function/invocations'
)

# Load the test event (event.json must be available in the working directory)
with open('integration-test/event.json', 'rt', encoding='utf-8') as f_in:
    event = json.load(f_in)

# Send the event to the backend and get the response
actual_response = requests.post(LAMBDA_ENDPOINT, json=event).json()
print('actual response:')
print(json.dumps(actual_response, indent=2))

# Check response structure and prediction values
assert 'predictions' in actual_response
assert isinstance(actual_response['predictions'], list)
assert len(actual_response['predictions']) > 0

prediction = actual_response['predictions'][0]
assert prediction['model'] == 'ride_duration_prediction_model'
assert prediction['prediction']['ride_id'] == 256
assert (
    abs(prediction['prediction']['ride_duration'] - 21.3) < 1.0
)  # Allow small tolerance

# Optionally print version for debugging
print(f"Model version in response: {prediction.get('version')}")
