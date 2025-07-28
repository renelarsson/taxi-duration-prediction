"""
Integration test for Kinesis stream in LocalStack.
Puts a test record to the stream and verifies it can be read back.
"""

import os
import json
import time

import boto3

# Load Kinesis endpoint and stream name from environment or defaults
KINESIS_ENDPOINT_URL = os.getenv('KINESIS_ENDPOINT_URL', 'http://localhost:4566')
STREAM_NAME = os.getenv('PREDICTIONS_STREAM_NAME', 'stg_taxi_predictions')
REGION_NAME = os.getenv('AWS_REGION', 'eu-north-1')

# Create Kinesis client for LocalStack
kinesis_client = boto3.client(
    'kinesis',
    endpoint_url=KINESIS_ENDPOINT_URL,
    region_name=REGION_NAME,
    aws_access_key_id='test',
    aws_secret_access_key='test',
)

# Put a test record to the stream
test_data = {
    "ride_id": 256,
    "prediction": 21.3,
    "model": "ride_duration_prediction_model",
}
response = kinesis_client.put_record(
    StreamName=STREAM_NAME, Data=json.dumps(test_data), PartitionKey="test"
)
print(f"Put record response: {response}")

# Wait for the record to be available
time.sleep(2)

# Get shard iterator
desc = kinesis_client.describe_stream(StreamName=STREAM_NAME)
shard_id = desc['StreamDescription']['Shards'][0]['ShardId']
shard_iterator = kinesis_client.get_shard_iterator(
    StreamName=STREAM_NAME, ShardId=shard_id, ShardIteratorType='TRIM_HORIZON'
)['ShardIterator']

# Read records from the stream
records_response = kinesis_client.get_records(ShardIterator=shard_iterator, Limit=10)
records = records_response['Records']
print(f"Records read from stream: {records}")

# Assert at least one record is present and matches test data
assert len(records) > 0
record_data = json.loads(records[0]['Data'])
assert record_data['ride_id'] == 256
assert abs(record_data['prediction'] - 21.3) < 1.0
assert record_data['model'] == "ride_duration_prediction_model"
