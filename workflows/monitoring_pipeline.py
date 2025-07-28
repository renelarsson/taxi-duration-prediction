"""
Monitoring pipeline using Prefect and Evidently.
"""

import os
import sys
import time
import logging
import argparse
import datetime

import joblib
import mlflow
import pandas as pd
import psycopg
from prefect import flow, task, get_run_logger
from evidently import Report, Dataset, DataDefinition
from evidently.metrics import ValueDrift, MissingValueCount, DriftedColumnsCount

# Add src to path for organized imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s"
)

SEND_TIMEOUT = 10

create_table_statement = """
drop table if exists dummy_metrics;
create table dummy_metrics(
    timestamp timestamp,
    prediction_drift float,
    num_drifted_columns integer,
    share_missing_values float
)
"""

# Configuration
CONNECTION_STRING = os.getenv(
    'POSTGRES_CONNECTION', "host=localhost port=5432 user=postgres password=example"
)
DB_NAME = os.getenv('POSTGRES_DB', 'monitoring')
CONNECTION_STRING_DB = CONNECTION_STRING + f" dbname={DB_NAME}"

# Features configuration
num_features = ['trip_distance']
cat_features = ['PULocationID', 'DOLocationID']

# Data definition for Evidently
data_definition = DataDefinition(
    numerical_columns=num_features + ['prediction'],
    categorical_columns=cat_features,
)

# Report configuration
report = Report(
    metrics=[
        ValueDrift(column='prediction'),
        DriftedColumnsCount(),
        MissingValueCount(column='prediction'),
    ]
)


@task
def prep_db():
    """Prepare database for monitoring metrics"""
    logger = get_run_logger()
    logger.info("Preparing monitoring database")

    with psycopg.connect(CONNECTION_STRING, autocommit=True) as conn:
        res = conn.execute(f"SELECT 1 FROM pg_database WHERE datname='{DB_NAME}'")
        if len(res.fetchall()) == 0:
            conn.execute(f"create database {DB_NAME};")
            logger.info(f"Created database {DB_NAME}")

        with psycopg.connect(CONNECTION_STRING_DB) as conn:
            conn.execute(create_table_statement)
            logger.info("Created metrics table")


@task
def load_reference_data(reference_path: str) -> pd.DataFrame:
    """Load reference data for drift comparison"""
    logger = get_run_logger()
    logger.info(f"Loading reference data from {reference_path}")

    if reference_path.startswith('s3://'):
        # Load from S3
        reference_data = pd.read_parquet(reference_path)
    else:
        # Load from local file
        reference_data = pd.read_parquet(reference_path)

    logger.info(f"Loaded {len(reference_data)} reference records")
    return reference_data


@task
def load_model(model_path: str = None, run_id: str = None):
    """Load model for predictions"""
    logger = get_run_logger()

    if run_id:
        logger.info(f"Loading model from MLflow run {run_id}")
        model_uri = f"runs:/{run_id}/model"
        model = mlflow.sklearn.load_model(model_uri)
    elif model_path:
        logger.info(f"Loading model from {model_path}")
        with open(model_path, 'rb') as f_in:
            model = joblib.load(f_in)
    else:
        # Try to load latest production model
        logger.info("Loading latest production model")
        client = mlflow.tracking.MlflowClient()
        latest_version = client.get_latest_versions(
            "taxi-duration-model", stages=["Production"]
        )
        if latest_version:
            model_uri = f"runs:/{latest_version[0].run_id}/model"
            model = mlflow.sklearn.load_model(model_uri)
        else:
            raise ValueError("No model found. Provide model_path or run_id.")

    logger.info("Model loaded successfully")
    return model


@task
def calculate_metrics_postgresql(
    current_data: pd.DataFrame,
    reference_data: pd.DataFrame,
    model,
    timestamp: datetime.datetime,
):
    """Calculate monitoring metrics and store in PostgreSQL"""
    logger = get_run_logger()
    logger.info(f"Calculating metrics for {len(current_data)} records")

    # Prepare current data
    current_data = current_data.copy()

    # Convert datetime columns for yellow taxi
    if 'tpep_pickup_datetime' in current_data.columns:
        current_data['pickup_datetime'] = pd.to_datetime(
            current_data['tpep_pickup_datetime']
        )
    elif 'lpep_pickup_datetime' in current_data.columns:
        current_data['pickup_datetime'] = pd.to_datetime(
            current_data['lpep_pickup_datetime']
        )

    # Calculate predictions
    feature_data = current_data[num_features + cat_features].fillna(0)
    current_data['prediction'] = model.predict(feature_data)

    # Create Evidently datasets
    current_dataset = Dataset.from_pandas(current_data, data_definition=data_definition)
    reference_dataset = Dataset.from_pandas(
        reference_data, data_definition=data_definition
    )

    # Run Evidently report
    run = report.run(reference_data=reference_dataset, current_data=current_dataset)
    result = run.dict()

    # Extract metrics
    prediction_drift = result['metrics'][0]['value']
    num_drifted_columns = result['metrics'][1]['value']['count']
    share_missing_values = result['metrics'][2]['value']['share']

    logger.info(
        f"Metrics calculated - Drift: {prediction_drift:.4f}, "
        f"Drifted columns: {num_drifted_columns}, "
        f"Missing values: {share_missing_values:.4f}"
    )

    # Store in PostgreSQL
    with psycopg.connect(CONNECTION_STRING_DB, autocommit=True) as conn:
        with conn.cursor() as curr:
            curr.execute(
                "insert into dummy_metrics(timestamp, prediction_drift, num_drifted_columns, share_missing_values) values (%s, %s, %s, %s)",
                (
                    timestamp,
                    prediction_drift,
                    num_drifted_columns,
                    share_missing_values,
                ),
            )

    logger.info("Metrics stored in database")

    return {
        'prediction_drift': prediction_drift,
        'num_drifted_columns': num_drifted_columns,
        'share_missing_values': share_missing_values,
    }


@task
def check_drift_alerts(metrics: dict, thresholds: dict = None):
    """Check if metrics exceed thresholds and send alerts"""
    logger = get_run_logger()

    if thresholds is None:
        # Default thresholds - should be tuned based on business requirements
        # TODO: Optimize these thresholds based on historical data analysis
        # TODO: Make thresholds configurable via environment variables or config file
        thresholds = {
            'prediction_drift': 0.1,  # 10% prediction drift threshold
            'num_drifted_columns': 3,  # Maximum acceptable drifted columns
            'share_missing_values': 0.05,  # 5% missing values threshold
        }

    alerts = []

    if metrics['prediction_drift'] > thresholds['prediction_drift']:
        alert = f"ALERT: Prediction drift {metrics['prediction_drift']:.4f} exceeds threshold {thresholds['prediction_drift']}"
        alerts.append(alert)
        logger.warning(alert)

    if metrics['num_drifted_columns'] > thresholds['num_drifted_columns']:
        alert = f"ALERT: Number of drifted columns {metrics['num_drifted_columns']} exceeds threshold {thresholds['num_drifted_columns']}"
        alerts.append(alert)
        logger.warning(alert)

    if metrics['share_missing_values'] > thresholds['share_missing_values']:
        alert = f"ALERT: Share of missing values {metrics['share_missing_values']:.4f} exceeds threshold {thresholds['share_missing_values']}"
        alerts.append(alert)
        logger.warning(alert)

    if not alerts:
        logger.info("All metrics within acceptable thresholds")

    return alerts


@flow
def batch_monitoring_backfill(
    data_path: str,
    reference_path: str,
    model_path: str = None,
    run_id: str = None,
    start_date: str = "2023-03-01",
    days: int = 30,
):
    """Backfill monitoring metrics for historical data"""
    logger = get_run_logger()
    logger.info(f"Starting monitoring backfill for {days} days from {start_date}")

    # Prepare database
    prep_db()

    # Load reference data and model
    reference_data = load_reference_data(reference_path)
    model = load_model(model_path, run_id)

    # Load raw data
    raw_data = pd.read_parquet(data_path)

    # Convert start date
    begin = datetime.datetime.strptime(start_date, "%Y-%m-%d")

    last_send = datetime.datetime.now() - datetime.timedelta(seconds=10)

    for i in range(0, days):
        current_date = begin + datetime.timedelta(i)

        # Filter data for current day
        if 'tpep_pickup_datetime' in raw_data.columns:
            pickup_col = 'tpep_pickup_datetime'
        else:
            pickup_col = 'lpep_pickup_datetime'

        current_data = raw_data[
            (raw_data[pickup_col] >= current_date)
            & (raw_data[pickup_col] < (current_date + datetime.timedelta(1)))
        ]

        if len(current_data) > 0:
            # Calculate metrics
            metrics = calculate_metrics_postgresql(
                current_data, reference_data, model, current_date
            )

            # Check for alerts
            check_drift_alerts(metrics)
        else:
            logger.warning(f"No data found for {current_date.date()}")

        # Rate limiting
        new_send = datetime.datetime.now()
        seconds_elapsed = (new_send - last_send).total_seconds()
        if seconds_elapsed < SEND_TIMEOUT:
            time.sleep(SEND_TIMEOUT - seconds_elapsed)
        while last_send < new_send:
            last_send = last_send + datetime.timedelta(seconds=10)

        logger.info(f"Processed day {i+1}/{days}")


@flow
def monitoring_pipeline(
    data_path: str = None,
    reference_path: str = "data/reference.parquet",
    model_path: str = None,
    run_id: str = None,
):
    """Main monitoring pipeline for current data"""
    logger = get_run_logger()
    logger.info("Starting monitoring pipeline")

    # Prepare database
    prep_db()

    # Load reference data and model
    reference_data = load_reference_data(reference_path)
    model = load_model(model_path, run_id)

    if data_path:
        # Load specific data file
        current_data = pd.read_parquet(data_path)
    else:
        # Load latest data (implementation depends on your data source)
        raise ValueError("data_path must be provided")

    # Calculate metrics for current timestamp
    current_timestamp = datetime.datetime.now()
    metrics = calculate_metrics_postgresql(
        current_data, reference_data, model, current_timestamp
    )

    # Check for alerts
    alerts = check_drift_alerts(metrics)

    return {'timestamp': current_timestamp, 'metrics': metrics, 'alerts': alerts}


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Monitoring pipeline')
    parser.add_argument('--data-path', required=True, help='Path to current data')
    parser.add_argument(
        '--reference-path',
        default='data/reference.parquet',
        help='Path to reference data',
    )
    parser.add_argument('--model-path', help='Path to model file')
    parser.add_argument('--run-id', help='MLflow run ID')
    parser.add_argument('--backfill', action='store_true', help='Run backfill mode')
    parser.add_argument(
        '--start-date', default='2023-03-01', help='Start date for backfill'
    )
    parser.add_argument(
        '--days', type=int, default=30, help='Number of days for backfill'
    )

    args = parser.parse_args()

    if args.backfill:
        # Run backfill pipeline
        batch_monitoring_backfill(
            data_path=args.data_path,
            reference_path=args.reference_path,
            model_path=args.model_path,
            run_id=args.run_id,
            start_date=args.start_date,
            days=args.days,
        )
    else:
        # Run monitoring pipeline
        result = monitoring_pipeline(
            data_path=args.data_path,
            reference_path=args.reference_path,
            model_path=args.model_path,
            run_id=args.run_id,
        )
        print(f"Monitoring result: {result}")
