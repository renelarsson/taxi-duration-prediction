# taxi-duration-prediction/src/data/extract.py
# Load and read NYC taxi trip data
import pandas as pd
import requests
from pathlib import Path

def download_data(year: int, month: int, color: str = 'yellow') -> str:
    """Download NYC taxi data"""
    url = f'https://d37ci6vzurychx.cloudfront.net/trip-data/{color}_tripdata_{year:04d}-{month:02d}.parquet'
    
    # Download to data/
    data_dir = Path('data')
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

def read_dataframe(filename: str, nrows: int = 1000) -> pd.DataFrame: # R: changed
    """Read and clean data, limiting to nrows for memory efficiency"""
    df = pd.read_parquet(filename, engine="pyarrow", columns=None)
    df = df.head(nrows)
    
    # Cleaning
    df['duration'] = df.tpep_dropoff_datetime - df.tpep_pickup_datetime
    df['duration'] = df.duration.dt.total_seconds() / 60
    
    # Filtering
    df = df[(df.duration >= 1) & (df.duration <= 60)].copy()
    
    return df
