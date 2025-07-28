"""
Train and log model and DictVectorizer as MLflow artifacts.
Ensures DictVectorizer is always uploaded for inference.
Automatically updates .env.dev with the latest RUN_ID after training.
"""

import os
import pickle
import shutil
from pathlib import Path

import boto3
import numpy as np
import mlflow
import mlflow.sklearn
from sklearn.metrics import mean_squared_error
from sklearn.ensemble import RandomForestRegressor


def update_env_run_id(run_id, env_path="/app/.env.dev"):
    """
    Updates the RUN_ID value in the specified .env file.
    If RUN_ID exists, it is replaced. If not, it is appended.
    """
    lines = []
    found = False
    try:
        with open(env_path, "r") as f:
            for line in f:
                if line.startswith("RUN_ID="):
                    lines.append(f"RUN_ID={run_id}\n")
                    found = True
                else:
                    lines.append(line)
    except FileNotFoundError:
        pass
    if not found:
        lines.append(f"RUN_ID={run_id}\n")
    with open(env_path, "w") as f:
        f.writelines(lines)


def train_model(X_train, X_val, y_train, y_val, dv):
    # Set MLflow tracking URI and experiment
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db"))
    mlflow.set_experiment("taxi-duration-prediction")
    s3_endpoint = os.getenv("MLFLOW_S3_ENDPOINT_URL")
    aws_region = os.getenv("AWS_REGION", "us-east-1")
    if s3_endpoint:
        os.environ["MLFLOW_S3_ENDPOINT_URL"] = s3_endpoint

    bucket = os.getenv('MODEL_BUCKET', 'rll-models-dev')
    aws_region = os.getenv("AWS_REGION", "us-east-1")
    if s3_endpoint:
        s3 = boto3.client("s3", endpoint_url=s3_endpoint, region_name=aws_region)
        try:
            s3.head_bucket(Bucket=bucket)
        except Exception:
            # Always specify region constraint for non-us-east-1
            if aws_region == "us-east-1":
                s3.create_bucket(Bucket=bucket)
            else:
                s3.create_bucket(
                    Bucket=bucket,
                    CreateBucketConfiguration={"LocationConstraint": aws_region},
                )

    with mlflow.start_run():
        rf = RandomForestRegressor(n_estimators=10, random_state=42)
        rf.fit(X_train, y_train)
        y_pred = rf.predict(X_val)
        rmse = np.sqrt(mean_squared_error(y_val, y_pred))

        mlflow.log_param("n_estimators", 10)
        mlflow.log_param("random_state", 42)
        mlflow.log_metric("rmse", rmse)

        # Save and log model
        import glob

        if os.path.exists("model"):
            for f in glob.glob("model/*"):
                try:
                    if os.path.isdir(f):
                        shutil.rmtree(f)
                    else:
                        os.remove(f)
                except Exception as e:
                    print(f"Warning: could not remove {f}: {e}")
        mlflow.sklearn.save_model(rf, path="model")
        mlflow.sklearn.log_model(rf, "model")

        # Save and log DictVectorizer
        with open("dict_vectorizer.pkl", "wb") as f_out:
            pickle.dump(dv, f_out)
        mlflow.log_artifact("dict_vectorizer.pkl")

        # Get the new run ID and update .env.dev
        run_id = mlflow.active_run().info.run_id
        print(f"RMSE: {rmse}")
        print(f"Model saved with run_id: {run_id}")
        update_env_run_id(run_id, env_path="/app/.env.dev")
        return rf, rmse


if __name__ == "__main__":
    from src.data.extract import download_data, read_dataframe
    from src.data.preprocess import preprocess_data

    train_path = download_data(2023, 1, 'yellow')
    val_path = download_data(2023, 2, 'yellow')
    df_train = read_dataframe(train_path, nrows=1000)
    df_val = read_dataframe(val_path, nrows=1000)
    X_train, X_val, y_train, y_val, dv = preprocess_data(df_train, df_val)
    train_model(X_train, X_val, y_train, y_val, dv)
