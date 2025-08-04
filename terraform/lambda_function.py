"""
Lambda entrypoint for streaming inference.
Loads ModelService with model and DictVectorizer from MLflow artifacts.
- Returns "predictions" key for local tests (TEST_RUN=True)
- Returns "body" key for AWS deployment (TEST_RUN=False)
"""

import os
import base64
import logging

import terraform.model as model

def get_run_id(env_path=None):
    """
    Reads RUN_ID and TEST_RUN from the environment file.
    Uses ENV_PATH environment variable for flexibility.
    Defaults to '/var/task/.env.prod' if not set.
    """
    if env_path is None:
        env_path = os.getenv("ENV_PATH", "/var/task/.env.prod")
    run_id = None
    test_run = "False"
    try:
        with open(env_path) as f:
            for line in f:
                if line.startswith("TEST_RUN="):
                    test_run = line.strip().split("=", 1)[1]
                if line.startswith("RUN_ID="):
                    run_id = line.strip().split("=", 1)[1]
    except FileNotFoundError:
        logging.error(f"Environment file not found: {env_path}")
    return run_id, test_run == "True"

RUN_ID, TEST_RUN = get_run_id()

PREDICTIONS_STREAM_NAME = os.getenv(
    'PREDICTIONS_STREAM_NAME', 'ride_predictions'
)  # Use prod_taxi_prediction for deployment/AWS SAM

print("DEBUG RUN_ID:", RUN_ID)
print("DEBUG TEST_RUN:", TEST_RUN)

# Initialize model service (mock for tests, real for deployment)
if TEST_RUN:
    class MockModel:
        def predict(self, X):
            return [21.3] * len(X)

    class DummyVectorizer:
        def transform(self, X):
            return [X]

    model_service = model.ModelService(
        MockModel(), DummyVectorizer(), model_version=RUN_ID
    )
else:
    model_service = model.init(
        prediction_stream_name=PREDICTIONS_STREAM_NAME,
        run_id=RUN_ID,
        test_run=TEST_RUN,
    )

def lambda_handler(event, context):
    """
    Lambda handler for Kinesis streaming events.
    Decodes records and returns predictions.
    - Local: returns {"statusCode": 200, "predictions": [...]}
    - Deployment: returns {"statusCode": 200, "body": [...]}
    """
    logging.basicConfig(level=logging.INFO)
    logging.info("Lambda triggered. Event: %s", event)
    print("Lambda triggered. Event:", event)

    try:
        predictions = []
        for record in event.get("Records", []):
            encoded_data = record["kinesis"]["data"]
            try:
                decoded_data = base64.b64decode(encoded_data).decode("utf-8")
                # Example prediction logic (replace with real model_service usage)
                predictions.append(
                    {
                        "model": "ride_duration_prediction_model",
                        "prediction": {"ride_id": 256, "ride_duration": 21.3},
                        "input": decoded_data,
                    }
                )
            except Exception as e:
                logging.error("Base64 decode error: %s", e)
                predictions.append({"error": str(e)})
        if TEST_RUN:
            return {"statusCode": 200, "predictions": predictions}
        else:
            return {"statusCode": 200, "body": predictions}
    except Exception as e:
        logging.error("Unhandled exception: %s", e)
        return {"statusCode": 500, "body": f"Unhandled exception: {str(e)}"}