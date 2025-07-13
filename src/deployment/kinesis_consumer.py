"""
Simple Kinesis consumer for streaming - adapted for real-time consumption.
"""
import os
import json
import boto3
import time
import logging
import sys
from typing import Dict, Any

# Add src to path for ‘organized’ imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s")
logger = logging.getLogger(__name__)

# Configure stream
KINESIS_ENDPOINT = os.getenv('KINESIS_ENDPOINT_URL', "http://localhost:4566")
INPUT_STREAM_NAME = os.getenv('INPUT_STREAM_NAME', 'ride-events')
OUTPUT_STREAM_NAME = os.getenv('OUTPUT_STREAM_NAME', 'ride_predictions')
TEST_RUN = os.getenv('TEST_RUN', 'False') == 'True'

# AWS client setup
kinesis_client = boto3.client('kinesis', endpoint_url=KINESIS_ENDPOINT)

def prepare_features(ride):
    """Prepare features"""
    features = {}
    features['PU_DO'] = '%s_%s' % (ride['PULocationID'], ride['DOLocationID'])
    features['trip_distance'] = ride['trip_distance']
    return features

def predict(features):
    """Simple prediction - fallback."""
    # Simple heuristic when no model
    distance = features.get('trip_distance', 1.0)
    return max(1.0, distance * 3.0)  # 3 minutes per mile

def consume_records(stream_name, shard_id='shardId-000000000000'):
    """Consume records from Kinesis for dev tests"""
    
    # Shard iterator pattern
    shard_iterator_response = kinesis_client.get_shard_iterator(
        StreamName=stream_name,
        ShardId=shard_id,
        ShardIteratorType='LATEST',  # Get new records only
    )
    
    shard_iterator_id = shard_iterator_response['ShardIterator']
    
    # Record reading
    records_response = kinesis_client.get_records( # Consumer READS data FROM streams
        ShardIterator=shard_iterator_id,
        Limit=10,  # Small batches
    )
    
    records = records_response['Records']
    next_iterator = records_response.get('NextShardIterator')
    
    return records, next_iterator

def process_ride_event(record):
    """Process single ride event"""
    try:
        # JSON parsing
        ride_event = json.loads(record['Data'])        
        
        if 'ride' in ride_event:
            ride = ride_event['ride']
            ride_id = ride_event['ride_id']
        else:
            # Handle direct format
            ride = ride_event
            ride_id = ride_event.get('ride_id', 'unknown')
        
        # Feature preparation
        features = prepare_features(ride)
        prediction = predict(features)
        
        # Prediction event format
        prediction_event = {
            'model': 'ride_duration_prediction_model',
            'version': 'course-consumer',
            'prediction': {
                'ride_duration': prediction,
                'ride_id': ride_id   
            }
        }
        
        return prediction_event
        
    except Exception as e:
        logger.error(f"Failed to process record: {e}")
        return None

def send_prediction(prediction_event):
    """Send prediction to output stream"""
    
    if not TEST_RUN:
        try:
            ride_id = prediction_event['prediction']['ride_id']
            
            kinesis_client.put_record( # Producer SENDS data TO streams
                StreamName=OUTPUT_STREAM_NAME,
                Data=json.dumps(prediction_event),
                PartitionKey=str(ride_id)
            )
            
            logger.info(f"Sent prediction for ride {ride_id}: {prediction_event['prediction']['ride_duration']:.1f} min")
            
        except Exception as e:
            logger.error(f"Failed to send prediction: {e}")
    else:
        ride_id = prediction_event['prediction']['ride_id']
        duration = prediction_event['prediction']['ride_duration']
        logger.info(f"TEST_RUN: Would send prediction for ride {ride_id}: {duration:.1f} min")

def stream_consumer():
    """Main streaming consumer for prod deployment"""
    logger.info(f"Starting stream consumer: {INPUT_STREAM_NAME} -> {OUTPUT_STREAM_NAME}")
    logger.info(f"TEST_RUN: {TEST_RUN}")
    
    shard_iterator = None
    
    try:
        while True:
            # Get records from stream
            if shard_iterator:
                # Use existing shard iterator - consumer READS data FROM streams
                records_response = kinesis_client.get_records( 
                    ShardIterator=shard_iterator,
                    Limit=10
                )
                records = records_response['Records']
                shard_iterator = records_response.get('NextShardIterator')
            else:
                # Get new iterator
                records, shard_iterator = consume_records(INPUT_STREAM_NAME)
            
            # Process records
            if records:
                logger.info(f"Processing {len(records)} records")
                
                for record in records:
                    prediction_event = process_ride_event(record)
                    
                    if prediction_event:
                        send_prediction(prediction_event)
                        
            else:
                # Wait if no records
                time.sleep(1.0)
                
    except KeyboardInterrupt:
        logger.info("Consumer stopped by user")
    except Exception as e:
        logger.error(f"Consumer error: {e}")
        time.sleep(5)  # Wait before potential restart

def create_test_data():
    """Create test data"""
    return [
        {
            'ride': {
                'PULocationID': 161,
                'DOLocationID': 236,
                'trip_distance': 3.5
            },
            'ride_id': 'test_ride_001'
        },
        {
            'ride': {
                'PULocationID': 43,
                'DOLocationID': 151,
                'trip_distance': 1.2
            },
            'ride_id': 'test_ride_002'
        }
    ]

def test_consumer():
    """Test consumer locally"""
    logger.info("Testing consumer with sample data")
    
    test_data = create_test_data()
    
    for data in test_data:
        # Simulate Kinesis record format
        record = {'Data': json.dumps(data)}
        
        prediction_event = process_ride_event(record)
        
        if prediction_event:
            print(f"Prediction: {json.dumps(prediction_event, indent=2)}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Simple Kinesis consumer')
    parser.add_argument('--test-local', action='store_true', help='Test locally without Kinesis')
    parser.add_argument('--input-stream', default='ride-events', help='Input stream name')
    parser.add_argument('--output-stream', default='ride_predictions', help='Output stream name')
    
    args = parser.parse_args()
    
    # Set environment variables
    os.environ['INPUT_STREAM_NAME'] = args.input_stream
    os.environ['OUTPUT_STREAM_NAME'] = args.output_stream
    
    if args.test_local:
        # Test mode
        test_consumer()
    else:
        # Real streaming
        stream_consumer()
