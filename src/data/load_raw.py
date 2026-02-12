import pandas as pd
from src.config import DATA_RAW

def load_raw() -> pd.DataFrame:
    df = pd.read_csv(DATA_RAW)
    return df
