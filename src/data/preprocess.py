# taxi-duration-prediction/src/data/preprocess.py
# Preprocess taxi trip data for model training and inference.
# Environment separation: Uses .env.dev for development, .env.prod for production.
# All bucket, artifact, and endpoint values are loaded from environment variables for flexibility.

import os
import pandas as pd
import pickle
from sklearn.feature_extraction import DictVectorizer
from sklearn.model_selection import train_test_split

def get_data_bucket():
    """
    Get the S3 bucket for input/output data from environment.
    Uses .env.dev for development, .env.prod for production.
    """
    return os.getenv('DATA_BUCKET', 'taxi-data-dev')

def prepare_features(df: pd.DataFrame, categorical: list, numerical: list):
    """
    Prepare feature dictionaries for model training/inference.
    Args:
        df: Input DataFrame
        categorical: List of categorical feature names
        numerical: List of numerical feature names
    Returns:
        List of feature dictionaries
    """
    # Create PU_DO feature
    df['PU_DO'] = df['PULocationID'].astype(str) + '_' + df['DOLocationID'].astype(str)
    categorical = categorical + ['PU_DO']
    dicts = df[categorical + numerical].to_dict(orient='records')
    return dicts

def preprocess_data(df_train: pd.DataFrame, df_val: pd.DataFrame):
    """
    Preprocess training and validation data for model training.
    Args:
        df_train: Training DataFrame
        df_val: Validation DataFrame
    Returns:
        Tuple of (X_train, X_val, y_train, y_val, dv)
    """
    categorical = ['PULocationID', 'DOLocationID']
    numerical = ['trip_distance']
    target = 'duration'
    y_train = df_train[target].values
    y_val = df_val[target].values
    train_dicts = prepare_features(df_train, categorical, numerical)
    val_dicts = prepare_features(df_val, categorical, numerical)
    dv = DictVectorizer()
    X_train = dv.fit_transform(train_dicts)
    X_val = dv.transform(val_dicts)
    return X_train, X_val, y_train, y_val, dv

def save_preprocessor(dv: DictVectorizer, filepath: str):
    """
    Save DictVectorizer to file or S3 bucket (bucket from environment).
    Args:
        dv: DictVectorizer object
        filepath: Local path or S3 URI
    """
    # If saving to S3, use bucket from environment
    if filepath.startswith("s3://"):
        import boto3
        import io
        bucket = filepath.split("/")[2]
        key = "/".join(filepath.split("/")[3:])
        buf = io.BytesIO()
        pickle.dump(dv, buf)
        buf.seek(0)
        s3 = boto3.client('s3')
        s3.put_object(Bucket=bucket, Key=key, Body=buf.getvalue())
    else:
        with open(filepath, 'wb') as f_out:
            pickle.dump(dv, f_out)

def load_preprocessor(filepath: str) -> DictVectorizer:
    """
    Load DictVectorizer from file or S3 bucket (bucket from environment).
    Args:
        filepath: Local path or S3 URI
    Returns:
        DictVectorizer object
    """
    if filepath.startswith("s3://"):
        import boto3
        bucket = filepath.split("/")[2]
        key = "/".join(filepath.split("/")[3:])
        s3 = boto3.client('s3')
        obj = s3.get_object(Bucket=bucket, Key=key)
        dv = pickle.load(obj['Body'])
        return dv
    else:
        with open(filepath, 'rb') as f_in:
            dv = pickle.load(f_in)
        return dv

def prepare_dictionaries(df: pd.DataFrame):
    """
    Prepare feature dictionaries for inference.
    Args:
        df: Input DataFrame
    Returns:
        List of feature dictionaries
    """
    categorical = ['PULocationID', 'DOLocationID']
    numerical = ['trip_distance']
    # Create PU_DO feature
    df['PU_DO'] = df['PULocationID'].astype(str) + '_' + df['DOLocationID'].astype(str)
    categorical = categorical + ['PU_DO']
    dicts = df[categorical + numerical].to_dict(orient='records')
    return dicts