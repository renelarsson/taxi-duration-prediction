# src/deployment/lambda_handler.py 
# Lambda handler for deployment - organized structure version.
# Environment separation: Uses .env.dev for development (rll-models-dev), .env.prod for production (rll-models-prod)
# MODEL_BUCKET and related values are loaded from environment variables for flexibility.

import os
import json
import boto3
import base64
import sys
import logging
from typing import Dict, List, Any
from models.predict import predict_single_trip, load_model, load_preprocessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

class LambdaHandler:
    """
    Lambda deployment handler. Handles Kinesis events and model predictions.
    Uses environment variables for bucket and stream separation.
    """
    def __init__(self):
        """Initialize handler"""
        self.predictions_stream_name = os.getenv('PREDICTIONS_STREAM_NAME', 'ride_predictions')
        self.run_id = os.getenv('RUN_ID')
        self.test_run = os.getenv('TEST_RUN', 'False') == 'True'
        self.model_bucket = os.getenv('MODEL_BUCKET', 'rll-models-dev')

        self.kinesis_client = boto3.client('kinesis', endpoint_url=os.getenv('KINESIS_ENDPOINT_URL'))
        self.s3_client = boto3.client('s3', endpoint_url=os.getenv('MLFLOW_S3_ENDPOINT_URL'))
        
        self.model = None
        self.dv = None
        self._load_model_artifacts()

        logger.info(f"LambdaHandler initialized - test_run: {self.test_run}, model_bucket: {self.model_bucket}")

    def _load_model_artifacts(self):
        """Load model and preprocessor"""
        try:
            if self.run_id:
                import mlflow
                logged_model = f's3://{self.model_bucket}/1/{self.run_id}/artifacts/model'
                s3_endpoint = os.getenv("MLFLOW_S3_ENDPOINT_URL")
                if s3_endpoint:
                    os.environ["MLFLOW_S3_ENDPOINT_URL"] = s3_endpoint
                self.model = mlflow.pyfunc.load_model(logged_model)
                logger.info(f"Loaded MLflow model from {logged_model}")

                # Preprocessor loading: Try local first, then S3 if not found
                dv_local_path = 'models/dv.bin'
                if os.path.exists(dv_local_path):
                    self.dv = load_preprocessor(dv_local_path)
                    logger.info(f"Loaded preprocessor from {dv_local_path}")
                else:
                    # Try to download from S3
                    s3_key = f"1/{self.run_id}/artifacts/models/dv.bin"
                    try:
                        os.makedirs('models', exist_ok=True)
                        self.s3_client.download_file(self.model_bucket, s3_key, dv_local_path)
                        self.dv = load_preprocessor(dv_local_path)
                        logger.info(f"Downloaded and loaded preprocessor from S3: {s3_key}")
                    except Exception as e:
                        logger.warning(f"Could not load preprocessor from S3 ({s3_key}): {e}")
                        self.dv = None
            else:
                self.model = load_model('models/model.bin')
                self.dv = load_preprocessor('models/dv.bin')
                logger.info("Loaded local model artifacts")

        except Exception as e:
            logger.error(f"Failed to load model artifacts: {e}")
            self.model = None
            self.dv = None

    def prepare_features(self, ride: Dict[str, Any]) -> Dict[str, Any]:
        features = {}
        features['PU_DO'] = f"{ride['PULocationID']}_{ride['DOLocationID']}"
        features['trip_distance'] = ride['trip_distance']
        features['PULocationID'] = ride['PULocationID']
        features['DOLocationID'] = ride['DOLocationID']
        return features

    def predict(self, features: Dict[str, Any]) -> float:
        if self.model is None:
            logger.warning("No model available for prediction")
            return 10.0

        try:
            if hasattr(self.model, 'predict'):
                import pandas as pd
                df = pd.DataFrame([features])
                pred = self.model.predict(df)
                return float(pred[0])
            elif self.dv is not None:
                prediction = predict_single_trip(features, self.model, self.dv)
                return float(prediction)
            else:
                logger.error("No valid prediction method available")
                return 10.0

        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return 10.0

    def process_kinesis_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        encoded_data = record['kinesis']['data']
        decoded_data = base64.b64decode(encoded_data).decode('utf-8')
        ride_event = json.loads(decoded_data)
        ride = ride_event['ride']
        ride_id = ride_event['ride_id']
        features = self.prepare_features(ride)
        prediction = self.predict(features)
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
        logger.info(f"Processing {len(event.get('Records', []))} records")
        predictions_events = []
        for record in event.get('Records', []):
            try:
                prediction_event = self.process_kinesis_record(record)
                ride_id = prediction_event['prediction']['ride_id']
                self.send_prediction(prediction_event, ride_id)
                predictions_events.append(prediction_event)
            except Exception as e:
                logger.error(f"Failed to process record: {e}")
                continue
        return {
            'predictions': predictions_events
        }

lambda_handler_instance = None

def get_handler():
    global lambda_handler_instance
    if lambda_handler_instance is None:
        lambda_handler_instance = LambdaHandler()
    return lambda_handler_instance

def lambda_handler(event, context):
    handler = get_handler()
    return handler.lambda_handler(event, context)

if __name__ == "__main__":
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
    os.environ['TEST_RUN'] = 'True'
    os.environ['MODEL_BUCKET'] = 'rll-models-dev'
    os.environ['RUN_ID'] = 'a986756f70a240cf8808a59ed77ba2d3'
    result = lambda_handler(test_event, None)