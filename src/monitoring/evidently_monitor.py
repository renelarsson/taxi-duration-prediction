import os
import datetime
import time
import logging 
import pandas as pd
import psycopg
import argparse
import joblib
from prefect import task, flow
from evidently import Report
from evidently import DataDefinition
from evidently import Dataset
from evidently.metrics import ValueDrift, DriftedColumnsCount, MissingValueCount

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s")

# Configuration from environment
SEND_TIMEOUT = int(os.getenv('MONITORING_SEND_TIMEOUT', '10'))
DB_HOST = os.getenv('DB_HOST', 'db')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'example')
DB_NAME = os.getenv('DB_NAME', 'test')

# Database setup - configurable
CONNECTION_STRING = f"host={DB_HOST} port={DB_PORT} user={DB_USER} password={DB_PASSWORD}"
CONNECTION_STRING_DB = f"{CONNECTION_STRING} dbname={DB_NAME}"

create_table_statement = """
drop table if exists taxi_metrics;
create table taxi_metrics(
    timestamp timestamp,
    prediction_drift float,
    num_drifted_columns integer,
    share_missing_values float
)
"""

def load_reference_data(reference_path: str = None):
    """
    Load reference data for drift detection.    
    Args:
        reference_path: Path to reference data file    
    Returns:
        Reference DataFrame
    """
    if reference_path is None:
        reference_path = os.getenv('REFERENCE_DATA_PATH', 'data/reference.parquet')
    
    try:
        reference_data = pd.read_parquet(reference_path)
        logging.info(f"Loaded reference data from {reference_path}")
        return reference_data
        
    except FileNotFoundError:
        logging.warning(f"Reference data not found at {reference_path}. Creating from historical data.")
        return create_reference_data()

def create_reference_data():
    """
    Create reference data from historical data.    
    Returns:
        Reference DataFrame
    """
    # Use January 2023 as stable reference
    reference_month = os.getenv('REFERENCE_MONTH', '2023-01')
    reference_file = f'data/yellow_tripdata_{reference_month}.parquet'
    
    try:
        reference_data = pd.read_parquet(reference_file)
        
        # Apply preprocessing to create stable reference
        reference_data = preprocess_taxi_data(reference_data)
        
        # Sample for performance 
        if len(reference_data) > 10000:
            reference_data = reference_data.sample(n=10000, random_state=42)
        
        # Save for future use
        os.makedirs('data', exist_ok=True)
        reference_data.to_parquet('data/reference.parquet')
        logging.info(f"Created reference data from {reference_file}")
        
        return reference_data
        
    except FileNotFoundError:
        raise FileNotFoundError(f"Cannot create reference data. {reference_file} not found.")

def preprocess_taxi_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply same preprocessing as reference data (training set) for fair comparison.    
    Args:
        df: Raw taxi DataFrame    
    Returns:
        Preprocessed DataFrame
    """
    # Datetime preprocessing
    df['tpep_pickup_datetime'] = pd.to_datetime(df['tpep_pickup_datetime'])
    df['tpep_dropoff_datetime'] = pd.to_datetime(df['tpep_dropoff_datetime'])
    
    # Duration calculation
    df['duration'] = (df.tpep_dropoff_datetime - df.tpep_pickup_datetime).dt.total_seconds() / 60
    
    # Filtering - same as training data
    df = df[(df.duration >= 1) & (df.duration <= 60)].copy()
    
    # Feature engineering - matches preprocess.py
    df['PU_DO'] = df['PULocationID'].astype(str) + '_' + df['DOLocationID'].astype(str)
    
    # Data quality - basic cleaning
    df = df[(df.passenger_count > 0) & (df.passenger_count < 8)].copy()
    
    return df

def load_model(model_path: str = None):
    """
    Load trained model for predictions.    
    Args:
        model_path: Path to model file    
    Returns:
        Loaded model or None
    """
    if model_path is None:
        model_path = os.getenv('MODEL_PATH', 'models/model.bin')
    
    try:
        with open(model_path, 'rb') as f_in:
            model = joblib.load(f_in)
        logging.info(f"Loaded model from {model_path}")
        return model
    except FileNotFoundError:
        logging.warning(f"Model not found at {model_path}")
        return None

def load_data_for_date(target_date: datetime.datetime) -> pd.DataFrame:
    """
    Load data for specific day.    
    Args:
        target_date: Date to load data for    
    Returns:
        DataFrame for target date
    """
    # Monthly files, filter by day
    monthly_file = f'data/yellow_tripdata_{target_date.year}-{target_date.month:02d}.parquet'
    
    try:
        df = pd.read_parquet(monthly_file)
        
        # Filter to specific day
        df['tpep_pickup_datetime'] = pd.to_datetime(df['tpep_pickup_datetime'])
        daily_data = df[df.tpep_pickup_datetime.dt.date == target_date.date()]
        
        if len(daily_data) == 0:
            logging.warning(f"No data found for {target_date.date()}")
        
        return daily_data
        
    except FileNotFoundError:
        logging.error(f"Monthly data file not found: {monthly_file}")
        return pd.DataFrame()

# Feature definitions - matches preprocess.py
num_features = ['trip_distance']
cat_features = ['PULocationID', 'DOLocationID', 'PU_DO']

# Evidently setup - post-0.7 version
data_definition = DataDefinition(
    numerical_columns=num_features + ['prediction'],
    categorical_columns=cat_features,
)

report = Report(metrics=[
    ValueDrift(column='prediction'),
    DriftedColumnsCount(),
    MissingValueCount(column='prediction'),
])

@task
def prep_db():
    """Prepare PostgreSQL database"""
    try:
        with psycopg.connect(CONNECTION_STRING, autocommit=True) as conn:
            res = conn.execute("SELECT 1 FROM pg_database WHERE datname=%s", (DB_NAME,))
            if len(res.fetchall()) == 0:
                conn.execute(f"create database {DB_NAME};")
                logging.info(f"Created database {DB_NAME}")
            
            with psycopg.connect(CONNECTION_STRING_DB) as conn:
                conn.execute(create_table_statement)
                logging.info("Created taxi_metrics table")
                
    except Exception as e:
        logging.error(f"Database preparation failed: {e}")
        raise

@task
def calculate_metrics_postgresql(current_data: pd.DataFrame, reference_data: pd.DataFrame, 
                               model, timestamp: datetime.datetime):
    """Calculate Evidently metrics and store in PostgreSQL"""
    
    if len(current_data) == 0:
        logging.warning("No current data to process")
        return
    
    # Preprocess current data - same as reference
    current_data = preprocess_taxi_data(current_data)
    
    if len(current_data) == 0:
        logging.warning("No data after preprocessing")
        return
    
    # Add predictions to current data
    if model is not None:
        try:
            # Prepare features for prediction - matches train.py
            feature_cols = num_features + ['PULocationID', 'DOLocationID']
            current_data['prediction'] = model.predict(current_data[feature_cols].fillna(0))
        except Exception as e:
            logging.warning(f"Model prediction failed: {e}. Using duration as prediction.")
            current_data['prediction'] = current_data['duration']
    else:
        # Fallback: use duration as prediction for monitoring demo
        current_data['prediction'] = current_data['duration']
    
    try:
        # Create Evidently datasets
        current_dataset = Dataset.from_pandas(current_data, data_definition=data_definition)
        reference_dataset = Dataset.from_pandas(reference_data, data_definition=data_definition)
        
        # Run Evidently report
        run = report.run(reference_data=reference_dataset, current_data=current_dataset)
        result = run.dict()
        
        # Extract metrics
        prediction_drift = result['metrics'][0]['value']
        num_drifted_columns = result['metrics'][1]['value']['count']
        share_missing_values = result['metrics'][2]['value']['share']
        
        # Store in PostgreSQL
        with psycopg.connect(CONNECTION_STRING_DB, autocommit=True) as conn:
            with conn.cursor() as curr:
                curr.execute(
                    "insert into taxi_metrics(timestamp, prediction_drift, num_drifted_columns, share_missing_values) values (%s, %s, %s, %s)",
                    (timestamp, prediction_drift, num_drifted_columns, share_missing_values)
                )
        
        logging.info(f"Metrics calculated for {timestamp}: drift={prediction_drift:.4f}, drifted_cols={num_drifted_columns}, missing={share_missing_values:.4f}")
        
    except Exception as e:
        logging.error(f"Metrics calculation failed: {e}")

def monitor_current_data(current_data_path: str):
    """Monitor single batch of data"""
    
    # Load reference data and model
    reference_data = load_reference_data()
    model = load_model()
    
    # Load and process current data
    current_data = pd.read_parquet(current_data_path)
    timestamp = datetime.datetime.now()
    
    # Calculate and store metrics
    calculate_metrics_postgresql(current_data, reference_data, model, timestamp)

@flow
def batch_monitoring_backfill(start_date: datetime.datetime, num_days: int = 7):
    """
    Batch monitoring backfill to simulate weeks of monitoring data quickly. Calculates metrics for historical/past dates to populate monitoring dashboard.    
    Args:
        start_date: Start date for backfill
        num_days: Number of days to backfill
    """    
    prep_db()
    reference_data = load_reference_data()
    model = load_model()
    
    last_send = datetime.datetime.now() - datetime.timedelta(seconds=SEND_TIMEOUT)
    
    for i in range(num_days):
        current_date = start_date + datetime.timedelta(days=i)
        logging.info(f"Processing day {i+1}/{num_days}: {current_date.date()}")
        
        # Load data for specific day
        current_data = load_data_for_date(current_date)
        
        if len(current_data) > 0:
            calculate_metrics_postgresql(current_data, reference_data, model, current_date)
        else:
            logging.warning(f"Skipping {current_date.date()} - no data")
        
        # Timing - throttle requests (add delays between operations)
        new_send = datetime.datetime.now()
        seconds_elapsed = (new_send - last_send).total_seconds()
        if seconds_elapsed < SEND_TIMEOUT:
            time.sleep(SEND_TIMEOUT - seconds_elapsed)
        while last_send < new_send:
            last_send = last_send + datetime.timedelta(seconds=SEND_TIMEOUT)
        
        logging.info(f"Day {i+1} completed")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Evidently monitoring')
    parser.add_argument('--start-date', default='2023-06-01', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--num-days', type=int, default=7, help='Number of days to process')
    parser.add_argument('--reference-path', help='Path to reference data')
    
    args = parser.parse_args()
    
    # Parse start date
    start_date = datetime.datetime.strptime(args.start_date, '%Y-%m-%d')
    
    # Run monitoring backfill
    batch_monitoring_backfill(start_date, args.num_days)