from pathlib import Path
import pandas as pd
import numpy as np

project_root=Path(__file__).resolve().parents[1]
raw_dir=project_root /"data"/"raw"
out_dir=project_root/"data"/"processed"
out_dir.mkdir(parents=True,exist_ok=True)

# Read raw CSV
csv_files=list(raw_dir.glob("*.csv"))
if len(csv_files) == 0:
    raise FileNotFoundError("Put your raw CSV inside data/raw/")
raw_path=csv_files[0]
print("Reading:", raw_path)
df=pd.read_csv(raw_path)

df.columns=(
    df.columns.str.strip()
    .str.lower()
    .str.replace(" ", "_")
    .str.replace(r"[^\w_]", "", regex=True)
)

if "timestamp" in df.columns:
    df["year"]=pd.to_datetime(df["timestamp"], errors="coerce").dt.year
else:
    df["year"]=2014
df["year"]=pd.to_numeric(df["year"], errors="coerce").astype("Int64")

if "country" in df.columns:
    c=df["country"].astype(str).str.strip().str.lower()
    df["region"]=np.where(
        c.isin(["united states", "usa", "us", "canada"]),
        "North America",
        "Other"
    )
else:
    df["region"] = pd.NA
if "age" in df.columns:
    age=pd.to_numeric(df["age"], errors="coerce")
    df["age_bin"] = pd.cut(
        age,
        bins=[0, 18, 25, 35, 45, 55, 65, 200],
        labels=["0-18", "19-25", "26-35", "36-45", "46-55", "56-65", "66+"],
        include_lowest=True
    ).astype("string")
else:
    df["age_bin"]=pd.NA
if "no_employees" in df.columns:
    df["company_size"]=df["no_employees"].astype("string").str.strip()
else:
    df["company_size"]=pd.NA
required_cols = [
    "year", "region", "gender", "age_bin", "company_size", "remote_work",
    "treatment", "work_interfere", "benefits", "family_history", "seek_help",
    "care_options", "wellness_program", "anonymity",
]
for col in required_cols:
    if col not in df.columns:
        df[col] = pd.NA
df_out=df[required_cols].copy()
for col in df_out.columns:
    if col != "year":
        df_out[col] = df_out[col].astype("string").fillna("<missing>")
df_out = df_out.dropna(subset=["year"])
out_path = out_dir / "cleaned.csv"
df_out.to_csv(out_path, index=False)

print("Saved to:", out_path)
print("Shape:", df_out.shape)
