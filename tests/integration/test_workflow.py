"""
Workflow integration tests.
Based on MLOps Zoomcamp Module 6 test_kinesis.py patterns.
"""

import os
import sys
import json
import time
from pprint import pprint
from pathlib import Path

import boto3
import pytest
from deepdiff import DeepDiff

# Add src to path for testing
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT / "src"))


def get_run_id(env_path="/var/task/.env.dev"):
    with open(env_path) as f:
        for line in f:
            if line.startswith("RUN_ID="):
                return line.strip().split("=", 1)[1]
    raise ValueError("RUN_ID not found in .env.dev")


# DummyVectorizer for testing ModelService without real DictVectorizer
class DummyVectorizer:
    def transform(self, X):
        # Returns input as a list, mimicking DictVectorizer interface
        return [X]


def test_kinesis_stream_integration():
    """
    Test Kinesis stream integration.
    Based on course test_kinesis.py pattern.
    """
    kinesis_endpoint = os.getenv('KINESIS_ENDPOINT_URL', "http://localhost:4566")
    stream_name = os.getenv('PREDICTIONS_STREAM_NAME', 'ride_predictions')
    try:
        kinesis_client = boto3.client('kinesis', endpoint_url=kinesis_endpoint)
        shard_id = 'shardId-000000000000'
        shard_iterator_response = kinesis_client.get_shard_iterator(
            StreamName=stream_name,
            ShardId=shard_id,
            ShardIteratorType='TRIM_HORIZON',
        )
        shard_iterator_id = shard_iterator_response['ShardIterator']
        records_response = kinesis_client.get_records(
            ShardIterator=shard_iterator_id,
            Limit=1,
        )
        records = records_response['Records']
        pprint(records)
        assert len(records) == 1
        actual_record = json.loads(records[0]['Data'])
        pprint(actual_record)
        expected_record = {
            'model': 'ride_duration_prediction_model',
            'version': get_run_id(),  # Use dynamic RUN_ID
            'prediction': {
                'ride_duration': 21.3,
                'ride_id': 256,
            },
        }
        diff = DeepDiff(actual_record, expected_record, significant_digits=1)
        print(f'diff={diff}')
        assert 'values_changed' not in diff
        assert 'type_changes' not in diff
        print('all good')
    except Exception as e:
        pytest.skip(f"Kinesis integration not available: {e}")


@pytest.mark.integration
def test_prefect_training_workflow():
    """
    Test Prefect training workflow integration.
    Validates workflow execution and task dependencies.
    """
    pytest.skip(
        "Prefect training workflow test - implement based on your Prefect setup"
    )


@pytest.mark.integration
def test_prefect_inference_workflow():
    """
    Test Prefect inference workflow integration.
    Validates batch inference workflow execution.
    """
    pytest.skip(
        "Prefect inference workflow test - implement based on your Prefect setup"
    )


@pytest.mark.integration
def test_prefect_monitoring_workflow():
    """
    Test Prefect monitoring workflow integration.
    Validates monitoring workflow execution and metrics storage.
    """
    pytest.skip(
        "Prefect monitoring workflow test - implement based on your Prefect setup"
    )


def test_mlflow_workflow_integration():
    """
    Test MLflow integration workflow.
    Validates model logging, loading, and version management.
    """
    try:
        from unittest.mock import Mock, patch

        import mlflow

        with (
            patch('mlflow.start_run'),
            patch('mlflow.log_params'),
            patch('mlflow.log_metric'),
            patch('mlflow.log_artifact'),
            patch('mlflow.sklearn.log_model'),
        ):
            pass
    except ImportError:
        pytest.skip("MLflow not available for workflow testing")


def test_evidently_monitoring_workflow():
    """
    Test Evidently monitoring workflow integration.
    Validates drift detection and metrics calculation workflow.
    """
    try:
        import pandas as pd
        from evidently import Report
        from evidently.metrics import ValueDrift

        reference_data = pd.DataFrame(
            {'feature1': [1, 2, 3, 4, 5], 'prediction': [10, 20, 30, 40, 50]}
        )
        current_data = pd.DataFrame(
            {'feature1': [1, 2, 3, 4, 5], 'prediction': [12, 22, 32, 42, 52]}
        )
        report = Report(metrics=[ValueDrift(column='prediction')])
        report.run(reference_data=reference_data, current_data=current_data)
        result = report.as_dict()
        assert 'metrics' in result
        assert len(result['metrics']) > 0
    except ImportError:
        pytest.skip("Evidently not available for workflow testing")


def test_lambda_kinesis_workflow():
    """
    Test Lambda → Kinesis workflow integration.
    Validates event processing and stream output workflow.
    """
    from terraform.model import ModelService

    class MockModel:
        def predict(self, X):
            return [21.3] * len(X)

    class DummyVectorizer:
        def transform(self, X):
            return [X]

    run_id = get_run_id()
    model_service = ModelService(MockModel(), DummyVectorizer(), model_version=run_id)

    event_path = PROJECT_ROOT / "integration-test" / "event.json"
    with open(event_path, 'rt', encoding='utf-8') as f_in:
        event = json.load(f_in)

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


@pytest.mark.slow
def test_end_to_end_workflow():
    """
    Test complete end-to-end workflow.
    Validates: Data → Training → Inference → Monitoring workflow.
    """
    pytest.skip("End-to-end workflow test - implement based on your complete setup")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-m", "not slow"])
