# src/models/predict.py
# Model prediction utilities for taxi duration prediction.
# Environment separation: Uses .env.dev for development (rll-models-dev), .env.prod for production (rll-models-prod)
# All bucket, stream, and run_id values are loaded from environment variables for flexibility.

import pickle
import mlflow
import mlflow.sklearn
import pandas as pd
import numpy as np
from sklearn.metrics import mean_squared_error
import os

# Set MLflow S3 endpoint if provided (for dev/prod separation)
s3_endpoint = os.getenv("MLFLOW_S3_ENDPOINT_URL")
if s3_endpoint:
    os.environ["MLFLOW_S3_ENDPOINT_URL"] = s3_endpoint

def get_model_bucket():
    """
    Get the S3 bucket for ML models from environment.
    Uses .env.dev for development, .env.prod for production.
    """
    return os.getenv('MODEL_BUCKET', 'rll-models-dev')

def get_run_id():
    """
    Get the MLflow run ID from environment.
    """
    return os.getenv('RUN_ID')

def load_model(model_path: str):
    """Load pickled model"""
    with open(model_path, 'rb') as f_in:
        model = pickle.load(f_in)
    return model

def load_preprocessor(dv_path: str):
    """Load DictVectorizer"""
    with open(dv_path, 'rb') as f_in:
        dv = pickle.load(f_in)
    return dv

def predict_duration(df: pd.DataFrame, model, dv):
    """    
    Args:
        df: Input DataFrame with taxi trip data
        model: Trained model
        dv: Fitted DictVectorizer    
    Returns:
        Array of predictions
    """
    # Prepare features 
    categorical = ['PULocationID', 'DOLocationID']
    numerical = ['trip_distance']
    
    # Create PU_DO feature
    df['PU_DO'] = df['PULocationID'].astype(str) + '_' + df['DOLocationID'].astype(str)
    categorical = categorical + ['PU_DO']
    
    # Convert to dicts 
    dicts = df[categorical + numerical].to_dict(orient='records')
    
    # Transform and predict
    X = dv.transform(dicts)
    predictions = model.predict(X)
    
    return predictions

def evaluate_model(df_test: pd.DataFrame, model, dv):
    """    
    Args:
        df_test: Test DataFrame
        model: Trained model
        dv: Fitted DictVectorizer    
    Returns:
        Dictionary with evaluation metrics
    """
    # Get actual values
    y_actual = df_test['duration'].values
    
    # Get predictions
    y_pred = predict_duration(df_test, model, dv)
    
    # Calculate metrics 
    rmse = np.sqrt(mean_squared_error(y_actual, y_pred))
    mae = np.mean(np.abs(y_actual - y_pred))
    
    print(f"RMSE: {rmse:.4f}")
    print(f"MAE: {mae:.4f}")
    
    return {'rmse': rmse, 'mae': mae}

def predict_single_trip(trip_data: dict, model, dv):
    """    
    Args:
        trip_data: Dictionary with trip information
        model: Trained model
        dv: Fitted DictVectorizer    
    Returns:
        Predicted duration
    """
    # Convert single trip to DataFrame
    df = pd.DataFrame([trip_data])
    
    # Predict
    prediction = predict_duration(df, model, dv)
    
    return prediction[0]

def load_mlflow_model(run_id: str = None):
    """
    Load model from MLflow.    
    Args:
        run_id: MLflow run ID (if not provided, loaded from environment)
    Returns:
        Loaded model
    """
    # Set tracking URI from environment
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db"))
    if run_id is None:
        run_id = get_run_id()
    # Use bucket from environment for S3-based model storage
    model_bucket = get_model_bucket()
    experiment_id = os.getenv('MLFLOW_EXPERIMENT_ID', '1')
    # If using MLflow S3 artifact store, use full S3 URI
    model_uri = f"s3://{model_bucket}/{experiment_id}/{run_id}/artifacts/model"
    try:
        model = mlflow.pyfunc.load_model(model_uri)
    except Exception:
        # Fallback to MLflow run URI if S3 fails
        model_uri = f"runs:/{run_id}/model"
        model = mlflow.sklearn.load_model(model_uri)
    return model

def apply_model(input_file: str, run_id: str = None, output_file: str = None):
    """
    Apply model to new data - batch prediction    
    Args:
        input_file: Input data file path
        run_id: MLflow run ID (optional, loaded from environment if not provided)
        output_file: Output predictions file path (optional)
    """
    # Load data
    df = pd.read_parquet(input_file)
    
    # Validate data before prediction
    if not validate_data(df):
        print("Input data validation failed.")
        return
    
    # Load model from MLflow
    model = load_mlflow_model(run_id)
    
    # Load preprocessor (assume it's saved with the model)
    dv = load_preprocessor('models/dv.bin')
    
    # Predict
    predictions = predict_duration(df, model, dv)
    
    # Save predictions
    df['predicted_duration'] = predictions
    if output_file:
        df.to_parquet(output_file, index=False)
        print(f"Predictions saved to {output_file}")
    else:
        print(df[['ride_id', 'predicted_duration']].head())

def validate_data(df: pd.DataFrame):
    """
    Validate input data.    
    Args:
        df: Input DataFrame    
    Returns:
        Boolean indicating if data is valid
    """
    required_columns = ['PULocationID', 'DOLocationID', 'trip_distance']
    
    # Check required columns
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        print(f"Missing columns: {missing_columns}")
        return False
    
    # Check for null values
    if df[required_columns].isnull().any().any():
        print("Found null values in required columns")
        return False
    
    # Check data types
    if not pd.api.types.is_numeric_dtype(df['trip_distance']):
        print("trip_distance is not numeric")
        return False
    
    return True

# Example usage for local testing
if __name__ == "__main__":
    # Set environment for local test (do not use in production)
    os.environ['MODEL_BUCKET'] = 'rll-models-dev'  # Change to rll-models-prod for prod test
    os.environ['RUN_ID'] = 'a986756f70a240cf8808a59ed77ba2d3'

    # Example: batch prediction
    input_file = 'data/test_trips.parquet'
    output_file = 'data/predictions.parquet'
    apply_model(input_file, os.environ['RUN_ID'], output_file)

    # Example: single trip prediction
    test_trip = {
        'PULocationID': 161,
        'DOLocationID': 236,
        'trip_distance': 3.5
    }
    model = load_mlflow_model()
    dv = load_preprocessor('models/dv.bin')
    duration = predict_single_trip(test_trip, model, dv)
    print(f"Predicted duration for test trip: {duration}")