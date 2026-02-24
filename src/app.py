# src/app/app.py
from pathlib import Path
import pandas as pd

import altair as alt
from dash import Dash, html, dcc, Input, Output
import dash_bootstrap_components as dbc

# Make Altair safer for larger tables
alt.data_transformers.disable_max_rows()

# -----------------------------
# Paths & Load
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent          # .../src/app
PROJECT_ROOT = BASE_DIR.parent              # project root
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "cleaned.csv"

df = pd.read_csv(DATA_PATH)

# -----------------------------
# Helpers
# -----------------------------
def _ensure_str_series(s: pd.Series) -> pd.Series:
    return s.astype("string").fillna("<missing>")

def _order_yes_no_unknown(values):
    priority = ["Yes", "No", "Don't know", "Not sure", "<missing>"]
    vals = list(pd.unique([v for v in values if pd.notna(v)]))
    ordered = [v for v in priority if v in vals]
    tail = sorted([v for v in vals if v not in ordered])
    return ordered + tail

def _order_work_interfere(values):
    priority = ["Never", "Rarely", "Sometimes", "Often", "Don't know", "<missing>"]
    vals = list(pd.unique([v for v in values if pd.notna(v)]))
    ordered = [v for v in priority if v in vals]
    tail = sorted([v for v in vals if v not in ordered])
    return ordered + tail

def _order_age_bin(values):
    vals = [v for v in values if pd.notna(v)]
    def key(v):
        try:
            return int(str(v).split("-")[0].strip())
        except Exception:
            return 10**9
    return sorted(pd.unique(vals), key=key)

def _order_company_size(values):
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
    return (
        alt.Chart(pd.DataFrame({"msg": [msg]}))
        .mark_text(size=14)
        .encode(text="msg:N")
        .properties(width="container", height=260)
    )

def as_iframe(chart: alt.Chart, height=280):
    """
    Critical fix: inline=True so Vega scripts are embedded (no CDN dependency).
    """
    chart = chart.properties(height=height, width="container")
    return html.Iframe(
        srcDoc=chart.to_html(fullhtml=False, inline=True),
        style={"width": "100%", "height": f"{height+90}px", "border": "0"},
    )

def filtered_df(dff, year, region, genders, age_bins, company_sizes, remote_work):
    if year:
        dff = dff[dff["year"] == int(year)]
    if region:
        dff = dff[dff["region"].isin(region)]
    if genders:
        dff = dff[dff["gender"].isin(genders)]
    if age_bins:
        dff = dff[dff["age_bin"].isin(age_bins)]
    if company_sizes:
        dff = dff[dff["company_size"].isin(company_sizes)]
    if remote_work:
        dff = dff[dff["remote_work"].isin(remote_work)]
    return dff

# -----------------------------
# Charts
# -----------------------------
def chart_treatment_by_group(dff: pd.DataFrame, group_by="age_bin", show_as="percent"):
    if dff is None or len(dff) == 0:
        return _no_data_chart("No data for Chart 1 (Treatment by group).")

    g = group_by
    if g not in dff.columns:
        return _no_data_chart(f"Missing column: {g}")

    tmp = dff.copy()
    tmp["treatment"] = _ensure_str_series(tmp["treatment"])
    tmp[g] = _ensure_str_series(tmp[g])
    tmp["gender"] = _ensure_str_series(tmp["gender"])

    agg = (
        tmp.groupby([g, "gender"], dropna=False)
        .agg(n=("treatment", "size"), treat_yes=("treatment", lambda x: (x == "Yes").sum()))
        .reset_index()
    )
    agg["rate"] = (agg["treat_yes"] / agg["n"]) * 100

    if g == "age_bin":
        order = _order_age_bin(tmp[g].unique())
    elif g == "company_size":
        order = _order_company_size(tmp[g].unique())
    else:
        order = sorted(tmp[g].unique().tolist())

    if show_as == "count":
        y_field = "treat_yes:Q"
        y_title = "Treatment (Yes) count"
        tooltip = [alt.Tooltip(g + ":N"), alt.Tooltip("gender:N"),
                   alt.Tooltip("treat_yes:Q"), alt.Tooltip("n:Q")]
    else:
        y_field = "rate:Q"
        y_title = "Treatment rate (%)"
        tooltip = [alt.Tooltip(g + ":N"), alt.Tooltip("gender:N"),
                   alt.Tooltip("rate:Q", format=".1f"), alt.Tooltip("n:Q")]

    chart = (
        alt.Chart(agg)
        .mark_bar()
        .encode(
            x=alt.X(f"{g}:N", sort=order, title=g.replace("_", " ").title()),
            y=alt.Y(y_field, title=y_title),
            color=alt.Color("gender:N", title="Gender"),
            tooltip=tooltip,
        )
        .properties(title="Treatment by group")
    )

    return chart.configure_title(fontSize=14).configure_axis(labelFontSize=11, titleFontSize=12)

def chart_interfere_heatmap(dff: pd.DataFrame, metric="row_percent"):
    if dff is None or len(dff) == 0:
        return _no_data_chart("No data for Chart 2 (Work interference heatmap).")

    if "work_interfere" not in dff.columns or "treatment" not in dff.columns:
        return _no_data_chart("Missing required columns for Chart 2.")

    tmp = dff.copy()
    tmp["work_interfere"] = _ensure_str_series(tmp["work_interfere"])
    tmp["treatment"] = _ensure_str_series(tmp["treatment"])

    counts = (
        tmp.groupby(["work_interfere", "treatment"], dropna=False)
        .size()
        .reset_index(name="count")
    )

    if metric == "count":
        counts["value"] = counts["count"]
        legend_title = "Count"
        tooltip = [
            alt.Tooltip("work_interfere:N"),
            alt.Tooltip("treatment:N"),
            alt.Tooltip("count:Q"),
        ]
    else:
        totals = counts.groupby("work_interfere")["count"].transform("sum")
        counts["value"] = (counts["count"] / totals) * 100
        legend_title = "Row %"
        tooltip = [
            alt.Tooltip("work_interfere:N"),
            alt.Tooltip("treatment:N"),
            alt.Tooltip("value:Q", format=".1f"),
            alt.Tooltip("count:Q"),
        ]

    x_order = _order_work_interfere(tmp["work_interfere"].unique())
    y_order = _order_yes_no_unknown(tmp["treatment"].unique())

    chart = (
        alt.Chart(counts)
        .mark_rect()
        .encode(
            x=alt.X("work_interfere:N", sort=x_order, title="Work interference"),
            y=alt.Y("treatment:N", sort=y_order, title="Treatment"),
            color=alt.Color("value:Q", title=legend_title),
            tooltip=tooltip,
        )
        .properties(title="Work interference × Treatment")
    )

    return chart.configure_title(fontSize=14).configure_axis(labelFontSize=11, titleFontSize=12)

def chart_support_vs_treatment(dff: pd.DataFrame, factor="benefits"):
    if dff is None or len(dff) == 0:
        return _no_data_chart(f"No data for Chart (Support: {factor}).")

    if factor not in dff.columns or "treatment" not in dff.columns:
        return _no_data_chart(f"Missing required columns for factor: {factor}")

    tmp = dff.copy()
    tmp[factor] = _ensure_str_series(tmp[factor])
    tmp["treatment"] = _ensure_str_series(tmp["treatment"])

    counts = (
        tmp.groupby([factor, "treatment"], dropna=False)
        .size()
        .reset_index(name="count")
    )
    totals = counts.groupby(factor)["count"].transform("sum")
    counts["pct"] = (counts["count"] / totals) * 100

    x_order = _order_yes_no_unknown(tmp[factor].unique())
    y_order = _order_yes_no_unknown(tmp["treatment"].unique())

    nice_title = factor.replace("_", " ").title()

    chart = (
        alt.Chart(counts)
        .mark_bar()
        .encode(
            x=alt.X(f"{factor}:N", sort=x_order, title=nice_title),
            y=alt.Y("pct:Q", stack="normalize", title="Share within group"),
            color=alt.Color("treatment:N", sort=y_order, title="Treatment"),
            tooltip=[
                alt.Tooltip(f"{factor}:N", title=nice_title),
                alt.Tooltip("treatment:N", title="Treatment"),
                alt.Tooltip("pct:Q", title="Percent", format=".1f"),
                alt.Tooltip("count:Q", title="Count"),
            ],
        )
        .properties(title=f"{nice_title} vs Treatment (100% stacked)")
    )

    return chart.configure_title(fontSize=14).configure_axis(labelFontSize=11, titleFontSize=12)

def kpi_cards(dff: pd.DataFrame):
    n = len(dff)

    def pct(col, val="Yes"):
        if n == 0:
            return 0.0
        return (dff[col].astype(str).eq(val).mean()) * 100

    cards = dbc.Row(
        [
            dbc.Col(dbc.Card(dbc.CardBody([html.Div("N", className="text-muted"), html.H4(f"{n}")]))),
            dbc.Col(dbc.Card(dbc.CardBody([html.Div("Treatment rate", className="text-muted"), html.H4(f"{pct('treatment'):.1f}%")]))),
            dbc.Col(dbc.Card(dbc.CardBody([html.Div("Benefits available", className="text-muted"), html.H4(f"{pct('benefits'):.1f}%")]))),
            dbc.Col(dbc.Card(dbc.CardBody([html.Div("Family history", className="text-muted"), html.H4(f"{pct('family_history'):.1f}%")]))),
        ],
        className="g-2",
    )
    return cards

# -----------------------------
# App
# -----------------------------
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

years = sorted(df["year"].dropna().unique())
regions = sorted(df["region"].dropna().unique())
genders = sorted(df["gender"].dropna().unique())
age_bins = _order_age_bin(df["age_bin"].dropna().unique())
company_sizes = _order_company_size(df["company_size"].dropna().unique())
remote_vals = sorted(df["remote_work"].dropna().unique())

filters = dbc.Card(
    dbc.CardBody(
        [
            html.H5("Filters"),
            html.Label("Year"),
            dcc.Dropdown(years, years[0] if years else None, id="f-year", clearable=False),

            html.Br(),
            html.Label("Region"),
            dcc.Dropdown(
                regions,
                ["North America"] if "North America" in regions else regions[:1],
                id="f-region",
                multi=True
            ),

            html.Hr(),
            html.Label("Gender"),
            dcc.Dropdown(genders, genders, id="f-gender", multi=True),

            html.Br(),
            html.Label("Age bin"),
            dcc.Dropdown(age_bins, age_bins, id="f-agebin", multi=True),

            html.Br(),
            html.Label("Company size"),
            dcc.Dropdown(company_sizes, id="f-company", multi=True),

            html.Br(),
            html.Label("Remote work"),
            dcc.Dropdown(remote_vals, id="f-remote", multi=True),
        ]
    ),
    className="h-100",
)

legend = dbc.Card(
    dbc.CardBody(
        [
            html.H5("Legend & Notes"),
            html.P("All charts update based on the filters on the left."),
            html.Hr(),
            html.H6("Definitions"),
            html.Ul(
                [
                    html.Li("treatment: whether respondent has sought treatment for mental health."),
                    html.Li("work_interfere: how often mental health interferes with work."),
                    html.Li("benefits/care_options/wellness_program/seek_help/anonymity: workplace support indicators."),
                ]
            ),
            html.Hr(),
            html.H6("Encodings"),
            html.Ul(
                [
                    html.Li("Chart 1: bars show treatment rate (%) by age group; colors represent gender."),
                    html.Li("Chart 2: heatmap shows treatment distribution by work interference (row %)."),
                    html.Li("Chart 3/4: 100% stacked bars show treatment share within each support category."),
                ]
            ),
            html.P(
                "Data includes 'Don't know/Unknown/<missing>' categories for transparency.",
                className="text-muted",
                style={"fontSize": "0.9em"},
            ),
        ]
    ),
    className="h-100",
)

app.layout = dbc.Container(
    fluid=True,
    children=[
        html.H2("Workplace Mental Health Dashboard (2014 Survey)"),
        html.P("Explore treatment rates and workplace factors across groups.", className="text-muted"),

        dbc.Row(
            [
                dbc.Col(filters, width=3),

                dbc.Col(
                    [
                        html.Div(id="kpi-area"),
                        html.Br(),
                        dbc.Row(
                            [
                                dbc.Col(html.Div(id="chart-1"), width=6),
                                dbc.Col(html.Div(id="chart-2"), width=6),
                            ],
                            className="g-2",
                        ),
                        html.Br(),
                        dbc.Row(
                            [
                                dbc.Col(html.Div(id="chart-3"), width=6),
                                dbc.Col(html.Div(id="chart-4"), width=6),
                            ],
                            className="g-2",
                        ),
                    ],
                    width=6,
                ),

                dbc.Col(legend, width=3),
            ],
            className="g-3",
        ),
    ],
)

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
    dff = filtered_df(df, year, region, gender, agebin, company, remote)

    c1 = as_iframe(chart_treatment_by_group(dff, group_by="age_bin", show_as="percent"), height=300)
    c2 = as_iframe(chart_interfere_heatmap(dff, metric="row_percent"), height=300)
    c3 = as_iframe(chart_support_vs_treatment(dff, factor="benefits"), height=300)
    c4 = as_iframe(chart_support_vs_treatment(dff, factor="seek_help"), height=300)

    return kpi_cards(dff), c1, c2, c3, c4

if __name__ == "__main__":
    app.run(debug=True)
