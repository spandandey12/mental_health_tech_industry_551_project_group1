import pandas as pd
from src.config import DATA_RAW
# to read the raw dataset from disk and returns it as a pandas dataFrame
def load_raw() -> pd.DataFrame:
    df = pd.read_csv(DATA_RAW)
    return df