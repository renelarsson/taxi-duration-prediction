"""
ModelService for streaming inference
Loads model and DictVectorizer from MLflow S3 artifacts
Includes KinesisCallback for streaming predictions
"""
import os
import json
import base64
import boto3
import mlflow
import pickle

def get_model_location(run_id):
    model_bucket = os.getenv('MODEL_BUCKET', 'mlflow-models-rll')
    experiment_id = os.getenv('MLFLOW_EXPERIMENT_ID', '1')
    return f's3://{model_bucket}/{experiment_id}/{run_id}/artifacts/model'

def get_dict_vectorizer_location(run_id):
    model_bucket = os.getenv('MODEL_BUCKET', 'mlflow-models-rll')
    experiment_id = os.getenv('MLFLOW_EXPERIMENT_ID', '1')
    return f's3://{model_bucket}/{experiment_id}/{run_id}/artifacts/dict_vectorizer.pkl'

def load_model(run_id):
    model_path = get_model_location(run_id)
    return mlflow.pyfunc.load_model(model_path)

def load_dict_vectorizer(run_id):
    dv_location = get_dict_vectorizer_location(run_id)
    parts = dv_location.replace("s3://", "").split("/", 1)
    bucket = parts[0]
    key = parts[1]
    s3 = boto3.client('s3', endpoint_url=os.getenv('MLFLOW_S3_ENDPOINT_URL'))
    obj = s3.get_object(Bucket=bucket, Key=key)
    dv = pickle.load(obj['Body'])
    return dv

def base64_decode(encoded_data):
    decoded_data = base64.b64decode(encoded_data).decode('utf-8')
    return json.loads(decoded_data)

class ModelService:
    def __init__(self, model, dict_vectorizer, model_version=None, callbacks=None):
        self.model = model
        self.dv = dict_vectorizer
        self.model_version = model_version
        self.callbacks = callbacks or []

    def prepare_features(self, ride):
        return {
            'PU_DO': f"{ride['PULocationID']}_{ride['DOLocationID']}",
            'trip_distance': ride['trip_distance'],
        }

    def predict(self, features):
        X = self.dv.transform([features])
        pred = self.model.predict(X)
        return float(pred[0])

    def lambda_handler(self, event):
        predictions_events = []
        for record in event['Records']:
            encoded_data = record['kinesis']['data']
            ride_event = base64_decode(encoded_data)
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
    Callback for sending predictions to Kinesis.
    """
    def __init__(self, kinesis_client, prediction_stream_name):
        self.kinesis_client = kinesis_client
        self.prediction_stream_name = prediction_stream_name

    def put_record(self, prediction_event):
        ride_id = prediction_event['prediction']['ride_id']
        self.kinesis_client.put_record(
            StreamName=self.prediction_stream_name,
            Data=json.dumps(prediction_event),
            PartitionKey=str(ride_id),
        )

def create_kinesis_client():
    endpoint_url = os.getenv('KINESIS_ENDPOINT_URL')
    if endpoint_url is None:
        return boto3.client('kinesis')
    return boto3.client('kinesis', endpoint_url=endpoint_url)

def init(prediction_stream_name: str, run_id: str, test_run: bool):
    model = load_model(run_id)
    dict_vectorizer = load_dict_vectorizer(run_id)
    callbacks = []
    if not test_run:
        kinesis_client = create_kinesis_client()
        kinesis_callback = KinesisCallback(kinesis_client, prediction_stream_name)
        callbacks.append(kinesis_callback.put_record)
    return ModelService(model, dict_vectorizer, model_version=run_id, callbacks=callbacks)