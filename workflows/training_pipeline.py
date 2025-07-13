"""
Training pipeline using Prefect.
"""
import os
import sys
import pathlib
import pickle
import pandas as pd
import numpy as np
import scipy
import sklearn
from sklearn.feature_extraction import DictVectorizer
from sklearn.metrics import mean_squared_error
import mlflow
import xgboost as xgb
from prefect import flow, task
from prefect.artifacts import create_markdown_artifact
from datetime import date

# Add src to path for organized imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

@task(retries=3, retry_delay_seconds=2)
def read_data(filename: str) -> pd.DataFrame:
    """Read data into DataFrame"""
    df = pd.read_parquet(filename)

    df.tpep_dropoff_datetime = pd.to_datetime(df.tpep_dropoff_datetime)
    df.tpep_pickup_datetime = pd.to_datetime(df.tpep_pickup_datetime)

    df["duration"] = df.tpep_dropoff_datetime - df.tpep_pickup_datetime
    df.duration = df.duration.apply(lambda td: td.total_seconds() / 60)

    df = df[(df.duration >= 1) & (df.duration <= 60)]

    categorical = ["PULocationID", "DOLocationID"]
    df[categorical] = df[categorical].astype(str)

    return df

@task
def add_features(
    df_train: pd.DataFrame, df_val: pd.DataFrame
) -> tuple[
    scipy.sparse._csr.csr_matrix,
    scipy.sparse._csr.csr_matrix,
    np.ndarray,
    np.ndarray,
    sklearn.feature_extraction.DictVectorizer,
]:
    """Add features to the model"""
    df_train["PU_DO"] = df_train["PULocationID"] + "_" + df_train["DOLocationID"]
    df_val["PU_DO"] = df_val["PULocationID"] + "_" + df_val["DOLocationID"]

    categorical = ["PU_DO"]
    numerical = ["trip_distance"]

    dv = DictVectorizer()

    train_dicts = df_train[categorical + numerical].to_dict(orient="records")
    X_train = dv.fit_transform(train_dicts)

    val_dicts = df_val[categorical + numerical].to_dict(orient="records")
    X_val = dv.transform(val_dicts)

    y_train = df_train["duration"].values
    y_val = df_val["duration"].values
    return X_train, X_val, y_train, y_val, dv

@task(log_prints=True)
def train_best_model(
    X_train: scipy.sparse._csr.csr_matrix,
    X_val: scipy.sparse._csr.csr_matrix,
    y_train: np.ndarray,
    y_val: np.ndarray,
    dv: sklearn.feature_extraction.DictVectorizer,
) -> None:
    """train a model with sensible hyperparams"""

    with mlflow.start_run():
        train = xgb.DMatrix(X_train, label=y_train)
        valid = xgb.DMatrix(X_val, label=y_val)

        # Sensible default parameters for yellow taxi duration prediction
        # TODO: Optimize these parameters specifically for our dataset
        best_params = {
            "learning_rate": 0.1,
            "max_depth": 6,
            "min_child_weight": 1,
            "objective": "reg:squarederror",
            "reg_alpha": 0.01,
            "reg_lambda": 0.01,
            "seed": 42,
        }

        mlflow.log_params(best_params)

        booster = xgb.train(
            params=best_params,
            dtrain=train,
            num_boost_round=100,
            evals=[(valid, "validation")],
            early_stopping_rounds=20,
        )

        y_pred = booster.predict(valid)
        rmse = mean_squared_error(y_val, y_pred, squared=False)
        mlflow.log_metric("rmse", rmse)

        pathlib.Path("models").mkdir(exist_ok=True)
        with open("models/preprocessor.b", "wb") as f_out:
            pickle.dump(dv, f_out)
        mlflow.log_artifact("models/preprocessor.b", artifact_path="preprocessor")

        mlflow.xgboost.log_model(booster, artifact_path="models_mlflow")

        markdown_rmse_report = f"""# RMSE Report

        ## Summary

        Duration Prediction 

        ## RMSE XGBoost Model

        | Region    | RMSE |
        |:----------|-------:|
        | {date.today()} | {rmse:.2f} |
        """

        create_markdown_artifact(
            key="duration-model-report", markdown=markdown_rmse_report
        )

    return None

@flow
def main_flow(
    train_path: str = "./data/yellow_tripdata_2023-01.parquet",
    val_path: str = "./data/yellow_tripdata_2023-02.parquet",
) -> None:
    """The main training pipeline"""

    # MLflow settings
    import os
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db"))
    # Set MLflow S3 endpoint if provided
    s3_endpoint = os.getenv("MLFLOW_S3_ENDPOINT_URL")
    if s3_endpoint:
        os.environ["MLFLOW_S3_ENDPOINT_URL"] = s3_endpoint
    mlflow.set_experiment("taxi-duration-experiment")

    # Load
    df_train = read_data(train_path)
    df_val = read_data(val_path)

    # Transform
    X_train, X_val, y_train, y_val, dv = add_features(df_train, df_val)

    # Train
    train_best_model(X_train, X_val, y_train, y_val, dv)

@flow
def training_pipeline(
    year: int = 2023,
    train_month: int = 1,
    val_month: int = 2,
) -> None:
    """Training pipeline with configurable months"""
    
    train_path = f"./data/yellow_tripdata_{year}-{train_month:02d}.parquet"
    val_path = f"./data/yellow_tripdata_{year}-{val_month:02d}.parquet"
    
    main_flow(train_path, val_path)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Training pipeline')
    parser.add_argument('--year', type=int, default=2023, help='Data year')
    parser.add_argument('--train-month', type=int, default=1, help='Training month')
    parser.add_argument('--val-month', type=int, default=2, help='Validation month')
    
    args = parser.parse_args()
    
    training_pipeline(
        year=args.year,
        train_month=args.train_month,
        val_month=args.val_month
    )
