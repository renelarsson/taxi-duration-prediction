"""
Lambda entrypoint for streaming inference.
Loads ModelService with model and DictVectorizer from MLflow artifacts.
"""
import os
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

PREDICTIONS_STREAM_NAME = os.getenv('PREDICTIONS_STREAM_NAME', 'ride_predictions')

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
    return model_service.lambda_handler(event)