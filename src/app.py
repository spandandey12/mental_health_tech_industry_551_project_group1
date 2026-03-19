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
- Show linked Altair charts embedded in Dash via an iframe.
- Support inter-plot interaction: selecting an age group in the first
  chart filters the remaining charts.
- Use a professional dashboard layout with cards, spacing, and
  consistent visual styling.
"""

from pathlib import Path
import pandas as pd
import traceback
import altair as alt
from dash import Dash, html, dcc, Input, Output
import dash_bootstrap_components as dbc

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
    "chart_teal": "#72B7B2",
    "chart_purple": "#9C89B8",
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
            return int(str(v).split("-")[0].replace("+", "").strip())
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
        .mark_text(size=14, color="#6B7280")
        .encode(text="msg:N")
        .properties(width=300, height=260)
    )


def as_iframe(chart, height=700):
    return html.Iframe(
        srcDoc=chart.to_html(
            inline=True,
            embed_options={
                "actions": False,
                "renderer": "svg",
            },
        ),
        style={
            "width": "100%",
            "height": f"{height}px",
            "border": "0",
            "borderRadius": "12px",
            "backgroundColor": "#FFFFFF",
            "display": "block",
        },
    )


def filtered_df(dff, year, region, genders, age_bins, company_sizes, remote_work):
    out = dff.copy()

    if year:
        out = out[out["year"] == int(year)]
    if region:
        out = out[out["region"].isin(region)]
    if genders:
        out = out[out["gender"].isin(genders)]
    if age_bins:
        out = out[out["age_bin"].isin(age_bins)]
    if company_sizes:
        out = out[out["company_size"].isin(company_sizes)]
    if remote_work:
        out = out[out["remote_work"].isin(remote_work)]

    return out


def wrap_chart(title, subtitle, child):
    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        title,
                        style={
                            "fontSize": "22px",
                            "fontWeight": "700",
                            "color": COLORS["text"],
                            "lineHeight": "1.2",
                            "marginBottom": "6px",
                        },
                    ),
                    html.Div(
                        subtitle,
                        style={
                            "fontSize": "14px",
                            "color": COLORS["muted"],
                            "lineHeight": "1.5",
                            "marginBottom": "14px",
                        },
                    ),
                ],
                style={"padding": "2px 2px 0 2px"},
            ),
            child,
        ],
        style={
            **CARD_STYLE,
            "padding": "18px 18px 14px 18px",
            "height": "100%",
        },
    )


# -----------------------------
# KPI cards
# -----------------------------
def kpi_cards(dff: pd.DataFrame):
    n = len(dff)

    def pct(col, val="Yes"):
        if n == 0 or col not in dff.columns:
            return None
        return (dff[col].astype(str).eq(val).mean()) * 100

    def fmt(x):
        return "N/A" if x is None else f"{x:.1f}%"

    def one_kpi(title, value, accent="#2F6BFF"):
        return dbc.Card(
            dbc.CardBody(
                [
                    html.Div(
                        title,
                        style={
                            "fontSize": "12px",
                            "color": COLORS["muted"],
                            "fontWeight": "600",
                            "marginBottom": "8px",
                        },
                    ),
                    html.Div(
                        value,
                        style={
                            "fontSize": "30px",
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


# -----------------------------
# Linked Altair dashboard
# -----------------------------
def linked_dashboard_chart(dff: pd.DataFrame, metric_mode="percent"):
    if dff is None or len(dff) == 0:
        return _no_data_chart("No data for current filters.")

    required_cols = [
        "age_bin",
        "gender",
        "treatment",
        "work_interfere",
        "benefits",
        "seek_help",
    ]
    missing = [c for c in required_cols if c not in dff.columns]
    if missing:
        return _no_data_chart(f"Missing required columns: {', '.join(missing)}")

    tmp = dff.copy()

    for col in required_cols:
        tmp[col] = _ensure_str_series(tmp[col])

    age_order = _order_age_bin(tmp["age_bin"].unique())
    interfere_order = _order_work_interfere(tmp["work_interfere"].unique())
    yn_order = _order_yes_no_unknown(
        pd.concat([tmp["benefits"], tmp["seek_help"]], axis=0).unique()
    )

    age_select = alt.selection_point(
        fields=["age_bin"],
        empty=True,
        on="click",
        clear="dblclick",
        name="SelectAgeGroup",
    )

    agg1 = (
        tmp.groupby(["age_bin", "gender"], dropna=False)
        .agg(
            n=("treatment", "size"),
            treat_yes=("treatment", lambda x: (x == "Yes").sum()),
        )
        .reset_index()
    )
    agg1["rate"] = (agg1["treat_yes"] / agg1["n"]) * 100

    if metric_mode == "count":
        y_field_1 = "treat_yes:Q"
        y_title_1 = "Treatment (Yes) count"
        tooltip_1 = [
            alt.Tooltip("age_bin:N", title="Age group"),
            alt.Tooltip("gender:N", title="Gender"),
            alt.Tooltip("treat_yes:Q", title="Treatment count"),
            alt.Tooltip("n:Q", title="Respondents"),
        ]
    else:
        y_field_1 = "rate:Q"
        y_title_1 = "Treatment rate (%)"
        tooltip_1 = [
            alt.Tooltip("age_bin:N", title="Age group"),
            alt.Tooltip("gender:N", title="Gender"),
            alt.Tooltip("rate:Q", title="Treatment rate", format=".1f"),
            alt.Tooltip("n:Q", title="Respondents"),
        ]

    c1 = (
        alt.Chart(agg1)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X(
                "age_bin:N",
                sort=age_order,
                title="Age group",
                axis=alt.Axis(labelAngle=0, labelPadding=8),
            ),
            xOffset=alt.XOffset("gender:N"),
            y=alt.Y(y_field_1, title=y_title_1),
            color=alt.Color(
                "gender:N",
                title="Gender",
                scale=alt.Scale(
                    range=["#4C78A8", "#F58518", "#E45756", "#72B7B2", "#54A24B"]
                ),
            ),
            opacity=alt.condition(age_select, alt.value(1.0), alt.value(0.35)),
            tooltip=tooltip_1,
        )
        .add_params(age_select)
        .properties(
            title="Treatment by age group",
            width=320,
            height=240,
        )
    )

    filtered_base = alt.Chart(tmp).transform_filter(age_select)
    treated_filtered = filtered_base.transform_filter(alt.datum.treatment == "Yes")

    c2 = (
        treated_filtered
        .transform_aggregate(
            count="count()",
            groupby=["work_interfere"],
        )
        .transform_joinaggregate(total="sum(count)")
        .transform_calculate(
            pct="datum.total > 0 ? datum.count / datum.total * 100 : 0"
        )
        .mark_bar(
            color="#4C78A8",
            cornerRadiusTopLeft=4,
            cornerRadiusTopRight=4,
        )
        .encode(
            x=alt.X(
                "work_interfere:N",
                sort=interfere_order,
                title="Work interference",
                axis=alt.Axis(labelAngle=0, labelPadding=8),
            ),
            y=alt.Y(
                "pct:Q" if metric_mode == "percent" else "count:Q",
                title=("Percent" if metric_mode == "percent" else "Count"),
            ),
            tooltip=[
                alt.Tooltip("work_interfere:N", title="Work interference"),
                alt.Tooltip("count:Q", title="Count"),
                alt.Tooltip("pct:Q", title="Percent", format=".1f"),
            ],
        )
        .properties(
            title="Work interference among treated respondents",
            width=320,
            height=240,
        )
    )

    c3 = (
        treated_filtered
        .transform_aggregate(
            count="count()",
            groupby=["benefits"],
        )
        .transform_joinaggregate(total="sum(count)")
        .transform_calculate(
            pct="datum.total > 0 ? datum.count / datum.total * 100 : 0"
        )
        .mark_bar(
            color="#54A24B",
            cornerRadiusTopLeft=4,
            cornerRadiusTopRight=4,
        )
        .encode(
            x=alt.X(
                "benefits:N",
                sort=yn_order,
                title="Benefits available",
                axis=alt.Axis(labelAngle=0, labelPadding=8),
            ),
            y=alt.Y(
                "pct:Q" if metric_mode == "percent" else "count:Q",
                title=("Percent" if metric_mode == "percent" else "Count"),
            ),
            tooltip=[
                alt.Tooltip("benefits:N", title="Benefits"),
                alt.Tooltip("count:Q", title="Count"),
                alt.Tooltip("pct:Q", title="Percent", format=".1f"),
            ],
        )
        .properties(
            title="Benefits support among treated respondents",
            width=320,
            height=240,
        )
    )

    c4 = (
        treated_filtered
        .transform_aggregate(
            count="count()",
            groupby=["seek_help"],
        )
        .transform_joinaggregate(total="sum(count)")
        .transform_calculate(
            pct="datum.total > 0 ? datum.count / datum.total * 100 : 0"
        )
        .mark_bar(
            color="#F4A261",
            cornerRadiusTopLeft=4,
            cornerRadiusTopRight=4,
        )
        .encode(
            x=alt.X(
                "seek_help:N",
                sort=yn_order,
                title="Seek-help climate",
                axis=alt.Axis(labelAngle=0, labelPadding=8),
            ),
            y=alt.Y(
                "pct:Q" if metric_mode == "percent" else "count:Q",
                title=("Percent" if metric_mode == "percent" else "Count"),
            ),
            tooltip=[
                alt.Tooltip("seek_help:N", title="Seek help"),
                alt.Tooltip("count:Q", title="Count"),
                alt.Tooltip("pct:Q", title="Percent", format=".1f"),
            ],
        )
        .properties(
            title="Help-seeking climate among treated respondents",
            width=320,
            height=240,
        )
    )

    dashboard = (
        alt.vconcat(
            (c1 | c2),
            (c3 | c4),
            spacing=26,
        )
        .configure_title(
            fontSize=15,
            anchor="start",
            color=COLORS["text"],
            fontWeight="bold",
            offset=8,
        )
        .configure_axis(
            labelFontSize=11,
            titleFontSize=12,
            labelColor=COLORS["text"],
            titleColor=COLORS["text"],
            gridColor="#E9EEF5",
            domainColor="#C9D4E5",
            tickColor="#C9D4E5",
        )
        .configure_legend(
            labelFontSize=11,
            titleFontSize=12,
            labelColor=COLORS["text"],
            titleColor=COLORS["text"],
            orient="top",
            symbolType="square",
        )
        .configure_view(stroke=None)
        .properties(
            title=alt.TitleParams(
                text="Linked views for workplace mental health exploration",
                subtitle=[
                    "Click an age group in the first chart to update the remaining panels. Double-click to clear the selection."
                ],
                anchor="start",
                fontSize=17,
                subtitleFontSize=12,
                color=COLORS["text"],
                subtitleColor=COLORS["muted"],
                offset=12,
            )
        )
    )

    return dashboard


# -----------------------------
# App init
# -----------------------------
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title="Workplace Mental Health Dashboard",
)
server = app.server

# -----------------------------
# Precompute dropdown values
# -----------------------------
years = sorted(df["year"].dropna().unique()) if "year" in df.columns else []
regions = sorted(df["region"].dropna().unique()) if "region" in df.columns else []
genders = sorted(df["gender"].dropna().unique()) if "gender" in df.columns else []
age_bins = _order_age_bin(df["age_bin"].dropna().unique()) if "age_bin" in df.columns else []
company_sizes = (
    _order_company_size(df["company_size"].dropna().unique())
    if "company_size" in df.columns
    else []
)
remote_vals = (
    sorted(df["remote_work"].dropna().unique()) if "remote_work" in df.columns else []
)

# -----------------------------
# Sidebar
# -----------------------------
filters = dbc.Card(
    dbc.CardBody(
        [
            html.Div("Filters", style=SECTION_TITLE_STYLE),

            html.Label("Year", style=LABEL_STYLE),
            dcc.Dropdown(
                options=[{"label": str(y), "value": y} for y in years],
                value=years[0] if years else None,
                id="f-year",
                clearable=False,
                placeholder="Select year",
            ),

            html.Div(style={"height": "16px"}),

            html.Label("Region", style=LABEL_STYLE),
            dcc.Dropdown(
                options=[{"label": r, "value": r} for r in regions],
                value=["North America"] if "North America" in regions else (regions[:1] if regions else []),
                id="f-region",
                multi=True,
                placeholder="Select region",
            ),

            html.Hr(style={"margin": "22px 0", "borderColor": COLORS["border"]}),

            html.Label("Gender", style=LABEL_STYLE),
            dcc.Dropdown(
                options=[{"label": g, "value": g} for g in genders],
                value=genders,
                id="f-gender",
                multi=True,
                placeholder="Select gender",
            ),

            html.Div(style={"height": "16px"}),

            html.Label("Age bin", style=LABEL_STYLE),
            dcc.Dropdown(
                options=[{"label": a, "value": a} for a in age_bins],
                value=age_bins,
                id="f-agebin",
                multi=True,
                placeholder="Select age group",
            ),

            html.Div(style={"height": "16px"}),

            html.Label("Company size", style=LABEL_STYLE),
            dcc.Dropdown(
                options=[{"label": c, "value": c} for c in company_sizes],
                value=company_sizes,
                id="f-company",
                multi=True,
                placeholder="Select company size",
            ),

            html.Div(style={"height": "16px"}),

            html.Label("Remote work", style=LABEL_STYLE),
            dcc.Dropdown(
                options=[{"label": r, "value": r} for r in remote_vals],
                value=remote_vals,
                id="f-remote",
                multi=True,
                placeholder="Select remote work status",
            ),

            html.Div(style={"height": "16px"}),

            html.Label("Chart metric", style=LABEL_STYLE),
            dcc.RadioItems(
                id="f-metric",
                options=[
                    {"label": " Percent", "value": "percent"},
                    {"label": " Count", "value": "count"},
                ],
                value="percent",
                inline=True,
                labelStyle={
                    "marginRight": "16px",
                    "fontSize": "13px",
                    "color": COLORS["text"],
                },
                inputStyle={"marginRight": "6px"},
            ),
        ],
        style={"padding": "22px"},
    ),
    style={
        **CARD_STYLE,
        "height": "100%",
    },
)

# -----------------------------
# Notes / Legend
# -----------------------------
legend = dbc.Card(
    dbc.CardBody(
        [
            html.Div("Legend & Notes", style=SECTION_TITLE_STYLE),

            html.P(
                "All charts update dynamically based on the filters selected on the left.",
                style={
                    "color": COLORS["muted"],
                    "fontSize": "14px",
                    "marginBottom": "16px",
                },
            ),

            dbc.Alert(
                "Linked interaction: click an age group in the first chart to filter the remaining views. Double-click to reset.",
                color="light",
                style={
                    "marginBottom": "14px",
                    "borderRadius": "12px",
                    "fontSize": "13px",
                    "border": f"1px solid {COLORS['border']}",
                    "color": COLORS["muted"],
                    "backgroundColor": "#FAFBFD",
                },
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
                    html.Li("benefits: whether the employer provides mental health benefits."),
                    html.Li("seek_help: whether the workplace encourages help-seeking."),
                ],
                style={
                    "paddingLeft": "18px",
                    "color": COLORS["text"],
                    "fontSize": "14px",
                },
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
                    html.Li("Top-left: grouped bars compare treatment outcomes by age group and gender."),
                    html.Li("Top-right: bars summarize work interference among treated respondents."),
                    html.Li("Bottom-left: bars summarize benefits support among treated respondents."),
                    html.Li("Bottom-right: bars summarize help-seeking support among treated respondents."),
                ],
                style={
                    "paddingLeft": "18px",
                    "color": COLORS["text"],
                    "fontSize": "14px",
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

# -----------------------------
# Layout
# -----------------------------
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
                            "Explore treatment rates and workplace support factors across demographic and organizational groups.",
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
                                id="linked-chart-area",
                                style={
                                    "flex": "1 1 auto",
                                    "minHeight": "0",
                                    "overflowY": "auto",
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

# -----------------------------
# Callback
# -----------------------------
@app.callback(
    Output("kpi-area", "children"),
    Output("linked-chart-area", "children"),
    Input("f-year", "value"),
    Input("f-region", "value"),
    Input("f-gender", "value"),
    Input("f-agebin", "value"),
    Input("f-company", "value"),
    Input("f-remote", "value"),
    Input("f-metric", "value"),
)
def update(year, region, gender, agebin, company, remote, metric_mode):
    try:
        dff = filtered_df(df, year, region, gender, agebin, company, remote)

        linked = wrap_chart(
            "Interactive dashboard",
            "Filter the data using the controls on the left. Then select an age group in the first chart to update the other panels.",
            as_iframe(linked_dashboard_chart(dff, metric_mode=metric_mode), height=700),
        )

        return kpi_cards(dff), linked

    except Exception as e:
        print("CALLBACK ERROR:", repr(e))
        traceback.print_exc()
        return html.Div(f"Callback error: {e}"), None


if __name__ == "__main__":
    app.run(debug=True)