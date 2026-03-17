"""
Workplace Mental Health Dashboard

This Dash application provides an interactive dashboard for exploring
mental health treatment patterns and workplace support factors across
demographic and organizational groups.

Main features
-------------
- Filter survey data by year, region, gender, age bin, company size,
  and remote work status.
- Display KPI summary cards for sample size, treatment rate,
  benefits availability, and family history.
- Show interactive Altair charts embedded in Dash via iframes.
- Use a professional dashboard layout with cards, spacing, and
  consistent visual styling.

Author
------
Your project team / course project
"""

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
    raise FileNotFoundError(
        f"Missing data file: {DATA_PATH}. Did you commit data/processed/cleaned.csv?"
    )
df = pd.read_csv(DATA_PATH)


# -----------------------------
# Theme / Style
# -----------------------------
COLORS = {
    "bg": "#F7F9FC",
    "panel": "#FFFFFF",
    "border": "#E5EAF2",
    "text": "#1F2937",
    "muted": "#6B7280",
    "primary": "#2F6BFF",
    "primary_soft": "#EEF4FF",
    "shadow": "0 4px 16px rgba(15, 23, 42, 0.06)",
    "success": "#59A14F",
    "warning": "#F4A261",
    "chart_blue": "#4C78A8",
}

CARD_STYLE = {
    "backgroundColor": COLORS["panel"],
    "border": f"1px solid {COLORS['border']}",
    "borderRadius": "16px",
    "boxShadow": COLORS["shadow"],
}

SECTION_TITLE_STYLE = {
    "fontSize": "15px",
    "fontWeight": "700",
    "color": COLORS["text"],
    "marginBottom": "12px",
}

LABEL_STYLE = {
    "fontSize": "13px",
    "fontWeight": "600",
    "color": COLORS["text"],
    "marginBottom": "6px",
    "display": "block",
}

PAGE_TITLE_STYLE = {
    "fontSize": "2.1rem",
    "fontWeight": "700",
    "color": COLORS["text"],
    "marginBottom": "2px",
}

PAGE_SUBTITLE_STYLE = {
    "color": COLORS["muted"],
    "fontSize": "1rem",
    "marginBottom": "0",
}


def _ensure_str_series(s: pd.Series) -> pd.Series:
    """
    Convert a pandas Series to string type and replace missing values.

    Parameters
    ----------
    s : pd.Series
        Input pandas Series that may contain missing values.

    Returns
    -------
    pd.Series
        A Series cast to pandas string dtype, where missing values are
        replaced with the label '<missing>'.

    Notes
    -----
    This helper ensures categorical variables behave consistently in
    filtering, aggregation, and chart rendering.
    """
    return s.astype("string").fillna("<missing>")


def _order_yes_no_unknown(values):
    """
    Return a consistent category ordering for yes/no/unknown responses.

    Parameters
    ----------
    values : iterable
        Collection of category labels.

    Returns
    -------
    list
        Ordered list of labels with common survey response categories
        placed first, followed by any remaining labels in sorted order.

    Examples
    --------
    Possible output:
    ['Yes', 'No', "Don't know", 'Not sure', '<missing>']
    """
    priority = ["Yes", "No", "Don't know", "Not sure", "<missing>"]
    vals = list(pd.unique([v for v in values if pd.notna(v)]))
    ordered = [v for v in priority if v in vals]
    tail = sorted([v for v in vals if v not in ordered])
    return ordered + tail


def _order_work_interfere(values):
    """
    Return a consistent ordering for work interference categories.

    Parameters
    ----------
    values : iterable
        Collection of work interference labels.

    Returns
    -------
    list
        Ordered list of work interference labels, preserving a logical
        progression from least to most interference, then unknown values.
    """
    priority = ["Never", "Rarely", "Sometimes", "Often", "Don't know", "<missing>"]
    vals = list(pd.unique([v for v in values if pd.notna(v)]))
    ordered = [v for v in priority if v in vals]
    tail = sorted([v for v in vals if v not in ordered])
    return ordered + tail


def _order_age_bin(values):
    """
    Order age bin labels by their lower bound.

    Parameters
    ----------
    values : iterable
        Collection of age bin labels such as '20-29', '30-39', or '50+'.

    Returns
    -------
    list
        Sorted list of age bin labels based on the first numeric value
        in each label.

    Notes
    -----
    Any labels that cannot be parsed numerically are placed at the end.
    """
    vals = [v for v in values if pd.notna(v)]

    def key(v):
        try:
            return int(str(v).split("-")[0].replace("+", "").strip())
        except Exception:
            return 10**9

    return sorted(pd.unique(vals), key=key)


def _order_company_size(values):
    """
    Order company size labels by their lower bound.

    Parameters
    ----------
    values : iterable
        Collection of company size labels such as '1-5', '26-100', or '1000+'.

    Returns
    -------
    list
        Sorted list of company size labels according to the starting
        numeric size of each category.

    Notes
    -----
    Labels that cannot be parsed are placed at the end of the ordering.
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
    Create a placeholder Altair chart when no data is available.

    Parameters
    ----------
    msg : str, default="No data for current filters."
        Message displayed inside the placeholder chart.

    Returns
    -------
    alt.Chart
        Altair text chart showing the supplied message.

    Notes
    -----
    This function is used to avoid rendering failures when filtered
    datasets are empty or required columns are missing.
    """
    return (
        alt.Chart(pd.DataFrame({"msg": [msg]}))
        .mark_text(size=14, color="#6B7280")
        .encode(text="msg:N")
        .properties(width="container", height=260)
    )


def as_iframe(chart: alt.Chart, height=320):
    """
    Render an Altair chart inside a Dash HTML iframe.

    Parameters
    ----------
    chart : alt.Chart
        Altair chart object to be embedded.
    height : int, default=320
        Total iframe height in pixels.

    Returns
    -------
    html.Iframe
        Dash iframe component containing the chart HTML.

    Notes
    -----
    Altair charts are converted to standalone HTML so they can be shown
    inside Dash without additional front-end integration complexity.
    """
    view_h = max(120, height - 90)
    chart = chart.properties(height=view_h, width="container")
    return html.Iframe(
        srcDoc=chart.to_html(inline=True, embed_options={"actions": False}),
        style={
            "width": "100%",
            "height": f"{height}px",
            "border": "0",
            "borderRadius": "12px",
            "backgroundColor": "#fff",
        },
    )


def filtered_df(dff, year, region, genders, age_bins, company_sizes, remote_work):
    """
    Apply dashboard filter selections to a DataFrame.

    Parameters
    ----------
    dff : pd.DataFrame
        Source DataFrame to filter.
    year : int or None
        Selected survey year.
    region : list or None
        Selected region values.
    genders : list or None
        Selected gender values.
    age_bins : list or None
        Selected age bin values.
    company_sizes : list or None
        Selected company size values.
    remote_work : list or None
        Selected remote work values.

    Returns
    -------
    pd.DataFrame
        Filtered DataFrame containing only rows that match all active
        filter criteria.

    Notes
    -----
    Empty filter inputs are ignored, so the corresponding variable does
    not restrict the dataset.
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


def wrap_chart(title, subtitle, child):
    """
    Wrap a chart component inside a styled dashboard card.

    Parameters
    ----------
    title : str
        Main chart title shown above the visualization.
    subtitle : str
        Short descriptive subtitle shown below the title.
    child : Dash component
        Chart component to display inside the card.

    Returns
    -------
    html.Div
        A styled container that includes chart title, subtitle,
        and the chart itself.

    Notes
    -----
    This helper standardizes the visual appearance of all chart panels.
    """
    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        title,
                        style={
                            "fontSize": "15px",
                            "fontWeight": "700",
                            "color": COLORS["text"],
                            "marginBottom": "2px",
                        },
                    ),
                    html.Div(
                        subtitle,
                        style={
                            "fontSize": "12px",
                            "color": COLORS["muted"],
                            "marginBottom": "10px",
                        },
                    ),
                ]
            ),
            child,
        ],
        style={
            **CARD_STYLE,
            "padding": "16px",
            "height": "100%",
        },
    )


def chart_treatment_by_group(dff: pd.DataFrame, group_by="age_bin", show_as="percent"):
    """
    Create a grouped bar chart of treatment outcomes by demographic group.

    Parameters
    ----------
    dff : pd.DataFrame
        Filtered dataset used to create the chart.
    group_by : str, default="age_bin"
        Column name used for the x-axis grouping.
    show_as : {"percent", "count"}, default="percent"
        Determines whether the y-axis shows treatment rate (%) or the
        number of respondents with treatment = 'Yes'.

    Returns
    -------
    alt.Chart
        Altair grouped bar chart.

    Notes
    -----
    - Bars are grouped by the selected category and split by gender.
    - Treatment rate is computed as the share of 'Yes' responses within
      each group.
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
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=alt.X(f"{g}:N", sort=order, title=g.replace("_", " ").title()),
            xOffset=alt.XOffset("gender:N"),
            y=alt.Y(y_field, title=y_title),
            color=alt.Color("gender:N", title="Gender"),
            tooltip=tooltip,
        )
        .properties(title="Treatment by group")
        .configure_title(fontSize=14, anchor="start", color=COLORS["text"])
        .configure_axis(
            labelFontSize=11,
            titleFontSize=12,
            labelColor=COLORS["text"],
            titleColor=COLORS["text"],
        )
        .configure_view(strokeOpacity=0)
    )
    return chart


def chart_interfere_heatmap(dff: pd.DataFrame, metric="count"):
    """
    Create a bar chart of work interference among respondents who sought treatment.

    Parameters
    ----------
    dff : pd.DataFrame
        Filtered dataset used to create the chart.
    metric : {"count", "percent"}, default="count"
        Metric shown on the y-axis. Use 'count' for raw counts or
        'percent' for percentage share within treatment = 'Yes' respondents.

    Returns
    -------
    alt.Chart
        Altair bar chart of work interference distribution.

    Notes
    -----
    Only respondents with treatment = 'Yes' are included in this chart.
    """
    if dff is None or len(dff) == 0:
        return _no_data_chart("No data for Chart 2 (Work interference).")

    if "work_interfere" not in dff.columns or "treatment" not in dff.columns:
        return _no_data_chart("Missing required columns for Chart 2.")

    tmp = dff.copy()
    tmp["work_interfere"] = _ensure_str_series(tmp["work_interfere"])
    tmp["treatment"] = _ensure_str_series(tmp["treatment"])

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
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3, color=COLORS["chart_blue"])
        .encode(
            x=alt.X("work_interfere:N", sort=x_order, title="Work interference"),
            y=alt.Y(y_field, title=y_title),
            tooltip=tooltip,
        )
        .properties(title="Work interference")
        .configure_title(fontSize=14, anchor="start", color=COLORS["text"])
        .configure_axis(
            labelFontSize=11,
            titleFontSize=12,
            labelColor=COLORS["text"],
            titleColor=COLORS["text"],
        )
        .configure_view(strokeOpacity=0)
    )
    return chart


def chart_support_yes_only(dff: pd.DataFrame, factor="benefits", bar_color="#4C78A8"):
    """
    Create a bar chart of workplace support categories among treated respondents.

    Parameters
    ----------
    dff : pd.DataFrame
        Filtered dataset used to create the chart.
    factor : str, default="benefits"
        Workplace support variable to visualize, such as 'benefits'
        or 'seek_help'.
    bar_color : str, default="#4C78A8"
        Fill color used for the bars.

    Returns
    -------
    alt.Chart
        Altair bar chart showing the percentage distribution of the
        selected factor among respondents with treatment = 'Yes'.

    Notes
    -----
    This chart is useful for comparing support availability or help-seeking
    climate among respondents who already reported treatment.
    """
    if dff is None or len(dff) == 0:
        return _no_data_chart(f"No data for Chart ({factor}).")

    if factor not in dff.columns or "treatment" not in dff.columns:
        return _no_data_chart(f"Missing required columns for factor: {factor}")

    tmp = dff.copy()
    tmp[factor] = _ensure_str_series(tmp[factor])
    tmp["treatment"] = _ensure_str_series(tmp["treatment"])

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
        .mark_bar(color=bar_color, cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=alt.X(f"{factor}:N", sort=x_order, title=nice_title),
            y=alt.Y("pct:Q", title="Percent of treatment = Yes respondents"),
            tooltip=[
                alt.Tooltip(f"{factor}:N", title=nice_title),
                alt.Tooltip("pct:Q", title="Percent", format=".1f"),
                alt.Tooltip("count:Q", title="Count"),
            ],
        )
        .properties(title=f"{nice_title} Support")
        .configure_title(fontSize=14, anchor="start", color=COLORS["text"])
        .configure_axis(
            labelFontSize=11,
            titleFontSize=12,
            labelColor=COLORS["text"],
            titleColor=COLORS["text"],
        )
        .configure_view(strokeOpacity=0)
    )
    return chart


def kpi_cards(dff: pd.DataFrame):
    """
    Generate KPI summary cards from the filtered dataset.

    Parameters
    ----------
    dff : pd.DataFrame
        Filtered dataset used to compute summary indicators.

    Returns
    -------
    dbc.Row
        Bootstrap row containing four KPI cards:
        sample size, treatment rate, benefits available, and family history.

    Notes
    -----
    Percentage KPIs are calculated as the share of 'Yes' responses in the
    corresponding column.
    """
    n = len(dff)

    def pct(col, val="Yes"):
        """
        Compute the percentage of rows matching a target value.

        Parameters
        ----------
        col : str
            Column name to evaluate.
        val : str, default="Yes"
            Target value used for the percentage calculation.

        Returns
        -------
        float or None
            Percentage of rows equal to the target value, or None if the
            dataset is empty or the column does not exist.
        """
        if n == 0:
            return None
        if col not in dff.columns:
            return None
        return (dff[col].astype(str).eq(val).mean()) * 100

    def fmt(x):
        """
        Format KPI percentages for display.

        Parameters
        ----------
        x : float or None
            Numeric percentage value.

        Returns
        -------
        str
            Formatted percentage string with one decimal place, or 'N/A'
            if the value is missing.
        """
        return "N/A" if x is None else f"{x:.1f}%"

    def one_kpi(title, value, accent="#2F6BFF"):
        """
        Build a single styled KPI card.

        Parameters
        ----------
        title : str
            KPI label shown at the top of the card.
        value : str
            Main KPI value shown prominently in the card.
        accent : str, default="#2F6BFF"
            Accent color used for the underline decoration.

        Returns
        -------
        dbc.Card
            Styled Bootstrap card representing one KPI.
        """
        return dbc.Card(
            dbc.CardBody(
                [
                    html.Div(
                        title,
                        style={
                            "fontSize": "13px",
                            "color": COLORS["muted"],
                            "fontWeight": "600",
                            "marginBottom": "8px",
                        },
                    ),
                    html.Div(
                        value,
                        style={
                            "fontSize": "32px",
                            "fontWeight": "700",
                            "color": COLORS["text"],
                            "lineHeight": "1.1",
                        },
                    ),
                    html.Div(
                        style={
                            "width": "42px",
                            "height": "4px",
                            "backgroundColor": accent,
                            "borderRadius": "999px",
                            "marginTop": "12px",
                        },
                    ),
                ]
            ),
            style={
                **CARD_STYLE,
                "padding": "4px",
                "height": "100%",
            },
        )

    return dbc.Row(
        [
            dbc.Col(one_kpi("Sample Size", f"{n}", accent=COLORS["primary"]), md=3),
            dbc.Col(one_kpi("Treatment Rate", fmt(pct("treatment")), accent=COLORS["chart_blue"]), md=3),
            dbc.Col(one_kpi("Benefits Available", fmt(pct("benefits")), accent=COLORS["success"]), md=3),
            dbc.Col(one_kpi("Family History", fmt(pct("family_history")), accent=COLORS["warning"]), md=3),
        ],
        className="g-3",
    )


app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title="Workplace Mental Health Dashboard",
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
            html.Div("Filters", style=SECTION_TITLE_STYLE),

            html.Label("Year", style=LABEL_STYLE),
            dcc.Dropdown(
                years,
                years[0] if years else None,
                id="f-year",
                clearable=False,
                placeholder="Select year",
            ),

            html.Div(style={"height": "16px"}),

            html.Label("Region", style=LABEL_STYLE),
            dcc.Dropdown(
                regions,
                ["North America"] if "North America" in regions else regions[:1],
                id="f-region",
                multi=True,
                placeholder="Select region",
            ),

            html.Hr(style={"margin": "22px 0", "borderColor": COLORS["border"]}),

            html.Label("Gender", style=LABEL_STYLE),
            dcc.Dropdown(
                genders,
                genders,
                id="f-gender",
                multi=True,
                placeholder="Select gender",
            ),

            html.Div(style={"height": "16px"}),

            html.Label("Age bin", style=LABEL_STYLE),
            dcc.Dropdown(
                age_bins,
                age_bins,
                id="f-agebin",
                multi=True,
                placeholder="Select age group",
            ),

            html.Div(style={"height": "16px"}),

            html.Label("Company size", style=LABEL_STYLE),
            dcc.Dropdown(
                company_sizes,
                id="f-company",
                multi=True,
                placeholder="Select company size",
            ),

            html.Div(style={"height": "16px"}),

            html.Label("Remote work", style=LABEL_STYLE),
            dcc.Dropdown(
                remote_vals,
                id="f-remote",
                multi=True,
                placeholder="Select remote work status",
            ),
        ],
        style={"padding": "22px"},
    ),
    style={
        **CARD_STYLE,
        "height": "100%",
    },
)

legend = dbc.Card(
    dbc.CardBody(
        [
            html.Div("Legend & Notes", style=SECTION_TITLE_STYLE),
            html.P(
                "All charts update dynamically based on the filters selected on the left.",
                style={"color": COLORS["muted"], "fontSize": "14px", "marginBottom": "16px"},
            ),

            html.Hr(style={"borderColor": COLORS["border"]}),

            html.Div(
                "Definitions",
                style={
                    "fontSize": "14px",
                    "fontWeight": "700",
                    "color": COLORS["text"],
                    "marginBottom": "8px",
                },
            ),
            html.Ul(
                [
                    html.Li("treatment: whether the respondent has sought treatment for mental health."),
                    html.Li("work_interfere: how often mental health interferes with work."),
                    html.Li("benefits / care_options / wellness_program / seek_help / anonymity: workplace support indicators."),
                ],
                style={"paddingLeft": "18px", "color": COLORS["text"], "fontSize": "14px"},
            ),

            html.Hr(style={"borderColor": COLORS["border"]}),

            html.Div(
                "Encodings",
                style={
                    "fontSize": "14px",
                    "fontWeight": "700",
                    "color": COLORS["text"],
                    "marginBottom": "8px",
                },
            ),
            html.Ul(
                [
                    html.Li("Chart 1: grouped bars show treatment rate (%) by age group, colored by gender."),
                    html.Li("Chart 2: bars show work interference among respondents who sought treatment."),
                    html.Li("Chart 3 & 4: bars show workplace support distributions among respondents who sought treatment."),
                ],
                style={"paddingLeft": "18px", "color": COLORS["text"], "fontSize": "14px"},
            ),

            dbc.Alert(
                "Data includes 'Don't know / Unknown / <missing>' categories for transparency.",
                color="light",
                style={
                    "marginTop": "16px",
                    "borderRadius": "12px",
                    "fontSize": "13px",
                    "border": f"1px solid {COLORS['border']}",
                    "color": COLORS["muted"],
                    "backgroundColor": "#FAFBFD",
                },
            ),
        ],
        style={"padding": "22px"},
    ),
    style={
        **CARD_STYLE,
        "height": "100%",
    },
)

app.layout = dbc.Container(
    fluid=True,
    style={
        "height": "100vh",
        "overflow": "hidden",
        "backgroundColor": COLORS["bg"],
        "padding": "18px 18px 16px 18px",
    },
    children=[
        html.Div(
            [
                html.Div(
                    [
                        html.H2("Workplace Mental Health Dashboard", style=PAGE_TITLE_STYLE),
                        html.P(
                            "Explore treatment rates and workplace factors across groups.",
                            style=PAGE_SUBTITLE_STYLE,
                        ),
                    ],
                    style={"flex": "1"},
                ),
            ],
            style={
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "space-between",
                "marginBottom": "14px",
            },
        ),

        dbc.Row(
            className="g-3",
            style={"height": "calc(100vh - 100px)"},
            children=[
                dbc.Col(
                    html.Div(filters, style={"height": "100%", "overflowY": "auto"}),
                    width=3,
                    style={"height": "100%"},
                ),

                dbc.Col(
                    html.Div(
                        [
                            html.Div(id="kpi-area", style={"flex": "0 0 auto", "marginBottom": "14px"}),
                            html.Div(
                                [
                                    html.Div(id="chart-1"),
                                    html.Div(id="chart-2"),
                                    html.Div(id="chart-3"),
                                    html.Div(id="chart-4"),
                                ],
                                style={
                                    "flex": "1 1 auto",
                                    "minHeight": "0",
                                    "overflowY": "auto",
                                    "display": "grid",
                                    "gridTemplateColumns": "1fr 1fr",
                                    "gap": "14px",
                                    "paddingRight": "2px",
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
    Update KPI cards and all charts when filter selections change.

    Parameters
    ----------
    year : int or None
        Selected survey year.
    region : list or None
        Selected region values.
    gender : list or None
        Selected gender values.
    agebin : list or None
        Selected age bin values.
    company : list or None
        Selected company size values.
    remote : list or None
        Selected remote work values.

    Returns
    -------
    tuple
        A five-element tuple containing:
        - KPI card row
        - Chart 1 component
        - Chart 2 component
        - Chart 3 component
        - Chart 4 component

    Notes
    -----
    This is the main reactive function of the dashboard. It filters the
    dataset based on current inputs, rebuilds summary KPIs, and regenerates
    all chart panels.
    """
    try:
        dff = filtered_df(df, year, region, gender, agebin, company, remote)
        h = 320

        c1 = wrap_chart(
            "Treatment by group",
            "Treatment rate across age groups and gender",
            as_iframe(chart_treatment_by_group(dff, "age_bin", "percent"), height=h),
        )

        c2 = wrap_chart(
            "Work interference",
            "Distribution among respondents who sought treatment",
            as_iframe(chart_interfere_heatmap(dff, "percent"), height=h),
        )

        c3 = wrap_chart(
            "Benefits support",
            "Benefits availability among respondents who sought treatment",
            as_iframe(chart_support_yes_only(dff, "benefits", COLORS["success"]), height=h),
        )

        c4 = wrap_chart(
            "Seek help support",
            "Help-seeking support among respondents who sought treatment",
            as_iframe(chart_support_yes_only(dff, "seek_help", COLORS["warning"]), height=h),
        )

        return kpi_cards(dff), c1, c2, c3, c4

    except Exception as e:
        print("CALLBACK ERROR:", repr(e))
        traceback.print_exc()
        return html.Div(f"Callback error: {e}"), None, None, None, None


if __name__ == "__main__":
    """
    Run the Dash development server locally.

    Notes
    -----
    Set debug=True for development. For deployment, this file should expose
    the `server` object to the hosting platform.
    """
    app.run(debug=True)