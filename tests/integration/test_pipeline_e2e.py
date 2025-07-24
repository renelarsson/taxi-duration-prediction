"""
End-to-end pipeline integration tests for streaming inference.
"""
import sys
import json
import pytest
import requests
from deepdiff import DeepDiff
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT / "src"))

def get_run_id(env_path="/var/task/.env.dev"):
    with open(env_path) as f:
        for line in f:
            if line.startswith("RUN_ID="):
                return line.strip().split("=", 1)[1]
    raise ValueError("RUN_ID not found in .env.dev")

def load_test_event():
    event_path = PROJECT_ROOT / "integration-test" / "event.json"
    with open(event_path, 'rt', encoding='utf-8') as f_in:
        return json.load(f_in)

def test_lambda_docker_integration():
    event = load_test_event()
    url = 'http://localhost:8080/2015-03-31/functions/function/invocations'
    run_id = get_run_id()
    try:
        response = requests.post(url, json=event, timeout=30)
        actual_response = response.json()
        print('actual response:')
        print(json.dumps(actual_response, indent=2))
        expected_response = {
            'predictions': [
                {
                    'model': 'ride_duration_prediction_model',
                    'version': run_id,  # Use dynamic RUN_ID
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
    except requests.exceptions.RequestException as e:
        pytest.skip(f"Lambda container not available: {e}")

@pytest.mark.integration
def test_model_service_integration():
    from terraform.model import ModelService
    class MockModel:
        def predict(self, X):
            return [21.3] * len(X)
    class DummyVectorizer:
        def transform(self, X):
            return [X]
    run_id = get_run_id()
    model_service = ModelService(MockModel(), DummyVectorizer(), model_version=run_id)
    ride_data = {
        "PULocationID": 130,
        "DOLocationID": 205,
        "trip_distance": 3.66,
    }
    features = model_service.prepare_features(ride_data)
    expected_features = {
        "PU_DO": "130_205",
        "trip_distance": 3.66,
    }
    assert features == expected_features
    prediction = model_service.predict(features)
    assert prediction == 21.3
    event = load_test_event()
    result = model_service.lambda_handler(event)
    expected_result = {
        'predictions': [
            {
                'model': 'ride_duration_prediction_model',
                'version': run_id,  # Use dynamic RUN_ID
                'prediction': {
                    'ride_duration': 21.3,
                    'ride_id': 256,
                },
            }
        ]
    }
    diff = DeepDiff(result, expected_result, significant_digits=1)
    assert 'type_changes' not in diff
    assert 'values_changed' not in diff