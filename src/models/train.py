# src/models/train.py
# Train and save machine learning models for taxi duration prediction.
# Environment separation: Uses .env.dev for development, .env.prod for production.
# All bucket, artifact, and endpoint values are loaded from environment variables for flexibility.

import pickle
import mlflow
import mlflow.sklearn
import os
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error
import numpy as np
from pathlib import Path

def get_model_bucket():
    """
    Get the S3 bucket for MLflow model artifacts from environment.
    Uses .env.dev for development, .env.prod for production.
    """
    return os.getenv('MODEL_BUCKET', 'mlflow-models-rll')

def get_mlflow_tracking_uri():
    """
    Get MLflow tracking URI from environment.
    """
    return os.getenv("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")

def get_mlflow_s3_endpoint():
    """
    Get MLflow S3 endpoint from environment.
    """
    return os.getenv("MLFLOW_S3_ENDPOINT_URL")

def train_model(X_train, X_val, y_train, y_val, dv):
    """
    Train Random Forest model and log to MLflow with environment separation.
    Args:
        X_train: Training features (sparse matrix from DictVectorizer)
        X_val: Validation features (sparse matrix from DictVectorizer)
        y_train: Training targets
        y_val: Validation targets
        dv: Fitted DictVectorizer
    Returns:
        Tuple of (model, rmse)
    """
    # Set MLflow tracking to use environment variable
    mlflow.set_tracking_uri(get_mlflow_tracking_uri())
    # Set MLflow S3 endpoint if provided (for dev/prod separation)
    s3_endpoint = get_mlflow_s3_endpoint()
    if s3_endpoint:
        os.environ["MLFLOW_S3_ENDPOINT_URL"] = s3_endpoint

    mlflow.set_experiment("taxi-duration-prediction")

    with mlflow.start_run():
        # Train Random Forest
        rf = RandomForestRegressor(n_estimators=10, random_state=42)
        rf.fit(X_train, y_train)

        # Predict
        y_pred = rf.predict(X_val)

        # Calculate RMSE
        rmse = np.sqrt(mean_squared_error(y_val, y_pred))

        # Log parameters
        mlflow.log_param("n_estimators", 10)
        mlflow.log_param("random_state", 42)
        mlflow.log_metric("rmse", rmse)

        # Save model artifacts locally
        models_dir = Path("model")
        models_dir.mkdir(exist_ok=True)

        with open(models_dir / "model.bin", "wb") as f_out:
            pickle.dump(rf, f_out)
        with open(models_dir / "dv.bin", "wb") as f_out:
            pickle.dump(dv, f_out)

        # Log artifacts to MLflow
        mlflow.log_artifact("model/model.bin")
        mlflow.log_artifact("model/dv.bin")

        # Also log as sklearn model
        mlflow.sklearn.log_model(rf, "model")

        print(f"RMSE: {rmse}")
        print(f"Model saved with run_id: {mlflow.active_run().info.run_id}")

        return rf, rmse

def train_linear_model(X_train, X_val, y_train, y_val):
    """
    Train Linear Regression model and log to MLflow.
    Args:
        X_train: Training features
        X_val: Validation features
        y_train: Training targets
        y_val: Validation targets
    Returns:
        Tuple of (model, rmse)
    """
    mlflow.set_tracking_uri(get_mlflow_tracking_uri())
    with mlflow.start_run():
        lr = LinearRegression()
        lr.fit(X_train, y_train)

        y_pred = lr.predict(X_val)
        rmse = np.sqrt(mean_squared_error(y_val, y_pred))

        mlflow.log_param("model_type", "LinearRegression")
        mlflow.log_metric("rmse", rmse)
        mlflow.sklearn.log_model(lr, "model")

        print(f"Linear Regression RMSE: {rmse}")
        return lr, rmse

def save_model(model, dv, output_dir: str = "model"):
    """
    Save model and preprocessor.
    Args:
        model: Trained model
        dv: Fitted DictVectorizer
        output_dir: Output directory
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    with open(output_path / "model.bin", "wb") as f_out:
        pickle.dump(model, f_out)
    with open(output_path / "dv.bin", "wb") as f_out:
        pickle.dump(dv, f_out)

    print(f"Model and preprocessor saved to {output_dir}")

def load_model(model_dir: str = "model"):
    """
    Load model and preprocessor.
    Args:
        model_dir: Model directory
    Returns:
        Tuple of (model, dv)
    """
    model_path = Path(model_dir)

    with open(model_path / "model.bin", "rb") as f_in:
        model = pickle.load(f_in)
    with open(model_path / "dv.bin", "rb") as f_in:
        dv = pickle.load(f_in)

    return model, dv

if __name__ == "__main__":
    from src.data.extract import download_data, read_dataframe
    from src.data.preprocess import preprocess_data

    # Download and preprocess data
    train_path = download_data(2023, 1, 'yellow')
    val_path = download_data(2023, 2, 'yellow')

    # Limit to first 1,000 rows for memory efficiency
    df_train = read_dataframe(train_path, nrows=1000)
    df_val = read_dataframe(val_path, nrows=1000)

    X_train, X_val, y_train, y_val, dv = preprocess_data(df_train, df_val)

    # Train and log model (uses environment separation for buckets and endpoints)
    train_model(X_train, X_val, y_train, y_val, dv)