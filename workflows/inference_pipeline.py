# workflows/inference_pipeline.py
# Inference pipeline using Prefect.
# Environment separation: Uses .env.dev for development (your-dev-bucket), .env.prod for production (your-prod-bucket)
# MODEL_BUCKET and OUTPUT_BUCKET are loaded from environment variables for flexibility.

import os
import sys
import uuid
import pickle
from datetime import datetime

import mlflow
import pandas as pd
from prefect import flow, task, get_run_logger
from prefect.context import get_run_context
from dateutil.relativedelta import relativedelta

# Add src to path for organized imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))


def generate_uuids(n):
    ride_ids = []
    for i in range(n):
        ride_ids.append(str(uuid.uuid4()))
    return ride_ids


def read_dataframe(filename: str):
    df = pd.read_parquet(filename)

    df['duration'] = df.tpep_dropoff_datetime - df.tpep_pickup_datetime
    df.duration = df.duration.dt.total_seconds() / 60
    df = df[(df.duration >= 1) & (df.duration <= 60)]

    df['ride_id'] = generate_uuids(len(df))

    return df


def prepare_dictionaries(df: pd.DataFrame):
    categorical = ['PULocationID', 'DOLocationID']
    df[categorical] = df[categorical].astype(str)

    df['PU_DO'] = df['PULocationID'] + '_' + df['DOLocationID']

    categorical = ['PU_DO']
    numerical = ['trip_distance']
    dicts = df[categorical + numerical].to_dict(orient='records')
    return dicts


def get_model_bucket():
    """
    Get the S3 bucket for ML models from environment.
    Uses .env.dev for development, .env.prod for production.
    """
    return os.getenv('MODEL_BUCKET', 'your-dev-bucket')


def load_model(run_id):
    model_bucket = get_model_bucket()
    logged_model = f's3://{model_bucket}/1/{run_id}/artifacts/model'
    # Set MLflow S3 endpoint if provided
    s3_endpoint = os.getenv("MLFLOW_S3_ENDPOINT_URL")
    if s3_endpoint:
        os.environ["MLFLOW_S3_ENDPOINT_URL"] = s3_endpoint
    model = mlflow.pyfunc.load_model(logged_model)
    return model


def get_output_bucket():
    """
    Get the S3 bucket for output predictions from environment.
    Uses OUTPUT_BUCKET env variable, defaults to 'taxi-duration-predictions'.
    """
    return os.getenv('OUTPUT_BUCKET', 'taxi-duration-predictions')


def save_results(df, y_pred, run_id, output_file):
    df_result = pd.DataFrame()
    df_result['ride_id'] = df['ride_id']
    df_result['pickup_datetime'] = df['tpep_pickup_datetime']
    df_result['PULocationID'] = df['PULocationID']
    df_result['DOLocationID'] = df['DOLocationID']
    df_result['actual_duration'] = df['duration']
    df_result['predicted_duration'] = y_pred
    df_result['diff'] = df_result['actual_duration'] - df_result['predicted_duration']
    df_result['model_version'] = run_id

    df_result.to_parquet(output_file, index=False)


@task
def apply_model(input_file, run_id, output_file):
    logger = get_run_logger()

    logger.info(f'reading the data from {input_file}...')
    df = read_dataframe(input_file)
    dicts = prepare_dictionaries(df)

    logger.info(f'loading the model with RUN_ID={run_id}...')
    model = load_model(run_id)

    logger.info(f'applying the model...')
    y_pred = model.predict(dicts)

    logger.info(f'saving the result to {output_file}...')

    save_results(df, y_pred, run_id, output_file)
    return output_file


def get_paths(run_date, taxi_type, run_id):
    prev_month = run_date - relativedelta(months=1)
    year = prev_month.year
    month = prev_month.month

    input_file = (
        f's3://nyc-tlc/trip data/{taxi_type}_tripdata_{year:04d}-{month:02d}.parquet'
    )

    output_bucket = get_output_bucket()
    output_file = f's3://{output_bucket}/taxi_type={taxi_type}/year={year:04d}/month={month:02d}/{run_id}.parquet'

    return input_file, output_file


@flow
def ride_duration_prediction(taxi_type: str, run_id: str, run_date: datetime = None):
    if run_date is None:
        ctx = get_run_context()
        run_date = ctx.flow_run.expected_start_time

    input_file, output_file = get_paths(run_date, taxi_type, run_id)

    apply_model(input_file=input_file, run_id=run_id, output_file=output_file)


@flow
def inference_pipeline_backfill(
    taxi_type: str = 'yellow',
    run_id: str = None,
    start_year: int = 2023,
    start_month: int = 3,
    end_year: int = 2023,
    end_month: int = 6,
):
    """Backfill inference pipeline for multiple months"""

    if run_id is None:
        raise ValueError("run_id must be provided")

    start_date = datetime(year=start_year, month=start_month, day=1)
    end_date = datetime(year=end_year, month=end_month, day=1)

    d = start_date

    while d <= end_date:
        ride_duration_prediction(taxi_type=taxi_type, run_id=run_id, run_date=d)

        d = d + relativedelta(months=1)


@flow
def inference_pipeline(
    taxi_type: str = 'yellow', run_id: str = None, year: int = None, month: int = None
):
    """Main inference pipeline flow"""

    if run_id is None:
        # Get latest model from registry
        client = mlflow.tracking.MlflowClient()
        latest_version = client.get_latest_versions(
            "taxi-duration-model", stages=["Production"]
        )
        if latest_version:
            run_id = latest_version[0].run_id
        else:
            raise ValueError("No production model found. Please specify run_id.")

    if year is None or month is None:
        # Use current month
        now = datetime.now()
        year = now.year
        month = now.month

    run_date = datetime(year=year, month=month, day=1)

    ride_duration_prediction(taxi_type=taxi_type, run_id=run_id, run_date=run_date)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Inference pipeline')
    parser.add_argument(
        '--taxi-type', default='yellow', help='Taxi type (yellow/green)'
    )
    parser.add_argument('--run-id', help='MLflow run ID')
    parser.add_argument('--year', type=int, help='Year for prediction')
    parser.add_argument('--month', type=int, help='Month for prediction')
    parser.add_argument('--backfill', action='store_true', help='Run backfill mode')
    parser.add_argument(
        '--start-year', type=int, default=2023, help='Backfill start year'
    )
    parser.add_argument(
        '--start-month', type=int, default=3, help='Backfill start month'
    )
    parser.add_argument('--end-year', type=int, default=2023, help='Backfill end year')
    parser.add_argument('--end-month', type=int, default=6, help='Backfill end month')

    args = parser.parse_args()

    if args.backfill:
        # Run backfill pipeline
        inference_pipeline_backfill(
            taxi_type=args.taxi_type,
            run_id=args.run_id,
            start_year=args.start_year,
            start_month=args.start_month,
            end_year=args.end_year,
            end_month=args.end_month,
        )
    else:
        # Run inference pipeline
        inference_pipeline(
            taxi_type=args.taxi_type,
            run_id=args.run_id,
            year=args.year,
            month=args.month,
        )
