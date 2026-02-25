from pathlib import Path
import pandas as pd
import traceback
import altair as alt
from dash import Dash, html, dcc, Input, Output
import dash_bootstrap_components as dbc

# Allow Altair to work with larger datasets without throwing row limit errors
alt.data_transformers.disable_max_rows()

# -----------------------------
# Paths & Load
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "cleaned.csv"

# Make sure the dataset exists before loading
if not DATA_PATH.exists():
    raise FileNotFoundError(f"Missing data file: {DATA_PATH}. Did you commit data/processed/cleaned.csv?")
df = pd.read_csv(DATA_PATH)

# -----------------------------
# Helpers
# -----------------------------

def _ensure_str_series(s: pd.Series) -> pd.Series:
    """
    Convert a pandas Series to string type and replace missing values.

    This helps avoid errors in Altair and keeps missing values visible
    instead of dropping them.
    """
    # Convert everything to string and fill missing values
    return s.astype("string").fillna("<missing>")


def _order_yes_no_unknown(values):
    """
    Order Yes/No style categories in a consistent and readable way.

    Instead of alphabetical order, we force a logical order:
    Yes → No → Don't know → Not sure → Missing
    """
    priority = ["Yes", "No", "Don't know", "Not sure", "<missing>"]
    vals = list(pd.unique([v for v in values if pd.notna(v)]))

    # Put priority values first
    ordered = [v for v in priority if v in vals]

    # Add any extra categories at the end
    tail = sorted([v for v in vals if v not in ordered])
    return ordered + tail


def _order_work_interfere(values):
    """
    Order work interference values logically from low to high.

    This makes the heatmap easier to understand instead of
    showing categories alphabetically.
    """
    priority = ["Never", "Rarely", "Sometimes", "Often", "Don't know", "<missing>"]
    vals = list(pd.unique([v for v in values if pd.notna(v)]))

    ordered = [v for v in priority if v in vals]
    tail = sorted([v for v in vals if v not in ordered])

    return ordered + tail


def _order_age_bin(values):
    """
    Sort age groups numerically.

    Without this, age bins would sort alphabetically
    (which looks wrong on charts).
    """
    vals = [v for v in values if pd.notna(v)]

    def key(v):
        try:
            # Extract the starting number of the age bin
            return int(str(v).split("-")[0].strip())
        except Exception:
            return 10**9

    return sorted(pd.unique(vals), key=key)


def _order_company_size(values):
    """
    Sort company size categories numerically.

    Ensures that company sizes appear in the correct order
    instead of alphabetical order.
    """
    vals = [v for v in values if pd.notna(v)]

    def key(v):
        s = str(v).strip()
        try:
            if "+" in s:
                return int(s.replace("+", ""))
            return int(s.split("-")[0])
        except Exception:
            return 10**9

    return sorted(pd.unique(vals), key=key)


def _no_data_chart(msg="No data for current filters."):
    """
    Create a placeholder chart when no data is available.

    This prevents the dashboard from crashing and
    shows a helpful message instead.
    """
    return (
        alt.Chart(pd.DataFrame({"msg": [msg]}))
        .mark_text(size=14)
        .encode(text="msg:N")
        .properties(width="container", height=260)
    )


def as_iframe(chart: alt.Chart, height=280):
    """
    Convert an Altair chart into an HTML iframe.

    Dash doesn't directly support Altair charts, so we embed
    the chart inside an iframe instead.

    inline=True ensures Vega scripts are included so the
    chart works without internet.
    """
    chart = chart.properties(height=height, width="container")

    return html.Iframe(
        srcDoc=chart.to_html(inline=True),
        style={"width": "100%", "height": f"{height+90}px", "border": "0"},
    )


def filtered_df(dff, year, region, genders, age_bins, company_sizes, remote_work):
    """
    Apply all dashboard filters to the dataset.

    Each filter is optional and only applied if selected.
    Returns the filtered dataframe.
    """

    # Filter by year
    if year:
        dff = dff[dff["year"] == int(year)]

    # Filter by region
    if region:
        dff = dff[dff["region"].isin(region)]

    # Filter by gender
    if genders:
        dff = dff[dff["gender"].isin(genders)]

    # Filter by age group
    if age_bins:
        dff = dff[dff["age_bin"].isin(age_bins)]

    # Filter by company size
    if company_sizes:
        dff = dff[dff["company_size"].isin(company_sizes)]

    # Filter by remote work
    if remote_work:
        dff = dff[dff["remote_work"].isin(remote_work)]

    return dff


# -----------------------------
# Charts
# -----------------------------

def chart_treatment_by_group(dff: pd.DataFrame, group_by="age_bin", show_as="percent"):
    """
    Create a grouped bar chart showing treatment rates by group.

    The chart compares treatment rates across demographic groups
    such as age or company size and splits by gender.
    """

    # If no data after filtering
    if dff is None or len(dff) == 0:
        return _no_data_chart("No data for Chart 1 (Treatment by group).")

    g = group_by

    # Check column exists
    if g not in dff.columns:
        return _no_data_chart(f"Missing column: {g}")

    tmp = dff.copy()

    # Convert columns to strings
    tmp["treatment"] = _ensure_str_series(tmp["treatment"])
    tmp[g] = _ensure_str_series(tmp[g])
    tmp["gender"] = _ensure_str_series(tmp["gender"])

    # Count treatment cases
    agg = (
        tmp.groupby([g, "gender"], dropna=False)
        .agg(
            n=("treatment", "size"),
            treat_yes=("treatment", lambda x: (x == "Yes").sum())
        )
        .reset_index()
    )

    # Calculate percentage
    agg["rate"] = (agg["treat_yes"] / agg["n"]) * 100

    # Choose correct ordering
    if g == "age_bin":
        order = _order_age_bin(tmp[g].unique())
    elif g == "company_size":
        order = _order_company_size(tmp[g].unique())
    else:
        order = sorted(tmp[g].unique().tolist())

    # Decide whether to show percent or count
    if show_as == "count":
        y_field = "treat_yes:Q"
        y_title = "Treatment (Yes) count"
    else:
        y_field = "rate:Q"
        y_title = "Treatment rate (%)"

    chart = (
        alt.Chart(agg)
        .mark_bar()
        .encode(
            x=alt.X(f"{g}:N", sort=order, title=g.replace("_", " ").title()),
            y=alt.Y(y_field, title=y_title),
            color=alt.Color("gender:N", title="Gender"),
        )
        .properties(title="Treatment by group")
    )

    return chart


def chart_interfere_heatmap(dff: pd.DataFrame, metric="row_percent"):
    """
    Create a heatmap showing treatment vs work interference.

    Shows how often mental health interferes with work
    compared to treatment status.
    """

    if dff is None or len(dff) == 0:
        return _no_data_chart("No data for Chart 2.")

    tmp = dff.copy()

    tmp["work_interfere"] = _ensure_str_series(tmp["work_interfere"])
    tmp["treatment"] = _ensure_str_series(tmp["treatment"])

    # Count combinations
    counts = (
        tmp.groupby(["work_interfere", "treatment"])
        .size()
        .reset_index(name="count")
    )

    # Convert to percentages
    totals = counts.groupby("work_interfere")["count"].transform("sum")
    counts["value"] = (counts["count"] / totals) * 100

    chart = (
        alt.Chart(counts)
        .mark_rect()
        .encode(
            x="work_interfere:N",
            y="treatment:N",
            color="value:Q",
        )
        .properties(title="Work interference vs Treatment")
    )

    return chart


def chart_support_vs_treatment(dff: pd.DataFrame, factor="benefits"):
    """
    Create a stacked bar chart comparing workplace support and treatment.

    Shows how workplace support factors relate to treatment rates.
    """

    if dff is None or len(dff) == 0:
        return _no_data_chart("No data available.")

    tmp = dff.copy()

    tmp[factor] = _ensure_str_series(tmp[factor])
    tmp["treatment"] = _ensure_str_series(tmp["treatment"])

    counts = (
        tmp.groupby([factor, "treatment"])
        .size()
        .reset_index(name="count")
    )

    totals = counts.groupby(factor)["count"].transform("sum")
    counts["pct"] = (counts["count"] / totals) * 100

    chart = (
        alt.Chart(counts)
        .mark_bar()
        .encode(
            x=f"{factor}:N",
            y="pct:Q",
            color="treatment:N",
        )
        .properties(title=f"{factor} vs Treatment")
    )

    return chart


def kpi_cards(dff: pd.DataFrame):
    """
    Create KPI summary cards.

    Shows:
    - Total sample size
    - Treatment rate
    - Benefits availability
    - Family history rate
    """

    n = len(dff)

    def pct(col):
        if n == 0:
            return None
        return (dff[col].astype(str) == "Yes").mean() * 100

    return dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([html.H4(n), html.Div("Sample Size")]))),
        dbc.Col(dbc.Card(dbc.CardBody([html.H4(f"{pct('treatment'):.1f}%"), html.Div("Treatment Rate")]))),
    ])


@app.callback(
    Output("kpi-area", "children"),
    Output("chart-1", "children"),
    Output("chart-2", "children"),
    Output("chart-3", "children"),
    Output("chart-4", "children"),
    Input("f-year", "value"),
    Input("f-region", "value"),
    Input("f-gender", "value"),
    Input("f-agebin", "value"),
    Input("f-company", "value"),
    Input("f-remote", "value"),
)
def update(year, region, gender, agebin, company, remote):
    """
    Main dashboard update function.

    This function runs whenever a filter changes.
    It filters the data and updates all charts.
    """

    try:
        # Apply filters
        dff = filtered_df(df, year, region, gender, agebin, company, remote)

        # Create charts
        c1 = as_iframe(chart_treatment_by_group(dff), 300)
        c2 = as_iframe(chart_interfere_heatmap(dff), 300)
        c3 = as_iframe(chart_support_vs_treatment(dff, "benefits"), 300)
        c4 = as_iframe(chart_support_vs_treatment(dff, "seek_help"), 300)

        return kpi_cards(dff), c1, c2, c3, c4

    except Exception as e:
        traceback.print_exc()
        return html.Div(f"Error: {e}"), None, None, None, None


if __name__ == "__main__":
    app.run(debug=True)