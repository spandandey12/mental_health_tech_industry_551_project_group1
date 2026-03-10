from pathlib import Path
import pandas as pd
import traceback
import altair as alt
from dash import Dash, html, dcc, Input, Output
import dash_bootstrap_components as dbc

# Make Altair safer for larger tables
alt.data_transformers.disable_max_rows()

# -----------------------------
# Paths & Load
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "cleaned.csv"

if not DATA_PATH.exists():
    raise FileNotFoundError(f"Missing data file: {DATA_PATH}. Did you commit data/processed/cleaned.csv?")
df = pd.read_csv(DATA_PATH)

# -----------------------------
# Helpers
# -----------------------------
def _ensure_str_series(s: pd.Series) -> pd.Series:
    """
    Convert a pandas Series to string type and replace missing values.

    Parameters
    ----------
    s : pd.Series
        Input series that may contain missing values.

    Returns
    -------
    pd.Series
        String-formatted series with missing values replaced by '<missing>'.
    """
    return s.astype("string").fillna("<missing>")

def _order_yes_no_unknown(values):
    """
       Return a consistent display order for yes/no-style categorical values.

       Parameters
       ----------
       values : iterable
           Collection of category values.

       Returns
       -------
       list
           Ordered list of category labels for plotting.
       """
    priority = ["Yes", "No", "Don't know", "Not sure", "<missing>"]
    vals = list(pd.unique([v for v in values if pd.notna(v)]))
    ordered = [v for v in priority if v in vals]
    tail = sorted([v for v in vals if v not in ordered])
    return ordered + tail

def _order_work_interfere(values):
    """
    Return a consistent display order for the work_interfere variable.

    Parameters
    ----------
    values : iterable
        Collection of work interference category values.

    Returns
    -------
    list
        Ordered list of work interference labels for plotting.
    """
    priority = ["Never", "Rarely", "Sometimes", "Often", "Don't know", "<missing>"]
    vals = list(pd.unique([v for v in values if pd.notna(v)]))
    ordered = [v for v in priority if v in vals]
    tail = sorted([v for v in vals if v not in ordered])
    return ordered + tail

def _order_age_bin(values):
    """
    Sort age-bin labels by the lower bound of each age range.

    Parameters
    ----------
    values : iterable
        Collection of age-bin labels such as '20-29' or '50+'.

    Returns
    -------
    list
        Ordered list of age-bin labels.
    """
    vals = [v for v in values if pd.notna(v)]
    def key(v):
        try:
            return int(str(v).split("-")[0].strip())
        except Exception:
            return 10**9
    return sorted(pd.unique(vals), key=key)

def _order_company_size(values):
    """
    Sort company-size labels by the lower bound of each size range.

    Parameters
    ----------
    values : iterable
        Collection of company size labels such as '1-5' or '1000+'.

    Returns
    -------
    list
        Ordered list of company-size labels.
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
    Create a fallback Altair text chart when no data is available.

    Parameters
    ----------
    msg : str, default="No data for current filters."
        Message displayed in the placeholder chart.

    Returns
    -------
    alt.Chart
        Altair chart containing a text message.
    """
    return (
        alt.Chart(pd.DataFrame({"msg": [msg]}))
        .mark_text(size=14)
        .encode(text="msg:N")
        .properties(width="container", height=260)
    )

def as_iframe(chart: alt.Chart, height=260):
    def as_iframe(chart: alt.Chart, height=260):
        """
        Render an Altair chart inside a Dash HTML iframe.

        Parameters
        ----------
        chart : alt.Chart
            Altair chart object to render.
        height : int, default=260
            Height of the iframe in pixels.

        Returns
        -------
        html.Iframe
            Dash iframe component containing the chart HTML.
        """
    view_h = max(120, height - 130)
    chart = chart.properties(height=view_h, width="container")
    return html.Iframe(
        srcDoc=chart.to_html(inline=True, embed_options={"actions": False}),
        style={"width": "100%", "height": f"{height}px", "border": "0"},
    )

def filtered_df(dff, year, region, genders, age_bins, company_sizes, remote_work):
    """
    Filter the dataset using the selected dashboard controls.

    Parameters
    ----------
    dff : pd.DataFrame
        Input dataframe to filter.
    year : int or None
        Selected survey year.
    region : list or None
        Selected region values.
    genders : list or None
        Selected gender values.
    age_bins : list or None
        Selected age-bin values.
    company_sizes : list or None
        Selected company-size values.
    remote_work : list or None
        Selected remote work values.

    Returns
    -------
    pd.DataFrame
        Filtered dataframe used for KPI cards and charts.
    """
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
    """
    Create Chart 1: a grouped bar chart of treatment by demographic group.

    Parameters
    ----------
    dff : pd.DataFrame
        Filtered dataframe used for plotting.
    group_by : str, default="age_bin"
        Column used to group respondents, such as age_bin or company_size.
    show_as : str, default="percent"
        Display metric. Use 'percent' for treatment rate or 'count' for counts.

    Returns
    -------
    alt.Chart
        Altair grouped bar chart.
    """
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
        tooltip = [
            alt.Tooltip(g + ":N"),
            alt.Tooltip("gender:N"),
            alt.Tooltip("treat_yes:Q"),
            alt.Tooltip("n:Q"),
        ]
    else:
        y_field = "rate:Q"
        y_title = "Treatment rate (%)"
        tooltip = [
            alt.Tooltip(g + ":N"),
            alt.Tooltip("gender:N"),
            alt.Tooltip("rate:Q", format=".1f"),
            alt.Tooltip("n:Q"),
        ]

    chart = (
        alt.Chart(agg)
        .mark_bar()
        .encode(
            x=alt.X(f"{g}:N", sort=order, title=g.replace("_", " ").title()),
            xOffset=alt.XOffset("gender:N"),   # 关键：并排 grouped bar
            y=alt.Y(y_field, title=y_title),
            color=alt.Color("gender:N", title="Gender"),
            tooltip=tooltip,
        )
        .properties(title="Treatment by group")
    )

    return chart.configure_title(fontSize=14).configure_axis(labelFontSize=11, titleFontSize=12)
# def chart_treatment_by_group(dff: pd.DataFrame, group_by="age_bin", show_as="percent"):
#     if dff is None or len(dff) == 0:
#         return _no_data_chart("No data for Chart 1 (Treatment by group).")
#
#     g = group_by
#     if g not in dff.columns:
#         return _no_data_chart(f"Missing column: {g}")
#
#     tmp = dff.copy()
#     tmp["treatment"] = _ensure_str_series(tmp["treatment"])
#     tmp[g] = _ensure_str_series(tmp[g])
#     tmp["gender"] = _ensure_str_series(tmp["gender"])
#
#     agg = (
#         tmp.groupby([g, "gender"], dropna=False)
#         .agg(n=("treatment", "size"), treat_yes=("treatment", lambda x: (x == "Yes").sum()))
#         .reset_index()
#     )
#     agg["rate"] = (agg["treat_yes"] / agg["n"]) * 100
#
#     if g == "age_bin":
#         order = _order_age_bin(tmp[g].unique())
#     elif g == "company_size":
#         order = _order_company_size(tmp[g].unique())
#     else:
#         order = sorted(tmp[g].unique().tolist())
#
#     if show_as == "count":
#         y_field = "treat_yes:Q"
#         y_title = "Treatment (Yes) count"
#         tooltip = [alt.Tooltip(g + ":N"), alt.Tooltip("gender:N"),
#                    alt.Tooltip("treat_yes:Q"), alt.Tooltip("n:Q")]
#     else:
#         y_field = "rate:Q"
#         y_title = "Treatment rate (%)"
#         tooltip = [alt.Tooltip(g + ":N"), alt.Tooltip("gender:N"),
#                    alt.Tooltip("rate:Q", format=".1f"), alt.Tooltip("n:Q")]
#
#     chart = (
#         alt.Chart(agg)
#         .mark_bar()
#         .encode(
#             x=alt.X(f"{g}:N", sort=order, title=g.replace("_", " ").title()),
#             y=alt.Y(y_field, title=y_title),
#             color=alt.Color("gender:N", title="Gender"),
#             tooltip=tooltip,
#         )
#         .properties(title="Treatment by group")
#     )
#
#     return chart.configure_title(fontSize=14).configure_axis(labelFontSize=11, titleFontSize=12)
def chart_interfere_heatmap(dff: pd.DataFrame, metric="count"):
    """
    Create Chart 2: a bar chart of work interference among respondents
    who sought treatment.

    Parameters
    ----------
    dff : pd.DataFrame
        Filtered dataframe used for plotting.
    metric : str, default="count"
        Metric shown on the y-axis. Use 'count' or 'percent'.

    Returns
    -------
    alt.Chart
        Altair bar chart showing the distribution of work_interfere values.
    """
    if dff is None or len(dff) == 0:
        return _no_data_chart("No data for Chart 2 (Work interference).")

    if "work_interfere" not in dff.columns or "treatment" not in dff.columns:
        return _no_data_chart("Missing required columns for Chart 2.")

    tmp = dff.copy()
    tmp["work_interfere"] = _ensure_str_series(tmp["work_interfere"])
    tmp["treatment"] = _ensure_str_series(tmp["treatment"])

    # 只保留 treatment = Yes
    tmp = tmp[tmp["treatment"] == "Yes"]

    if len(tmp) == 0:
        return _no_data_chart("No treatment='Yes' data for Chart 2.")

    counts = (
        tmp.groupby(["work_interfere"], dropna=False)
        .size()
        .reset_index(name="count")
    )

    total = counts["count"].sum()
    counts["pct"] = (counts["count"] / total) * 100

    x_order = _order_work_interfere(tmp["work_interfere"].unique())

    if metric == "percent":
        y_field = "pct:Q"
        y_title = "Percent of treatment = Yes respondents"
        tooltip = [
            alt.Tooltip("work_interfere:N", title="Work interference"),
            alt.Tooltip("pct:Q", title="Percent", format=".1f"),
            alt.Tooltip("count:Q", title="Count"),
        ]
    else:
        y_field = "count:Q"
        y_title = "Count of treatment = Yes respondents"
        tooltip = [
            alt.Tooltip("work_interfere:N", title="Work interference"),
            alt.Tooltip("count:Q", title="Count"),
            alt.Tooltip("pct:Q", title="Percent", format=".1f"),
        ]

    chart = (
        alt.Chart(counts)
        .mark_bar()
        .encode(
            x=alt.X("work_interfere:N", sort=x_order, title="Work interference"),
            y=alt.Y(y_field, title=y_title),
            tooltip=tooltip,
        )
        .properties(title="Work interference among respondents who sought treatment")
    )

    return chart.configure_title(fontSize=14).configure_axis(labelFontSize=11, titleFontSize=12)
# def chart_interfere_heatmap(dff: pd.DataFrame, metric="row_percent"):
#     if dff is None or len(dff) == 0:
#         return _no_data_chart("No data for Chart 2 (Work interference heatmap).")
#
#     if "work_interfere" not in dff.columns or "treatment" not in dff.columns:
#         return _no_data_chart("Missing required columns for Chart 2.")
#
#     tmp = dff.copy()
#     tmp["work_interfere"] = _ensure_str_series(tmp["work_interfere"])
#     tmp["treatment"] = _ensure_str_series(tmp["treatment"])
#
#     counts = (
#         tmp.groupby(["work_interfere", "treatment"], dropna=False)
#         .size()
#         .reset_index(name="count")
#     )
#
#     if metric == "count":
#         counts["value"] = counts["count"]
#         legend_title = "Count"
#         tooltip = [
#             alt.Tooltip("work_interfere:N"),
#             alt.Tooltip("treatment:N"),
#             alt.Tooltip("count:Q"),
#         ]
#     else:
#         totals = counts.groupby("work_interfere")["count"].transform("sum")
#         counts["value"] = (counts["count"] / totals) * 100
#         legend_title = "Row %"
#         tooltip = [
#             alt.Tooltip("work_interfere:N"),
#             alt.Tooltip("treatment:N"),
#             alt.Tooltip("value:Q", format=".1f"),
#             alt.Tooltip("count:Q"),
#         ]
#
#     x_order = _order_work_interfere(tmp["work_interfere"].unique())
#     y_order = _order_yes_no_unknown(tmp["treatment"].unique())
#
#     chart = (
#         alt.Chart(counts)
#         .mark_rect()
#         .encode(
#             x=alt.X("work_interfere:N", sort=x_order, title="Work interference"),
#             y=alt.Y("treatment:N", sort=y_order, title="Treatment"),
#             color=alt.Color("value:Q", title=legend_title),
#             tooltip=tooltip,
#         )
#         .properties(title="Work interference × Treatment")
#     )
#
#     return chart.configure_title(fontSize=14).configure_axis(labelFontSize=11, titleFontSize=12)

# def chart_support_vs_treatment(dff: pd.DataFrame, factor="benefits"):
#     if dff is None or len(dff) == 0:
#         return _no_data_chart(f"No data for Chart (Support: {factor}).")
#
#     if factor not in dff.columns or "treatment" not in dff.columns:
#         return _no_data_chart(f"Missing required columns for factor: {factor}")
#
#     tmp = dff.copy()
#     tmp[factor] = _ensure_str_series(tmp[factor])
#     tmp["treatment"] = _ensure_str_series(tmp["treatment"])
#
#     counts = (
#         tmp.groupby([factor, "treatment"], dropna=False)
#         .size()
#         .reset_index(name="count")
#     )
#     totals = counts.groupby(factor)["count"].transform("sum")
#     counts["pct"] = (counts["count"] / totals) * 100
#
#     x_order = _order_yes_no_unknown(tmp[factor].unique())
#     y_order = _order_yes_no_unknown(tmp["treatment"].unique())
#
#     nice_title = factor.replace("_", " ").title()
#
#     chart = (
#         alt.Chart(counts)
#         .mark_bar()
#         .encode(
#             x=alt.X(f"{factor}:N", sort=x_order, title=nice_title),
#             y=alt.Y("pct:Q", stack="normalize", title="Share within group"),
#             color=alt.Color("treatment:N", sort=y_order, title="Treatment"),
#             tooltip=[
#                 alt.Tooltip(f"{factor}:N", title=nice_title),
#                 alt.Tooltip("treatment:N", title="Treatment"),
#                 alt.Tooltip("pct:Q", title="Percent", format=".1f"),
#                 alt.Tooltip("count:Q", title="Count"),
#             ],
#         )
#         .properties(title=f"{nice_title} vs Treatment (100% stacked)")
#     )
#
#     return chart.configure_title(fontSize=14).configure_axis(labelFontSize=11, titleFontSize=12)

def chart_support_yes_only(dff: pd.DataFrame, factor="benefits", bar_color="#4C78A8"):
    """
    Create Charts 3 and 4: distributions of workplace support variables
    among respondents who sought treatment.

    Parameters
    ----------
    dff : pd.DataFrame
        Filtered dataframe used for plotting.
    factor : str, default="benefits"
        Support-related variable to visualize, such as benefits or seek_help.

    Returns
    -------
    alt.Chart
        Altair bar chart showing the percentage distribution for the factor.
    """
    if dff is None or len(dff) == 0:
        return _no_data_chart(f"No data for Chart ({factor}).")

    if factor not in dff.columns or "treatment" not in dff.columns:
        return _no_data_chart(f"Missing required columns for factor: {factor}")

    tmp = dff.copy()
    tmp[factor] = _ensure_str_series(tmp[factor])
    tmp["treatment"] = _ensure_str_series(tmp["treatment"])

    # 只保留 treatment = Yes
    tmp = tmp[tmp["treatment"] == "Yes"]

    if len(tmp) == 0:
        return _no_data_chart(f"No treatment='Yes' data for factor: {factor}")

    counts = (
        tmp.groupby([factor], dropna=False)
        .size()
        .reset_index(name="count")
    )
    total = counts["count"].sum()
    counts["pct"] = (counts["count"] / total) * 100

    x_order = _order_yes_no_unknown(tmp[factor].unique())
    nice_title = factor.replace("_", " ").title()

    chart = (
        alt.Chart(counts)
        .mark_bar(color=bar_color)
        .encode(
            x=alt.X(f"{factor}:N", sort=x_order, title=nice_title),
            y=alt.Y("pct:Q", title="Percent of treatment = Yes respondents"),
            tooltip=[
                alt.Tooltip(f"{factor}:N", title=nice_title),
                alt.Tooltip("pct:Q", title="Percent", format=".1f"),
                alt.Tooltip("count:Q", title="Count"),
            ],
        )
        .properties(title=f"{nice_title} among respondents who sought treatment")
    )

    return chart.configure_title(fontSize=14).configure_axis(labelFontSize=11, titleFontSize=12)

def kpi_cards(dff: pd.DataFrame):
    """
    Create KPI summary cards for the filtered dataset.

    Parameters
    ----------
    dff : pd.DataFrame
        Filtered dataframe used to compute summary statistics.

    Returns
    -------
    dbc.Row
        Bootstrap row containing four KPI cards.
    """
    n = len(dff)

    def pct(col, val="Yes"):
        if n == 0:
            return None
        if col not in dff.columns:
            return None
        return (dff[col].astype(str).eq(val).mean()) * 100

    def fmt(x):
        return "N/A" if x is None else f"{x:.1f}%"

    cards = dbc.Row(
        [
            dbc.Col(dbc.Card(dbc.CardBody([html.Div("N", className="text-muted"), html.H4(f"{n}")]))),
            dbc.Col(dbc.Card(dbc.CardBody([html.Div("Treatment rate", className="text-muted"), html.H4(fmt(pct("treatment")))]))),
            dbc.Col(dbc.Card(dbc.CardBody([html.Div("Benefits available", className="text-muted"), html.H4(fmt(pct("benefits")))]))),
            dbc.Col(dbc.Card(dbc.CardBody([html.Div("Family history", className="text-muted"), html.H4(fmt(pct("family_history")))]))),
        ],
        className="g-2",
    )
    return cards

# -----------------------------
# App
# -----------------------------
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title="Workplace Mental Health Dashboard"
)
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
            html.H5("Filters", className="mb-4"),

            html.Label("Year", className="mb-2 fw-semibold"),
            dcc.Dropdown(
                years,
                years[0] if years else None,
                id="f-year",
                clearable=False
            ),

            html.Label("Region", className="mt-4 mb-2 fw-semibold"),
            dcc.Dropdown(
                regions,
                ["North America"] if "North America" in regions else regions[:1],
                id="f-region",
                multi=True
            ),

            html.Hr(className="my-4"),

            html.Label("Gender", className="mb-2 fw-semibold"),
            dcc.Dropdown(
                genders,
                genders,
                id="f-gender",
                multi=True
            ),

            html.Label("Age bin", className="mt-4 mb-2 fw-semibold"),
            dcc.Dropdown(
                age_bins,
                age_bins,
                id="f-agebin",
                multi=True
            ),

            html.Label("Company size", className="mt-4 mb-2 fw-semibold"),
            dcc.Dropdown(
                company_sizes,
                id="f-company",
                multi=True
            ),

            html.Label("Remote work", className="mt-4 mb-2 fw-semibold"),
            dcc.Dropdown(
                remote_vals,
                id="f-remote",
                multi=True
            ),
        ],
        style={
            "padding": "24px",
        },
    ),
    className="h-100 shadow-sm",
)
# filters = dbc.Card(
#     dbc.CardBody(
#         [
#             html.H5("Filters"),
#             html.Label("Year"),
#             dcc.Dropdown(years, years[0] if years else None, id="f-year", clearable=False),
#
#             html.Br(),
#             html.Label("Region"),
#             dcc.Dropdown(
#                 regions,
#                 ["North America"] if "North America" in regions else regions[:1],
#                 id="f-region",
#                 multi=True
#             ),
#
#             html.Hr(),
#             html.Label("Gender"),
#             dcc.Dropdown(genders, genders, id="f-gender", multi=True),
#
#             html.Br(),
#             html.Label("Age bin"),
#             dcc.Dropdown(age_bins, age_bins, id="f-agebin", multi=True),
#
#             html.Br(),
#             html.Label("Company size"),
#             dcc.Dropdown(company_sizes, id="f-company", multi=True),
#
#             html.Br(),
#             html.Label("Remote work"),
#             dcc.Dropdown(remote_vals, id="f-remote", multi=True),
#         ]
#     ),
#     className="h-100",
# )

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
                    html.Li("Chart 2: bar chart shows work interference among respondents who sought treatment."),
                    html.Li("Chart 3/4: bar charts show workplace support distributions among respondents who sought treatment."),
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
    style={
        "height": "calc(100vh - 10px)",
        "overflow": "hidden",
        "paddingBottom": "10px",
    },
    children=[

        html.Div(
            [
                html.H2("Workplace Mental Health Dashboard", style={"marginBottom": "4px"}),
                html.P("Explore treatment rates and workplace factors across groups.",
                       className="text-muted", style={"marginBottom": "8px"}),
            ],
            style={"flex": "0 0 auto"},
        ),


        dbc.Row(
            style={"height": "calc(100vh - 10px - 70px)"},
            className="g-3",
            children=[

                dbc.Col(
                    html.Div(filters, style={"height": "100%", "overflowY": "auto"}),
                    width=3,
                    style={"height": "100%"},
                ),


                dbc.Col(
                    html.Div(
                        [
                            html.Div(id="kpi-area", style={"flex": "0 0 auto"}),
                            html.Div(
                                [
                                    html.Div(id="chart-1", style={"minHeight": "0"}),
                                    html.Div(id="chart-2", style={"minHeight": "0"}),
                                    html.Div(id="chart-3", style={"minHeight": "0"}),
                                    html.Div(id="chart-4", style={"minHeight": "0"}),
                                ],
                                style={
                                    "flex": "1 1 auto",
                                    "minHeight": "0",
                                    "overflowY": "auto",
                                    "display": "grid",
                                    "gridTemplateColumns": "1fr 1fr",
                                    "gap": "10px",
                                    "paddingRight": "6px",
                                },
                            ),
                        ],
                        style={
                            "height": "100%",
                            "display": "flex",
                            "flexDirection": "column",
                            "minHeight": "0",
                        },
                    ),
                    width=6,
                    style={"height": "100%"},
                ),


                dbc.Col(
                    html.Div(legend, style={"height": "100%", "overflowY": "auto"}),
                    width=3,
                    style={"height": "100%"},
                ),
            ],
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
    """
    Update the KPI cards and all charts whenever a dashboard filter changes.

    Parameters
    ----------
    year : int or None
        Selected survey year.
    region : list or None
        Selected region values.
    gender : list or None
        Selected gender values.
    agebin : list or None
        Selected age-bin values.
    company : list or None
        Selected company-size values.
    remote : list or None
        Selected remote work values.

    Returns
    -------
    tuple
        Updated KPI cards and four chart components.
    """
    try:
        print("DATA_PATH:", DATA_PATH)
        print("df.shape:", df.shape)
        print("df.columns:", list(df.columns))

        dff = filtered_df(df, year, region, gender, agebin, company, remote)
        print("filters:", year, region, gender, agebin, company, remote)
        print("dff.shape:", dff.shape)
        h=300
        c1 = as_iframe(chart_treatment_by_group(dff, "age_bin", "percent"), height=h)
        c2 = as_iframe(chart_interfere_heatmap(dff, "row_percent"), height=h)
        c3 = as_iframe(chart_support_yes_only(dff, "benefits","#59A14F"), height=h)
        c4 = as_iframe(chart_support_yes_only(dff, "seek_help", "#F4A261"), height=h)

        return kpi_cards(dff), c1, c2, c3, c4

    except Exception as e:
        print("CALLBACK ERROR:", repr(e))
        traceback.print_exc()
        return html.Div(f"Callback error: {e}"), None, None, None, None

if __name__ == "__main__":
    app.run(debug=True)