# terraform/model.py
# Model service for taxi trip duration prediction
# Uses environment separation: .env.dev for development, .env.prod for production
# MODEL_BUCKET and related values are loaded from environment variables

import os
import json
import base64
import boto3
import mlflow

def get_model_location(run_id):
    """
    Returns the S3 location for the MLflow model.
    Uses MODEL_BUCKET from environment (.env.dev for dev, .env.prod for prod).
    """
    model_location = os.getenv('MODEL_LOCATION')
    if model_location is not None:
        return model_location

    model_bucket = os.getenv('MODEL_BUCKET', 'mlflow-models-rll')# The correct value will be loaded from environment variables
    experiment_id = os.getenv('MLFLOW_EXPERIMENT_ID', '1')
    model_location = f's3://{model_bucket}/{experiment_id}/{run_id}/artifacts/model'
    return model_location

def load_model(run_id):
    """
    Loads the MLflow model from the specified S3 location.
    """
    model_path = get_model_location(run_id)
    model = mlflow.pyfunc.load_model(model_path)
    return model

def base64_decode(encoded_data):
    """
    Decodes base64-encoded Kinesis data to a ride event dict.
    """
    decoded_data = base64.b64decode(encoded_data).decode('utf-8')
    ride_event = json.loads(decoded_data)
    return ride_event

class ModelService:
    """
    Service for model inference and Kinesis integration.
    """
    def __init__(self, model, model_version=None, callbacks=None):
        self.model = model
        self.model_version = model_version
        self.callbacks = callbacks or []

    def prepare_features(self, ride):
        features = {}
        features['PU_DO'] = f"{ride['PULocationID']}_{ride['DOLocationID']}"
        features['trip_distance'] = ride['trip_distance']
        return features

    def predict(self, features): # Real-time inference
        pred = self.model.predict(features)
        return float(pred[0])

    def lambda_handler(self, event): # AWS Lambda integration
        # print(json.dumps(event))
        predictions_events = []
        for record in event['Records']:
            encoded_data = record['kinesis']['data']
            ride_event = base64_decode(encoded_data)
            # print(ride_event)
            ride = ride_event['ride']
            ride_id = ride_event['ride_id']

            features = self.prepare_features(ride)
            prediction = self.predict(features)

            prediction_event = {
                'model': 'ride_duration_prediction_model',
                'version': self.model_version,
                'prediction': {'ride_duration': prediction, 'ride_id': ride_id},
            }

            for callback in self.callbacks:
                callback(prediction_event)

            predictions_events.append(prediction_event)

        return {'predictions': predictions_events}

class KinesisCallback:
    """
    Callback for streaming predictions to Kinesis.
    """
    def __init__(self, kinesis_client, prediction_stream_name):
        self.kinesis_client = kinesis_client
        self.prediction_stream_name = prediction_stream_name

    def put_record(self, prediction_event): # Producer SENDS data TO streams
        ride_id = prediction_event['prediction']['ride_id']
        self.kinesis_client.put_record(
            StreamName=self.prediction_stream_name,
            Data=json.dumps(prediction_event),
            PartitionKey=str(ride_id),
        )

def create_kinesis_client():
    """
    Creates a Kinesis client using the endpoint from environment (.env.dev/.env.prod).
    """
    endpoint_url = os.getenv('KINESIS_ENDPOINT_URL')
    if endpoint_url is None:
        return boto3.client('kinesis') 
    return boto3.client('kinesis', endpoint_url=endpoint_url) 

def init(prediction_stream_name: str, run_id: str, test_run: bool):
    """
    Initializes the ModelService with the correct model and Kinesis callback.
    Uses environment separation for dev/prod.
    """
    model = load_model(run_id) # Load trained model from S3/MLflow
    callbacks = []
    if not test_run:
        kinesis_client = create_kinesis_client()
        # Stream predictions to output	
        kinesis_callback = KinesisCallback(kinesis_client, prediction_stream_name)
        callbacks.append(kinesis_callback.put_record)
    model_service = ModelService(model=model, model_version=run_id, callbacks=callbacks)
    return