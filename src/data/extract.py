# taxi-duration-prediction/src/data/extract.py 
# Load and read NYC taxi trip data
# Environment separation: Uses .env.dev for local paths, .env.prod for S3 buckets if needed.
# All data paths/buckets are loaded from environment variables for flexibility.

import os
import pandas as pd
import requests
from pathlib import Path

def get_data_dir():
    """
    Get the local data directory from environment.
    Uses .env.dev for development, .env.prod for production.
    """
    return os.getenv('LOCAL_DATA_PATH', 'data')

def download_data(year: int, month: int, color: str = 'yellow') -> str:
    """Download NYC taxi data to local or S3 (if configured)"""
    url = f'https://d37ci6vzurychx.cloudfront.net/trip-data/{color}_tripdata_{year:04d}-{month:02d}.parquet'
    
    # Use environment variable for data directory
    data_dir = Path(get_data_dir())
    data_dir.mkdir(exist_ok=True)
    
    filename = f'{color}_tripdata_{year:04d}-{month:02d}.parquet'
    filepath = data_dir / filename
    
    if not filepath.exists():
        print(f"Downloading {filename}")
        response = requests.get(url)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            f.write(response.content)
    
    return str(filepath)

def read_dataframe(filename: str, nrows: int = 1000) -> pd.DataFrame:
    """Read and clean data, limiting to nrows for memory efficiency"""
    df = pd.read_parquet(filename, engine="pyarrow", columns=None)
    df = df.head(nrows)
    
    # Cleaning
    df['duration'] = df.tpep_dropoff_datetime - df.tpep_pickup_datetime
    df['duration'] = df.duration.dt.total_seconds() / 60
    
    # Filtering
    df = df[(df.duration >= 1) & (df.duration <= 60)].copy()
    
    return df

# Example usage for local testing
if __name__ == "__main__":
    # Set environment for local test (do not use in production)
    os.environ['LOCAL_DATA_PATH'] = 'data'
    filepath = download_data(2023, 3, 'yellow')
    df = read_dataframe(filepath)
    print(df.head())