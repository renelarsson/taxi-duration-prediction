# terraform/lambda_function.py
import os
import terraform.model as model

PREDICTIONS_STREAM_NAME = os.getenv('PREDICTIONS_STREAM_NAME', 'ride_predictions')
RUN_ID = os.getenv('RUN_ID')
TEST_RUN = os.getenv('TEST_RUN', 'False') == 'True'

print("DEBUG RUN_ID:", RUN_ID)  # Line for debugging

model_service = model.init(
    prediction_stream_name=PREDICTIONS_STREAM_NAME,
    run_id=RUN_ID,
    test_run=TEST_RUN,
)

def lambda_handler(event, context):
    # pylint: disable=unused-argument
    return model_service.lambda_handler(event)
