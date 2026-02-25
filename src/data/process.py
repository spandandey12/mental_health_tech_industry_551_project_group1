from __future__ import annotations
import re
from pathlib import Path
import pandas as pd
from src.config import DATA_PROCESSED
from src.data.load_raw import load_raw

# Changing all to Yes/No/Unknown
YES_NO_MAP={
    "yes": "Yes",
    "y": "Yes",
    "no": "No",
    "n": "No",
    "don't know": "Don't know",
    "dont know": "Don't know",
    "dk": "Don't know",
    "unknown": "Unknown",
    "not sure": "Don't know",
    "notsure": "Don't know", 
}
# Creating company size categories
COMPANY_SIZE_ORDER=["1-5", "6-25", "26-100", "100-500", "500-1000", "More than 1000"]

def _norm_str(x) -> str | None:
    if pd.isna(x):
        return None
    s=str(x).strip()
    return s if s != "" else None

def normalize_yes_no_unknown(x) -> str:
    s= _norm_str(x)
    if s is None:
        return "Unknown"
    key=s.lower()
    return YES_NO_MAP.get(key, s)

# to normalize gender responses
def normalize_gender(x) -> str:
    s= _norm_str(x)
    if s is None:
        return "Prefer not to say / Unknown"
    t= s.strip().lower()
    # male detection
    if re.search(r"\b(male|man|m)\b", t) and "female" not in t:
        return "Male"
    # female detection
    if re.search(r"\b(female|woman|f)\b", t):
        return "Female"

    # non-binary
    if any(k in t for k in ["non", "nb", "enby", "genderqueer", "trans", "queer", "fluid", "agender"]):
        return "Non-binary / Other"

    # other typos
    if t in ["make", "mail", "mal"]:
        return "Male"

    return "Non-binary / Other"
# year from timestamp column
def parse_year_from_timestamp(series: pd.Series) -> pd.Series:
    ts=pd.to_datetime(series, errors="coerce")
    return ts.dt.year

# to convert to numeric and remove unrealistic values
def clean_age(series: pd.Series) -> pd.Series:
    age=pd.to_numeric(series, errors="coerce")
    age=age.where((age >= 13) & (age <= 80))
    return age  

# age bins for grouped analysis
def make_age_bin(age: pd.Series) -> pd.Series:
    bins=[0, 20, 30, 40, 50, 100]
    labels=["<20", "20–29", "30–39", "40–49", "50+"]
    return pd.cut(age, bins=bins, labels=labels, right=False, include_lowest=True)

def map_country_to_region(country: str | None) -> str:
    if country is None:
        return "Unknown"

    c=country.strip().lower()
    north_america = {"united states", "canada", "mexico"}
    europe={"united kingdom", "ireland", "germany", "france", "netherlands", "sweden",
              "norway", "denmark", "finland", "belgium", "switzerland", "austria",
              "spain", "italy", "portugal", "poland", "czech republic", "romania",
              "hungary", "greece", "russia", "ukraine"}
    oceania={"australia", "new zealand"}
    asia={"india", "china", "japan", "singapore", "philippines",
            "pakistan", "israel", "taiwan", "south korea"}
    south_america={"brazil", "argentina", "chile", "colombia", "peru"}
    africa={"south africa", "nigeria", "kenya", "egypt", "morocco"}
    if c in north_america:
        return "North America"
    if c in europe:
        return "Europe"
    if c in oceania:
        return "Oceania"
    if c in asia:
        return "Asia"
    if c in south_america:
        return "South America"
    if c in africa:
        return "Africa"

    return "Other / Unknown"
def process(df: pd.DataFrame) -> pd.DataFrame:
    col_map={
        "Timestamp": "timestamp",
        "Age": "age",
        "Gender": "gender_raw",
        "Country": "country",
        "state": "state",
        "self_employed": "self_employed",
        "family_history": "family_history",
        "treatment": "treatment",
        "work_interfere": "work_interfere",
        "no_employees": "company_size",
        "remote_work": "remote_work",
        "tech_company": "tech_company",
        "benefits": "benefits",
        "care_options": "care_options",
        "wellness_program": "wellness_program",
        "seek_help": "seek_help",
        "anonymity": "anonymity",
        "leave": "leave",
        "mental_health_consequence": "mental_health_consequence",
        "phys_health_consequence": "phys_health_consequence",
        "coworkers": "coworkers",
        "supervisor": "supervisor",
        "mental_health_interview": "mental_health_interview",
        "phys_health_interview": "phys_health_interview",
        "mental_vs_physical": "mental_vs_physical",
        "obs_consequence": "obs_consequence",
        "comments": "comments",
    }
    df=df.rename(columns={k: v for k, v in col_map.items() if k in df.columns}).copy()
    df["year"]=parse_year_from_timestamp(df["timestamp"]) if "timestamp" in df.columns else pd.NA
    if "age" in df.columns:
        df["age"]=clean_age(df["age"])
        df["age_bin"]=make_age_bin(df["age"])
    if "gender_raw" in df.columns:
        df["gender"] = df["gender_raw"].apply(normalize_gender)
    else:
        df["gender"] = "Prefer not to say / Unknown"

    if "country" in df.columns:
        df["country"] = df["country"].astype("string")
        df["region"] = df["country"].apply(lambda x: map_country_to_region(_norm_str(x)))

    # company size categorical ordering
    if "company_size" in df.columns:
        df["company_size"] = df["company_size"].astype("string").fillna("Unknown")
        df["company_size"] = df["company_size"].where(
            df["company_size"].isin(COMPANY_SIZE_ORDER), "Unknown"
        )
        df["company_size"] = pd.Categorical(
            df["company_size"],
            categories=COMPANY_SIZE_ORDER + ["Unknown"],
            ordered=True
        )
    else:
        df["company_size"] = pd.Categorical(
            ["Unknown"] * len(df),
            categories=COMPANY_SIZE_ORDER + ["Unknown"],
            ordered=True,
        )
    # yes/no columns
    yn_cols=[
        "self_employed", "family_history", "treatment", "remote_work",
        "tech_company", "benefits", "care_options", "wellness_program",
        "seek_help", "anonymity", "mental_health_consequence",
        "phys_health_consequence", "coworkers", "supervisor",
        "mental_health_interview", "phys_health_interview",
        "mental_vs_physical", "obs_consequence",
    ]
    for c in yn_cols:
        if c in df.columns:
            df[c]=df[c].apply(normalize_yes_no_unknown)
    if "comments" in df.columns:
        df=df.drop(columns=["comments"])
    # to chosse need columns for dashboard
    keep=[
        "year", "age", "age_bin", "gender",
        "country", "region", "state", "company_size",
        "benefits", "treatment", "work_interfere",
        "remote_work", "family_history", "self_employed",
        "tech_company", "care_options", "wellness_program",
        "seek_help", "anonymity",
    ]
    keep=[c for c in keep if c in df.columns]
    out=df[keep].copy()

    return out
def main() -> None:
    df_raw=load_raw()
    df_clean=process(df_raw)
    DATA_PROCESSED.parent.mkdir(parents=True, exist_ok=True)
    df_clean.to_parquet(DATA_PROCESSED, index=False)
    csv_path=Path(str(DATA_PROCESSED)).with_suffix(".csv")
    df_clean.to_csv(csv_path, index=False)

    print(f"Wrote processed data: {DATA_PROCESSED} (rows={len(df_clean)}, cols={df_clean.shape[1]})")
    print(f"Wrote processed data: {csv_path}")


if __name__ == "__main__":
    main()