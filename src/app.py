
from pathlib import Path
import pandas as pd
import numpy as np

from dash import Dash, html, dcc, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go

# -----------------------------
# Paths / data
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "cleaned.csv"

if not DATA_PATH.exists():
    raise FileNotFoundError(f"Missing data file: {DATA_PATH}")

df = pd.read_csv(DATA_PATH)

# -----------------------------
# Theme
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
    "blue": "#636EFA",
    "red": "#EF553B",
    "green": "#00CC96",
    "purple": "#AB63FA",
    "teal": "#19D3F3",
}

GENDER_COLORS = {
    "Female": COLORS["blue"],
    "Male": COLORS["red"],
    "Non-binary / Other": COLORS["green"],
}

CARD_STYLE = {
    "backgroundColor": COLORS["panel"],
    "border": f"1px solid {COLORS['border']}",
    "borderRadius": "18px",
    "boxShadow": COLORS["shadow"],
    "height": "100%",
}

GRAPH_CONFIG = {"displayModeBar": False, "responsive": True}

# -----------------------------
# Helpers
# -----------------------------
def stable_unique(values):
    return list(pd.Series(list(values)).dropna().astype(str).drop_duplicates())

def ensure_str(s):
    return s.astype("string").fillna("<missing>")

def order_yes_no_unknown(values):
    priority = ["Yes", "No", "Don't know", "Not sure", "<missing>"]
    vals = stable_unique(values)
    ordered = [v for v in priority if v in vals]
    tail = sorted([v for v in vals if v not in ordered])
    return ordered + tail

def order_work_interfere(values):
    priority = ["Never", "Rarely", "Sometimes", "Often", "Don't know", "<missing>"]
    vals = stable_unique(values)
    ordered = [v for v in priority if v in vals]
    tail = sorted([v for v in vals if v not in ordered])
    return ordered + tail

def order_age_bin(values):
    vals = stable_unique(values)

    def key(v):
        s = str(v).strip()
        try:
            if "+" in s:
                return int(s.replace("+", ""))
            return int(s.split("-")[0])
        except Exception:
            return 10**9

    return sorted(vals, key=key)

def order_company_size(values):
    vals = stable_unique(values)

    def key(v):
        s = str(v).strip()
        try:
            if "+" in s:
                return int(s.replace("+", ""))
            return int(s.split("-")[0])
        except Exception:
            return 10**9

    return sorted(vals, key=key)

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

def apply_linked_filters(dff, selected_age, selected_country, selected_region):
    out = dff.copy()

    if selected_age:
        out = out[out["age_bin"].astype(str) == str(selected_age)]
    if selected_country and "country" in out.columns:
        out = out[out["country"].astype(str) == str(selected_country)]
    if selected_region and "region" in out.columns:
        out = out[out["region"].astype(str) == str(selected_region)]

    return out

def make_empty_figure(msg="No data for current filters."):
    fig = go.Figure()
    fig.add_annotation(
        text=msg,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font=dict(size=15, color=COLORS["muted"]),
    )
    fig.update_layout(
        template="plotly_white",
        margin=dict(l=20, r=20, t=40, b=30),
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig

def beautify_fig(fig, height=340, legend=True):
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=20, r=20, t=48, b=30),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color=COLORS["text"]),
    )
    if legend:
        fig.update_layout(
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.03,
                xanchor="left",
                x=0,
                title=None,
            )
        )
    return fig

def wrap_chart(title, subtitle, graph_id):
    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(
                    title,
                    style={
                        "fontSize": "18px",
                        "fontWeight": "700",
                        "color": COLORS["text"],
                        "marginBottom": "8px",
                    },
                ),
                html.Div(
                    subtitle,
                    style={
                        "fontSize": "13px",
                        "color": COLORS["muted"],
                        "marginBottom": "18px",
                        "lineHeight": "1.5",
                    },
                ),
                html.Div(
                    dcc.Graph(id=graph_id, config=GRAPH_CONFIG),
                    style={"marginTop": "6px"},
                ),
            ]
        ),
        style=CARD_STYLE,
    )

def kpi_card(title, value, accent):
    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(
                    title,
                    style={
                        "fontSize": "12px",
                        "fontWeight": "600",
                        "color": COLORS["muted"],
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
                        "width": "44px",
                        "height": "4px",
                        "backgroundColor": accent,
                        "borderRadius": "999px",
                        "marginTop": "12px",
                    }
                ),
            ]
        ),
        style=CARD_STYLE,
    )

def build_kpis(dff):
    n = len(dff)

    def pct(col, val="Yes"):
        if n == 0 or col not in dff.columns:
            return None
        return dff[col].astype(str).eq(val).mean() * 100

    def fmt_pct(x):
        return "N/A" if x is None else f"{x:.1f}%"

    return dbc.Row(
        [
            dbc.Col(kpi_card("Sample Size", f"{n}", COLORS["primary"]), md=3),
            dbc.Col(kpi_card("Treatment Rate", fmt_pct(pct("treatment")), COLORS["blue"]), md=3),
            dbc.Col(kpi_card("Benefits Available", fmt_pct(pct("benefits")), COLORS["success"]), md=3),
            dbc.Col(kpi_card("Family History", fmt_pct(pct("family_history")), COLORS["warning"]), md=3),
        ],
        className="g-3",
    )

# -----------------------------
# Figure builders
# -----------------------------
def fig_treatment_by_age(dff):
    needed = {"age_bin", "gender", "treatment"}
    if len(dff) == 0:
        return make_empty_figure()
    if not needed.issubset(dff.columns):
        return make_empty_figure("Missing columns for age-linked chart.")

    tmp = dff.copy()
    tmp["age_bin"] = ensure_str(tmp["age_bin"])
    tmp["gender"] = ensure_str(tmp["gender"])
    tmp["treatment"] = ensure_str(tmp["treatment"])

    agg = (
        tmp.groupby(["age_bin", "gender"], dropna=False)
        .agg(n=("treatment", "size"),
             treat_yes=("treatment", lambda x: (x == "Yes").sum()))
        .reset_index()
    )
    agg["rate"] = agg["treat_yes"] / agg["n"] * 100

    fig = px.bar(
        agg,
        x="age_bin",
        y="rate",
        color="gender",
        barmode="group",
        category_orders={"age_bin": order_age_bin(agg["age_bin"].tolist())},
        color_discrete_map=GENDER_COLORS,
        custom_data=["age_bin"],
        labels={"age_bin": "Age group", "rate": "Treatment rate (%)"},
    )
    fig.update_traces(
        hovertemplate="Age group=%{x}<br>Gender=%{legendgroup}<br>Rate=%{y:.1f}%<extra></extra>"
    )
    return beautify_fig(fig)

def fig_support_donut(dff):
    if len(dff) == 0 or "benefits" not in dff.columns:
        return make_empty_figure()

    tmp = dff.copy()
    tmp["benefits"] = ensure_str(tmp["benefits"])
    agg = tmp["benefits"].value_counts(dropna=False).reset_index()
    agg.columns = ["benefits", "count"]

    fig = px.pie(
        agg,
        names="benefits",
        values="count",
        hole=0.58,
        color="benefits",
        category_orders={"benefits": order_yes_no_unknown(agg["benefits"].tolist())},
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    return beautify_fig(fig)

def fig_interference_bar(dff):
    needed = {"work_interfere", "treatment"}
    if len(dff) == 0 or not needed.issubset(dff.columns):
        return make_empty_figure()

    tmp = dff.copy()
    tmp["work_interfere"] = ensure_str(tmp["work_interfere"])
    tmp["treatment"] = ensure_str(tmp["treatment"])
    tmp = tmp[tmp["treatment"] == "Yes"]

    if len(tmp) == 0:
        return make_empty_figure("No treated respondents for current linked filters.")

    agg = tmp["work_interfere"].value_counts(dropna=False).reset_index()
    agg.columns = ["work_interfere", "count"]
    agg["pct"] = agg["count"] / agg["count"].sum() * 100

    fig = px.bar(
        agg,
        x="work_interfere",
        y="pct",
        category_orders={"work_interfere": order_work_interfere(agg["work_interfere"].tolist())},
        labels={"work_interfere": "Work interference", "pct": "Percent"},
    )
    fig.update_traces(hovertemplate="%{x}<br>%{y:.1f}%<extra></extra>")
    return beautify_fig(fig, legend=False)

def fig_overview_heatmap(dff):
    needed = {"gender", "treatment"}
    if len(dff) == 0 or not needed.issubset(dff.columns):
        return make_empty_figure()

    if "benefits" not in dff.columns or "seek_help" not in dff.columns:
        return make_empty_figure("Missing support columns.")

    tmp = dff.copy()
    tmp["gender"] = ensure_str(tmp["gender"])
    tmp["treatment"] = ensure_str(tmp["treatment"])
    tmp["benefits"] = ensure_str(tmp["benefits"])
    tmp["seek_help"] = ensure_str(tmp["seek_help"])

    rows = []
    for metric in ["benefits", "seek_help"]:
        sub = (
            tmp.groupby(["gender", metric], dropna=False)
            .size()
            .reset_index(name="count")
        )
        yes_mask = sub[metric].astype(str) == "Yes"
        sub = sub[yes_mask].copy()
        sub["metric"] = metric
        rows.append(sub[["gender", "metric", "count"]])

    heat = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    if len(heat) == 0:
        return make_empty_figure()

    totals = heat.groupby("metric")["count"].transform("sum")
    heat["rate"] = heat["count"] / totals * 100
    heat["metric"] = heat["metric"].replace(
        {"benefits": "Benefits available", "seek_help": "Encourages help-seeking"}
    )

    fig = px.density_heatmap(
        heat,
        x="metric",
        y="gender",
        z="rate",
        text_auto=".1f",
        color_continuous_scale="Tealgrn",
        labels={"metric": "", "gender": "Gender", "rate": "Percent"},
    )
    return beautify_fig(fig, legend=False)

def fig_demographic_treemap(dff):
    if len(dff) == 0 or "gender" not in dff.columns or "age_bin" not in dff.columns:
        return make_empty_figure()

    tmp = dff.copy()
    tmp["gender"] = ensure_str(tmp["gender"])
    tmp["age_bin"] = ensure_str(tmp["age_bin"])

    agg = tmp.groupby(["gender", "age_bin"], dropna=False).size().reset_index(name="count")

    fig = px.treemap(
        agg,
        path=[px.Constant("All respondents"), "gender", "age_bin"],
        values="count",
        color="gender",
        color_discrete_map=GENDER_COLORS,
    )
    return beautify_fig(fig, legend=False)

def fig_age_box(dff):
    if len(dff) == 0 or "gender" not in dff.columns or "age" not in dff.columns:
        return make_empty_figure()

    tmp = dff.copy()
    tmp = tmp[pd.to_numeric(tmp["age"], errors="coerce").notna()].copy()
    tmp["age"] = pd.to_numeric(tmp["age"], errors="coerce")
    tmp["gender"] = ensure_str(tmp["gender"])

    if len(tmp) == 0:
        return make_empty_figure("No numeric age values available.")

    fig = px.box(
        tmp,
        x="gender",
        y="age",
        color="gender",
        color_discrete_map=GENDER_COLORS,
        points="outliers",
        labels={"gender": "Gender", "age": "Age"},
    )
    return beautify_fig(fig)

def fig_support_bubble(dff):
    needed = {"region", "benefits", "seek_help", "treatment"}
    if len(dff) == 0 or not needed.issubset(dff.columns):
        return make_empty_figure()

    tmp = dff.copy()
    for c in ["region", "benefits", "seek_help", "treatment"]:
        tmp[c] = ensure_str(tmp[c])

    grp = tmp.groupby("region", dropna=False).agg(
        n=("treatment", "size"),
        benefits_yes=("benefits", lambda x: (x == "Yes").mean() * 100),
        seek_yes=("seek_help", lambda x: (x == "Yes").mean() * 100),
        treatment_yes=("treatment", lambda x: (x == "Yes").mean() * 100),
    ).reset_index()

    fig = px.scatter(
        grp,
        x="benefits_yes",
        y="seek_yes",
        size="n",
        color="treatment_yes",
        hover_name="region",
        custom_data=["region"],
        labels={
            "benefits_yes": "Benefits available (%)",
            "seek_yes": "Help-seeking support (%)",
            "treatment_yes": "Treatment rate (%)",
        },
        color_continuous_scale="Blues",
    )
    return beautify_fig(fig, legend=False)

def fig_support_stacked(dff):
    needed = {"benefits", "treatment"}
    if len(dff) == 0 or not needed.issubset(dff.columns):
        return make_empty_figure()

    tmp = dff.copy()
    tmp["benefits"] = ensure_str(tmp["benefits"])
    tmp["treatment"] = ensure_str(tmp["treatment"])

    agg = tmp.groupby(["benefits", "treatment"], dropna=False).size().reset_index(name="count")
    fig = px.bar(
        agg,
        x="benefits",
        y="count",
        color="treatment",
        barmode="stack",
        category_orders={
            "benefits": order_yes_no_unknown(agg["benefits"].tolist()),
            "treatment": order_yes_no_unknown(agg["treatment"].tolist()),
        },
    )
    return beautify_fig(fig)

def fig_region_support_heatmap(dff):
    needed = {"region", "benefits", "seek_help", "anonymity"}
    if len(dff) == 0 or not needed.issubset(dff.columns):
        return make_empty_figure()

    tmp = dff.copy()
    for c in ["region", "benefits", "seek_help", "anonymity"]:
        tmp[c] = ensure_str(tmp[c])

    metrics = []
    for col, label in [
        ("benefits", "Benefits"),
        ("seek_help", "Seek help"),
        ("anonymity", "Anonymity"),
    ]:
        g = tmp.groupby("region", dropna=False)[col].apply(lambda x: (x == "Yes").mean() * 100).reset_index(name="rate")
        g["metric"] = label
        metrics.append(g)

    heat = pd.concat(metrics, ignore_index=True)
    fig = px.density_heatmap(
        heat,
        x="metric",
        y="region",
        z="rate",
        text_auto=".1f",
        color_continuous_scale="Tealgrn",
        labels={"metric": "", "region": "Region", "rate": "Percent"},
    )
    return beautify_fig(fig, legend=False)

def fig_country_map(dff):
    if len(dff) == 0 or "country" not in dff.columns:
        return make_empty_figure("No country column found.")

    tmp = dff.copy()
    tmp["country"] = ensure_str(tmp["country"])

    if "treatment" in tmp.columns:
        grp = tmp.groupby("country", dropna=False).agg(
            n=("country", "size"),
            treatment_rate=("treatment", lambda x: (x.astype(str) == "Yes").mean() * 100),
        ).reset_index()
    else:
        grp = tmp.groupby("country", dropna=False).size().reset_index(name="n")
        grp["treatment_rate"] = grp["n"]

    fig = px.choropleth(
        grp,
        locations="country",
        locationmode="country names",
        color="treatment_rate",
        hover_name="country",
        custom_data=["country"],
        color_continuous_scale="Blues",
        labels={"treatment_rate": "Treatment rate (%)"},
    )
    return beautify_fig(fig, legend=False)

def fig_remote_donut(dff):
    if len(dff) == 0 or "remote_work" not in dff.columns:
        return make_empty_figure()

    tmp = dff.copy()
    tmp["remote_work"] = ensure_str(tmp["remote_work"])
    agg = tmp["remote_work"].value_counts(dropna=False).reset_index()
    agg.columns = ["remote_work", "count"]

    fig = px.pie(
        agg,
        names="remote_work",
        values="count",
        hole=0.58,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    return beautify_fig(fig)

def fig_country_treatment_bar(dff):
    if len(dff) == 0 or "country" not in dff.columns or "treatment" not in dff.columns:
        return make_empty_figure()

    tmp = dff.copy()
    tmp["country"] = ensure_str(tmp["country"])
    tmp["treatment"] = ensure_str(tmp["treatment"])

    grp = tmp.groupby("country", dropna=False).agg(
        n=("country", "size"),
        treatment_rate=("treatment", lambda x: (x == "Yes").mean() * 100),
    ).reset_index()

    grp = grp.sort_values("n", ascending=False).head(12)
    fig = px.bar(
        grp,
        x="country",
        y="treatment_rate",
        labels={"country": "Country", "treatment_rate": "Treatment rate (%)"},
    )
    return beautify_fig(fig, legend=False)

# -----------------------------
# Data prep for dropdowns
# -----------------------------
years = sorted(df["year"].dropna().unique()) if "year" in df.columns else []
regions = sorted(df["region"].dropna().unique()) if "region" in df.columns else []
genders = sorted(df["gender"].dropna().unique()) if "gender" in df.columns else []
age_bins = order_age_bin(df["age_bin"].dropna().unique()) if "age_bin" in df.columns else []
company_sizes = order_company_size(df["company_size"].dropna().unique()) if "company_size" in df.columns else []
remote_vals = sorted(df["remote_work"].dropna().unique()) if "remote_work" in df.columns else []

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
# Sidebar
# -----------------------------
filters = dbc.Card(
    dbc.CardBody(
        [
            html.Div("Filters", style={"fontSize": "16px", "fontWeight": "700", "marginBottom": "16px"}),

            html.Label("Year"),
            dcc.Dropdown(
                options=[{"label": str(y), "value": y} for y in years],
                value=years[0] if years else None,
                id="f-year",
                clearable=False,
            ),

            html.Div(style={"height": "14px"}),

            html.Label("Region"),
            dcc.Dropdown(
                options=[{"label": r, "value": r} for r in regions],
                value=["North America"] if "North America" in regions else (regions[:1] if regions else []),
                id="f-region",
                multi=True,
            ),

            html.Div(style={"height": "14px"}),

            html.Label("Gender"),
            dcc.Dropdown(
                options=[{"label": g, "value": g} for g in genders],
                value=genders,
                id="f-gender",
                multi=True,
            ),

            html.Div(style={"height": "14px"}),

            html.Label("Age bin"),
            dcc.Dropdown(
                options=[{"label": a, "value": a} for a in age_bins],
                value=age_bins,
                id="f-agebin",
                multi=True,
            ),

            html.Div(style={"height": "14px"}),

            html.Label("Company size"),
            dcc.Dropdown(
                options=[{"label": c, "value": c} for c in company_sizes],
                value=company_sizes,
                id="f-company",
                multi=True,
            ),

            html.Div(style={"height": "14px"}),

            html.Label("Remote work"),
            dcc.Dropdown(
                options=[{"label": r, "value": r} for r in remote_vals],
                value=remote_vals,
                id="f-remote",
                multi=True,
            ),

            html.Hr(),

            html.Div("Linked selections", style={"fontWeight": "700", "marginBottom": "8px"}),
            html.Div(id="selected-tags", style={"marginBottom": "12px"}),

            dbc.Button(
                "Reset linked selection",
                id="btn-reset-linked",
                color="secondary",
                outline=True,
                size="sm",
            ),
        ]
    ),
    style=CARD_STYLE,
)

# -----------------------------
# Tabs
# -----------------------------
overview_tab = html.Div(
    [
        html.Div(id="kpi-area", style={"marginBottom": "16px"}),

        dbc.Row(
            [
                dbc.Col(
                    wrap_chart(
                        "Linked selection source",
                        "Click an age group to update the other overview panels.",
                        "overview-age-bar",
                    ),
                    md=6,
                ),
                dbc.Col(
                    wrap_chart(
                        "Support composition",
                        "Distribution of employer mental-health benefits under the current linked filters.",
                        "overview-support-donut",
                    ),
                    md=6,
                ),
            ],
            className="g-3",
        ),

        html.Div(style={"height": "16px"}),

        dbc.Row(
            [
                dbc.Col(
                    wrap_chart(
                        "Work interference among treated respondents",
                        "How often mental health affects work for treated respondents.",
                        "overview-interference-bar",
                    ),
                    md=6,
                ),
                dbc.Col(
                    wrap_chart(
                        "Support profile heatmap",
                        "Comparison of support signals across demographic groups.",
                        "overview-support-heatmap",
                    ),
                    md=6,
                ),
            ],
            className="g-3",
        ),
    ]
)

demographics_tab = html.Div(
    [
        dbc.Row(
            [
                dbc.Col(
                    wrap_chart(
                        "Demographic treemap",
                        "Composition of respondents by gender and age group.",
                        "demo-treemap",
                    ),
                    md=6,
                ),
                dbc.Col(
                    wrap_chart(
                        "Age distribution",
                        "Distribution of reported ages across gender groups.",
                        "demo-age-box",
                    ),
                    md=6,
                ),
            ],
            className="g-3",
        ),
    ]
)

support_tab = html.Div(
    [
        dbc.Row(
            [
                dbc.Col(
                    wrap_chart(
                        "Regional support landscape",
                        "Bubble size reflects sample size; color reflects treatment rate.",
                        "support-bubble",
                    ),
                    md=6,
                ),
                dbc.Col(
                    wrap_chart(
                        "Benefits vs treatment",
                        "Treatment composition across employer mental-health benefits.",
                        "support-stacked",
                    ),
                    md=6,
                ),
            ],
            className="g-3",
        ),

        html.Div(style={"height": "16px"}),

        dbc.Row(
            [
                dbc.Col(
                    wrap_chart(
                        "Regional support heatmap",
                        "Click a region to filter charts across tabs.",
                        "support-heatmap",
                    ),
                    md=12,
                ),
            ],
            className="g-3",
        ),
    ]
)

geo_tab = html.Div(
    [
        dbc.Row(
            [
                dbc.Col(
                    wrap_chart(
                        "Global treatment map",
                        "Click a country to apply a linked selection.",
                        "geo-map",
                    ),
                    md=7,
                ),
                dbc.Col(
                    wrap_chart(
                        "Remote work composition",
                        "Breakdown of remote-work status under the current linked filters.",
                        "geo-remote-donut",
                    ),
                    md=5,
                ),
            ],
            className="g-3",
        ),

        html.Div(style={"height": "16px"}),

        dbc.Row(
            [
                dbc.Col(
                    wrap_chart(
                        "Country treatment comparison",
                        "Top countries by response count and treatment rate.",
                        "geo-country-bar",
                    ),
                    md=12,
                ),
            ],
            className="g-3",
        ),
    ]
)

app.layout = dbc.Container(
    fluid=True,
    style={
        "minHeight": "100vh",
        "backgroundColor": COLORS["bg"],
        "padding": "18px",
    },
    children=[
        html.Div(
            [
                html.Div(
                    [
                        html.H2(
                            "Workplace Mental Health Dashboard",
                            style={
                                "fontWeight": "700",
                                "color": COLORS["text"],
                                "marginBottom": "2px",
                            },
                        ),
                        html.Div(
                            "Interactive exploration of treatment patterns, demographic structure, workplace support, and geography.",
                            style={"color": COLORS["muted"]},
                        ),
                    ]
                )
            ],
            style={"marginBottom": "16px"},
        ),

        dcc.Store(id="store-selected-age"),
        dcc.Store(id="store-selected-country"),
        dcc.Store(id="store-selected-region"),

        dbc.Row(
            [
                dbc.Col(filters, width=3),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            dcc.Tabs(
                                id="main-tabs",
                                value="tab-overview",
                                children=[
                                    dcc.Tab(label="Overview", value="tab-overview", children=overview_tab),
                                    dcc.Tab(label="Demographics", value="tab-demographics", children=demographics_tab),
                                    dcc.Tab(label="Support Systems", value="tab-support", children=support_tab),
                                    dcc.Tab(label="Geography & Work Style", value="tab-geo", children=geo_tab),
                                ],
                            )
                        ),
                        style=CARD_STYLE,
                    ),
                    width=9,
                ),
            ],
            className="g-3",
        ),
    ],
)

# -----------------------------
# Linked selection callback
# -----------------------------
@app.callback(
    Output("store-selected-age", "data"),
    Output("store-selected-country", "data"),
    Output("store-selected-region", "data"),
    Input("overview-age-bar", "clickData"),
    Input("geo-map", "clickData"),
    Input("support-heatmap", "clickData"),
    Input("btn-reset-linked", "n_clicks"),
    State("store-selected-age", "data"),
    State("store-selected-country", "data"),
    State("store-selected-region", "data"),
    prevent_initial_call=True,
)
def update_linked_selection(age_click, geo_click, region_click, reset_clicks,
                            current_age, current_country, current_region):
    triggered = callback_context.triggered[0]["prop_id"].split(".")[0]

    if triggered == "btn-reset-linked":
        return None, None, None

    if triggered == "overview-age-bar" and age_click:
        try:
            age_val = age_click["points"][0]["customdata"][0]
            return (None if current_age == age_val else age_val), current_country, current_region
        except Exception:
            return current_age, current_country, current_region

    if triggered == "geo-map" and geo_click:
        try:
            country_val = geo_click["points"][0]["customdata"][0]
            return current_age, (None if current_country == country_val else country_val), current_region
        except Exception:
            return current_age, current_country, current_region

    if triggered == "support-heatmap" and region_click:
        try:
            point = region_click["points"][0]
            region_val = point.get("y")
            return current_age, current_country, (None if current_region == region_val else region_val)
        except Exception:
            return current_age, current_country, current_region

    return current_age, current_country, current_region

# -----------------------------
# Main update callback
# -----------------------------
@app.callback(
    Output("kpi-area", "children"),
    Output("selected-tags", "children"),

    Output("overview-age-bar", "figure"),
    Output("overview-support-donut", "figure"),
    Output("overview-interference-bar", "figure"),
    Output("overview-support-heatmap", "figure"),

    Output("demo-treemap", "figure"),
    Output("demo-age-box", "figure"),

    Output("support-bubble", "figure"),
    Output("support-stacked", "figure"),
    Output("support-heatmap", "figure"),

    Output("geo-map", "figure"),
    Output("geo-remote-donut", "figure"),
    Output("geo-country-bar", "figure"),

    Input("f-year", "value"),
    Input("f-region", "value"),
    Input("f-gender", "value"),
    Input("f-agebin", "value"),
    Input("f-company", "value"),
    Input("f-remote", "value"),
    Input("store-selected-age", "data"),
    Input("store-selected-country", "data"),
    Input("store-selected-region", "data"),
)
def update_dashboard(year, region, gender, agebin, company, remote,
                     selected_age, selected_country, selected_region):
    base = filtered_df(df, year, region, gender, agebin, company, remote)
    linked = apply_linked_filters(base, selected_age, selected_country, selected_region)

    tags = []
    if selected_age:
        tags.append(dbc.Badge(f"Age: {selected_age}", color="primary", className="me-1"))
    if selected_country:
        tags.append(dbc.Badge(f"Country: {selected_country}", color="info", className="me-1"))
    if selected_region:
        tags.append(dbc.Badge(f"Region: {selected_region}", color="success", className="me-1"))
    if not tags:
        tags = html.Div("No linked selection active.", style={"color": COLORS["muted"], "fontSize": "13px"})

    return (
        build_kpis(linked),
        tags,

        fig_treatment_by_age(base),
        fig_support_donut(linked),
        fig_interference_bar(linked),
        fig_overview_heatmap(linked),

        fig_demographic_treemap(linked),
        fig_age_box(linked),

        fig_support_bubble(linked),
        fig_support_stacked(linked),
        fig_region_support_heatmap(base),

        fig_country_map(base),
        fig_remote_donut(linked),
        fig_country_treatment_bar(linked),
    )

if __name__ == "__main__":
    app.run(debug=True)
