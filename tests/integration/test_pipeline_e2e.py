"""
End-to-end pipeline integration tests.
Based on MLOps Zoomcamp Module 6 integration testing patterns.
"""
import json
import os
import sys
import time
import pytest
import requests
from deepdiff import DeepDiff
from pathlib import Path

# Add src to path for testing
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT / "src"))

def load_test_event():
    """Load test event from integration-test directory"""
    event_path = PROJECT_ROOT / "integration-test" / "event.json"
    with open(event_path, 'rt', encoding='utf-8') as f_in:
        return json.load(f_in)

def test_lambda_docker_integration():
    """
    Test containerized Lambda function via HTTP endpoint.
    Based on course test_docker.py pattern.
    """
    # Load test event
    event = load_test_event()
    
    # Lambda container endpoint (matches course docker-compose setup)
    url = 'http://localhost:8080/2015-03-31/functions/function/invocations'
    
    try:
        # Make request to containerized Lambda
        response = requests.post(url, json=event, timeout=30)
        actual_response = response.json()
        
        print('actual response:')
        print(json.dumps(actual_response, indent=2))
        
        # Expected response structure (adapted for taxi duration)
        expected_response = {
            'predictions': [
                {
                    'model': 'ride_duration_prediction_model',
                    'version': 'Test123',
                    'prediction': {
                        'ride_duration': 21.3,  # Expected from course test data
                        'ride_id': 256,
                    },
                }
            ]
        }
        
        # Use DeepDiff for flexible comparison (course pattern)
        diff = DeepDiff(actual_response, expected_response, significant_digits=1)
        print(f'diff={diff}')
        
        # Assertions matching course pattern
        assert 'type_changes' not in diff
        assert 'values_changed' not in diff
        
    except requests.exceptions.RequestException as e:
        pytest.skip(f"Lambda container not available: {e}")

def test_training_pipeline_e2e():
    """
    Test complete training pipeline end-to-end.
    Validates data flow: extract → preprocess → train → evaluate
    """
    # Test training workflow and skip if dependencies are not available
    pytest.skip("Training pipeline E2E test - implement based on training setup")

def test_inference_pipeline_e2e():
    """
    Test complete inference pipeline end-to-end.
    Validates data flow: load model → process batch → generate predictions
    """
    # Test inference workflow and skip if dependencies not available  
    pytest.skip("Inference pipeline E2E test - implement based on inference setup")

def test_monitoring_pipeline_e2e():
    """
    Test complete monitoring pipeline end-to-end.
    Validates data flow: load data → calculate metrics → store results → check alerts
    """
    # Test monitoring workflow and skip if dependencies not available
    pytest.skip("Monitoring pipeline E2E test - implement based on monitoring setup")

# Tag tests for selective execution (eg. pytest -m integration # Run only integration tests)
@pytest.mark.integration
def test_model_service_integration():
    """
    Test model service integration without external dependencies.
    Tests the core model logic with realistic data.
    """
    from model import ModelService
    
    # Mock model for integration testing (course pattern)
    class MockModel:
        def predict(self, X):
            # Return realistic taxi duration prediction
            return [21.3] * len(X)
    
    # Test model service integration
    model_service = ModelService(MockModel(), version='Test123')
    
    # Test data (from course event.json)
    ride_data = {
        "PULocationID": 130,
        "DOLocationID": 205,
        "trip_distance": 3.66,
    }
    
    # Test feature preparation
    features = model_service.prepare_features(ride_data)
    expected_features = {
        "PU_DO": "130_205",
        "trip_distance": 3.66,
    }
    
    assert features == expected_features
    
    # Test prediction
    prediction = model_service.predict(features)
    assert prediction == 21.3
    
    # Test event processing (course pattern)
    event = load_test_event()
    result = model_service.lambda_handler(event)
    
    expected_result = {
        'predictions': [
            {
                'model': 'ride_duration_prediction_model',
                'version': 'Test123',
                'prediction': {
                    'ride_duration': 21.3,
                    'ride_id': 256,
                },
            }
        ]
    }
    
    # Use DeepDiff for comparison (course pattern)
    diff = DeepDiff(result, expected_result, significant_digits=1)
    assert 'type_changes' not in diff
    assert 'values_changed' not in diff

def test_data_pipeline_integration():
    """
    Test data processing pipeline integration.
    Validates extract → preprocess flow.
    """
    # Skip if data dependencies not available
    pytest.skip("Data pipeline integration test - implement based on your data setup")

if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "-s"])
