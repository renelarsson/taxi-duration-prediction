# taxi-duration-prediction/src/data/preprocess.py
# Preprocess taxi trip data for model training and inference
import pandas as pd
import pickle
from sklearn.feature_extraction import DictVectorizer
from sklearn.model_selection import train_test_split

def prepare_features(df: pd.DataFrame, categorical: list, numerical: list):
    """
    Args:
        df: Input DataFrame
        categorical: List of categorical feature names
        numerical: List of numerical feature names
    Returns:
        List of feature dictionaries
    """
    # Create PU_DO feature
    df['PU_DO'] = df['PULocationID'].astype(str) + '_' + df['DOLocationID'].astype(str)
    
    # Add to categorical features
    categorical = categorical + ['PU_DO']
    
    # Convert to dict records
    dicts = df[categorical + numerical].to_dict(orient='records')
    return dicts

def preprocess_data(df_train: pd.DataFrame, df_val: pd.DataFrame):
    """
    Args:
        df_train: Training DataFrame
        df_val: Validation DataFrame    
    Returns:
        Tuple of (X_train, X_val, y_train, y_val, dv)
    """
    # Define categorical and numerical features
    categorical = ['PULocationID', 'DOLocationID']
    numerical = ['trip_distance']
    
    # Add duration target
    target = 'duration'
    y_train = df_train[target].values
    y_val = df_val[target].values
    
    # Prepare features
    train_dicts = prepare_features(df_train, categorical, numerical)
    val_dicts = prepare_features(df_val, categorical, numerical)
    
    # Fit DictVectorizer
    dv = DictVectorizer()
    X_train = dv.fit_transform(train_dicts)
    X_val = dv.transform(val_dicts)
    
    return X_train, X_val, y_train, y_val, dv

def save_preprocessor(dv: DictVectorizer, filepath: str):
    """Save DictVectorizer"""
    with open(filepath, 'wb') as f_out:
        pickle.dump(dv, f_out)

def load_preprocessor(filepath: str) -> DictVectorizer:
    """Load DictVectorizer"""
    with open(filepath, 'rb') as f_in:
        dv = pickle.load(f_in)
    return dv

def prepare_dictionaries(df: pd.DataFrame):
    """
    Prepare feature dictionaries for inference   
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
    
    # Convert to dicts
    dicts = df[categorical + numerical].to_dict(orient='records')
    return dicts