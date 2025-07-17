# src/deployment/lambda_handler.py 
# Lambda handler for deployment - organized structure version.
# Environment separation: Uses .env.dev for development (mlflow-models-rll), .env.prod for production (mlflow-models-rll-mlops-capstone)
# MODEL_BUCKET and related values are loaded from environment variables for flexibility.

import os
import json
import boto3
import base64
import sys
import logging
from typing import Dict, List, Any
from models.predict import predict_single_trip, load_model, load_preprocessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add src to path ('/src/deployment/lambda_handler.py')
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

class LambdaHandler:
    """
    Lambda deployment handler. Handles Kinesis events and model predictions.
    Uses environment variables for bucket and stream separation.
    """
    def __init__(self):
        """Initialize handler"""
        # Environment variables for dev/prod separation
        self.predictions_stream_name = os.getenv('PREDICTIONS_STREAM_NAME', 'ride_predictions')
        self.run_id = os.getenv('RUN_ID')
        self.test_run = os.getenv('TEST_RUN', 'False') == 'True'
        self.model_bucket = os.getenv('MODEL_BUCKET', 'mlflow-models-rll')  # .env.dev for dev, .env.prod for prod

        # Initialize AWS clients
        self.kinesis_client = boto3.client('kinesis')

        # Load model and preprocessor
        self.model = None
        self.dv = None
        self._load_model_artifacts()

        logger.info(f"LambdaHandler initialized - test_run: {self.test_run}, model_bucket: {self.model_bucket}")

    def _load_model_artifacts(self):
        """Load model and preprocessor"""
        try:
            if self.run_id:
                # MLflow loading
                import mlflow
                logged_model = f's3://{self.model_bucket}/1/{self.run_id}/artifacts/model'
                # Set MLflow S3 endpoint if provided
                s3_endpoint = os.getenv("MLFLOW_S3_ENDPOINT_URL")
                if s3_endpoint:
                    os.environ["MLFLOW_S3_ENDPOINT_URL"] = s3_endpoint
                self.model = mlflow.pyfunc.load_model(logged_model)
                logger.info(f"Loaded MLflow model from {logged_model}")

                # Load preprocessor (assuming it's saved with model)
                try:
                    self.dv = load_preprocessor('models/dv.bin')
                except Exception as e:
                    logger.warning(f"Could not load preprocessor from models/dv.bin: {e}")
            else:
                # Fallback: load local artifacts
                self.model = load_model('models/model.bin')
                self.dv = load_preprocessor('models/dv.bin')
                logger.info("Loaded local model artifacts")

        except Exception as e:
            logger.error(f"Failed to load model artifacts: {e}")
            self.model = None
            self.dv = None

    def prepare_features(self, ride: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare features from ride data.
        Args:
            ride: Ride event dictionary
        Returns:
            Feature dictionary
        """
        features = {}
        features['PU_DO'] = f"{ride['PULocationID']}_{ride['DOLocationID']}"
        features['trip_distance'] = ride['trip_distance']
        features['PULocationID'] = ride['PULocationID']
        features['DOLocationID'] = ride['DOLocationID']
        return features

    def predict(self, features: Dict[str, Any]) -> float:
        """
        Args:
            features: Feature dictionary
        Returns:
            Prediction value
        """
        if self.model is None:
            logger.warning("No model available for prediction")
            return 10.0  # Default duration

        try:
            if hasattr(self.model, 'predict'):
                # MLflow model
                import pandas as pd
                df = pd.DataFrame([features])
                pred = self.model.predict(df)
                return float(pred[0])
            elif self.dv is not None:
                # Use 'organized' predict module
                prediction = predict_single_trip(features, self.model, self.dv)
                return float(prediction)
            else:
                logger.error("No valid prediction method available")
                return 10.0

        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return 10.0  # Fallback prediction

    def process_kinesis_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process single Kinesis record.
        Args:
            record: Kinesis record
        Returns:
            Prediction event
        """
        # Kinesis decoding
        encoded_data = record['kinesis']['data']
        decoded_data = base64.b64decode(encoded_data).decode('utf-8')
        ride_event = json.loads(decoded_data)

        # Extract ride data
        ride = ride_event['ride']
        ride_id = ride_event['ride_id']

        # Prepare features and predict
        features = self.prepare_features(ride)
        prediction = self.predict(features)

        # Prediction event format
        prediction_event = {
            'model': 'taxi_duration_prediction_model',
            'version': 'organized-v1',
            'prediction': {
                'ride_duration': prediction,
                'ride_id': ride_id
            }
        }

        return prediction_event

    def send_prediction(self, prediction_event: Dict[str, Any], ride_id: str):
        """
        Send prediction to Kinesis.
        Args:
            prediction_event: Prediction event
            ride_id: Ride ID for partitioning
        """
        if not self.test_run:
            try:
                self.kinesis_client.put_record(
                    StreamName=self.predictions_stream_name,
                    Data=json.dumps(prediction_event),
                    PartitionKey=str(ride_id)
                )
                logger.info(f"Sent prediction for ride {ride_id}")
            except Exception as e:
                logger.error(f"Failed to send prediction: {e}")
        else:
            logger.info(f"TEST_RUN: Would send prediction for ride {ride_id}")

    def lambda_handler(self, event: Dict[str, Any], context=None) -> Dict[str, Any]:
        """
        Main Lambda handler - Instance method (does the actual work): Process records, make predictions, etc.
        Args:
            event: Lambda event (Kinesis records)
            context: Lambda context
        Returns:
            Response with predictions
        """
        logger.info(f"Processing {len(event.get('Records', []))} records")

        predictions_events = []

        for record in event.get('Records', []):
            try:
                # Process record
                prediction_event = self.process_kinesis_record(record)
                ride_id = prediction_event['prediction']['ride_id']

                # Send to output stream
                self.send_prediction(prediction_event, ride_id)

                # Collect response
                predictions_events.append(prediction_event)

            except Exception as e:
                logger.error(f"Failed to process record: {e}")
                continue

        return {
            'predictions': predictions_events
        }

# Global handler instance
lambda_handler_instance = None

def get_handler():
    """Get or create handler instance - singleton pattern (Loads model once and reuses)."""
    global lambda_handler_instance
    if lambda_handler_instance is None:
        lambda_handler_instance = LambdaHandler()
    return lambda_handler_instance

def lambda_handler(event, context):
    """
    AWS Lambda entry point (required by AWS).
    Args:
        event: Lambda event
        context: Lambda context
    Returns:
        Handler response
    """
    handler = get_handler()
    return handler.lambda_handler(event, context)

# For local testing
if __name__ == "__main__":
    # Test event structure
    test_event = {
        'Records': [{
            'kinesis': {
                'data': base64.b64encode(json.dumps({
                    'ride': {
                        'PULocationID': 161,
                        'DOLocationID': 236,
                        'trip_distance': 3.5
                    },
                    'ride_id': 'test_ride_123'
                }).encode()).decode()
            }
        }]
    }

    # Set environment for local test
    os.environ['TEST_RUN'] = 'True'
    os.environ['MODEL_BUCKET'] = 'mlflow-models-rll'  # Only for local testing
    os.environ['RUN_ID'] = 'a986756f70a240cf8808a59ed77ba2d3'

    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))