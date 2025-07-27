"""
Lambda entrypoint for streaming inference.
Loads ModelService with model and DictVectorizer from MLflow artifacts.
"""
import os
import base64
import logging
import terraform.model as model

def get_run_id(env_path="/var/task/.env.dev"):
    with open(env_path) as f:
        for line in f:
            if line.startswith("TEST_RUN="):
                test_run = line.strip().split("=", 1)[1]
            if line.startswith("RUN_ID="):
                run_id = line.strip().split("=", 1)[1]
    return run_id, test_run == "True"

RUN_ID, TEST_RUN = get_run_id()

PREDICTIONS_STREAM_NAME = os.getenv('PREDICTIONS_STREAM_NAME', 'ride_predictions') # Use 'prod_taxi_predictions' in AWS CLI for LocalStack

print("DEBUG RUN_ID:", RUN_ID)
print("DEBUG TEST_RUN:", TEST_RUN)

if TEST_RUN:
    class MockModel:
        def predict(self, X):
            return [21.3] * len(X)
    class DummyVectorizer:
        def transform(self, X):
            return [X]
    model_service = model.ModelService(MockModel(), DummyVectorizer(), model_version=RUN_ID)
else:
    model_service = model.init(
        prediction_stream_name=PREDICTIONS_STREAM_NAME,
        run_id=RUN_ID,
        test_run=TEST_RUN,
    )

def lambda_handler(event, context):
    print("EVENT RECEIVED:", event)
    try:
        logging.info("Received event: %s", event)
        results = []
        for record in event["Records"]:
            encoded_data = record["kinesis"]["data"]
            try:
                decoded_data = base64.b64decode(encoded_data).decode("utf-8")
                results.append(decoded_data)
            except Exception as e:
                logging.error("Base64 decode error: %s", e)
                results.append(f"Base64 decode error: {str(e)}")
        return {
            "statusCode": 200,
            "body": results
        }
    except Exception as e:
        logging.error("Unhandled exception: %s", e)
        return {
            "statusCode": 500,
            "body": f"Unhandled exception: {str(e)}"
        }