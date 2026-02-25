import pandas as pd
# to import functions to load raw datasets
from src.data.load_raw import load_raw
from src.config import REPORT_EDA

# here the output will be eturned as a string
def make_eda_report(df: pd.DataFrame) -> str:
    
    # to make a list to store lines 
    lines=[]
    
    # to have the dataset information
    lines.append("# EDA Summary (Raw Data)\n")
    lines.append(f"- Rows: {df.shape[0]}\n")   
    lines.append(f"- Columns: {df.shape[1]}\n") 

    # to have the column data types
    lines.append("## Column Types\n")
    lines.append(df.dtypes.astype(str).to_frame("dtype").to_markdown())
    lines.append("\n")
    
    # here it is to find the percentage of the missing values per columns
    lines.append("## Missing Rate (Top 20)\n")
    miss = (df.isna().mean().sort_values(ascending=False)*100).round(2)
    
    # to add the top 20 columns with highest missing rate
    lines.append(miss.head(20).to_frame("missing_%").to_markdown())
    lines.append("\n")
    
    # here it is to add first 10 object-type columns
    cat_cols=[c for c in df.columns if df[c].dtype == "object"][:10]
    lines.append("## Categorical Value Counts (sample)\n")
    for c in cat_cols:
        lines.append(f"### {c}\n")
        # Convert to string type and replace missing with label
        s=df[c].astype("string").fillna("<missing>")
        # Top 10 most frequent values
        vc = (s.value_counts(dropna=False).head(10).rename_axis("value").reset_index(name="count"))
        lines.append(vc.to_markdown(index=False))
        lines.append("\n")
        return "\n".join(lines)
def main():
    df=load_raw()
    REPORT_EDA.parent.mkdir(parents=True, exist_ok=True)
    REPORT_EDA.write_text(make_eda_report(df),encoding="utf-8")
    print(f"Wrote: {REPORT_EDA}")
if __name__ == "__main__":
    main()