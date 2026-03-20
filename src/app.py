from pathlib import Path
import traceback

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc

# -----------------------------
# Paths / data
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "cleaned.csv"

if not DATA_PATH.exists():
    raise FileNotFoundError(
        f"Missing data file: {DATA_PATH}. Please make sure cleaned.csv is in data/processed/."
    )


def _safe_unique(values):
    return list(pd.Series(list(values), dtype="object").dropna().drop_duplicates())


def _ensure_str_series(s: pd.Series) -> pd.Series:
    return s.astype("string").fillna("<missing>")


def _order_age_bin(values):
    vals = _safe_unique(values)

    def key(v):
        s = str(v).strip()
        try:
            return int(s.split("-")[0].replace("+", ""))
        except Exception:
            return 10**9

    return sorted(vals, key=key)


def _order_company_size(values):
    vals = _safe_unique(values)

    def key(v):
        s = str(v).strip()
        try:
            if "+" in s:
                return int(s.replace("+", ""))
            return int(s.split("-")[0])
        except Exception:
            return 10**9

    return sorted(vals, key=key)


def _order_yes_no_unknown(values):
    priority = ["Yes", "No", "Don't know", "Not sure", "Maybe", "<missing>"]
    vals = _safe_unique(values)
    ordered = [v for v in priority if v in vals]
    ordered += sorted([v for v in vals if v not in ordered])
    return ordered


def _order_interfere(values):
    priority = ["Never", "Rarely", "Sometimes", "Often", "Don't know", "<missing>"]
    vals = _safe_unique(values)
    ordered = [v for v in priority if v in vals]
    ordered += sorted([v for v in vals if v not in ordered])
    return ordered


def _pick_col(df_: pd.DataFrame, candidates):
    for c in candidates:
        if c in df_.columns:
            return c
    return None


raw = pd.read_csv(DATA_PATH)
df = raw.copy()

# Normalize likely columns used in the dashboard
for c in df.columns:
    if df[c].dtype == object:
        df[c] = df[c].astype("string").str.strip()

# Harmonize geographic columns if possible
country_col = _pick_col(df, ["country", "Country"])
if country_col is None:
    df["country"] = "Unknown"
else:
    df["country"] = _ensure_str_series(df[country_col])

region_col = _pick_col(df, ["region", "Region"])
if region_col is None:
    df["region"] = "Unknown"
else:
    df["region"] = _ensure_str_series(df[region_col])

# Optional year handling
if "year" in df.columns:
    df["year"] = pd.to_numeric(df["year"], errors="coerce")

# Required-ish columns with fallbacks
fallbacks = {
    "gender": "Unknown",
    "age_bin": "Unknown",
    "company_size": "Unknown",
    "remote_work": "Unknown",
    "treatment": "Unknown",
    "work_interfere": "Unknown",
    "benefits": "Unknown",
    "seek_help": "Unknown",
}
for col, val in fallbacks.items():
    if col not in df.columns:
        df[col] = val
    df[col] = _ensure_str_series(df[col])

# Age numeric for boxplot when available
age_num_col = _pick_col(df, ["Age", "age"])
if age_num_col:
    df["age_numeric"] = pd.to_numeric(df[age_num_col], errors="coerce")
else:
    df["age_numeric"] = np.nan

# Remove unreasonable ages if present
if "age_numeric" in df.columns:
    df.loc[(df["age_numeric"] < 10) | (df["age_numeric"] > 100), "age_numeric"] = np.nan

# Geo mapping coverage
country_geo = px.data.gapminder()[["country", "iso_alpha"]].drop_duplicates()

COLORS = {
    "bg": "#F7F9FC",
    "panel": "#FFFFFF",
    "border": "#E6ECF4",
    "text": "#1F2937",
    "muted": "#667085",
    "primary": "#2F6BFF",
    "blue": "#4C78A8",
    "teal": "#72B7B2",
    "green": "#54A24B",
    "orange": "#F58518",
    "red": "#E45756",
    "purple": "#9C89B8",
}

CARD_STYLE = {
    "backgroundColor": COLORS["panel"],
    "border": f"1px solid {COLORS['border']}",
    "borderRadius": "16px",
    "boxShadow": "0 4px 18px rgba(15, 23, 42, 0.06)",
}


def filtered_df(dff, year, regions, genders, age_bins, company_sizes, remote_work, linked_age, linked_country, linked_region):
    out = dff.copy()

    if year and "year" in out.columns:
        out = out[out["year"] == float(year)]
    if regions:
        out = out[out["region"].isin(regions)]
    if genders:
        out = out[out["gender"].isin(genders)]
    if age_bins:
        out = out[out["age_bin"].isin(age_bins)]
    if company_sizes:
        out = out[out["company_size"].isin(company_sizes)]
    if remote_work:
        out = out[out["remote_work"].isin(remote_work)]

    if linked_age:
        out = out[out["age_bin"] == linked_age]
    if linked_country:
        out = out[out["country"] == linked_country]
    if linked_region:
        out = out[out["region"] == linked_region]

    return out


def empty_fig(msg="No data for current filters"):
    fig = go.Figure()
    fig.add_annotation(text=msg, x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False, font=dict(size=16))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(height=360, margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor="white", plot_bgcolor="white")
    return fig


def style_fig(fig, height=340):
    fig.update_layout(
        height=height,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=24, r=18, t=54, b=28),
        font=dict(color=COLORS["text"]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    fig.update_xaxes(showgrid=False, linecolor="#D6DEEA")
    fig.update_yaxes(gridcolor="#ECF1F7", linecolor="#D6DEEA")
    return fig


def pct_yes(series):
    s = series.astype(str)
    return round(100 * (s == "Yes").mean(), 1) if len(s) else 0.0


def kpi_cards(dff):
    n = len(dff)
    vals = [
        ("Sample Size", f"{n:,}"),
        ("Treatment Rate", f"{pct_yes(dff['treatment']) if n else 0:.1f}%"),
        ("Benefits Available", f"{pct_yes(dff['benefits']) if n else 0:.1f}%"),
        ("Help-Seeking Climate", f"{pct_yes(dff['seek_help']) if n else 0:.1f}%"),
    ]
    cols = []
    for title, value in vals:
        cols.append(
            dbc.Col(
                dbc.Card(
                    dbc.CardBody([
                        html.Div(title, style={"fontSize": "12px", "color": COLORS["muted"], "fontWeight": "600"}),
                        html.Div(value, style={"fontSize": "30px", "fontWeight": "700", "marginTop": "8px"}),
                    ]),
                    style={**CARD_STYLE, "height": "100%"},
                ),
                md=3,
            )
        )
    return dbc.Row(cols, className="g-3")


def fig_treatment_age_gender(dff):
    if dff.empty:
        return empty_fig()
    age_order = _order_age_bin(dff["age_bin"])
    agg = dff.groupby(["age_bin", "gender"], dropna=False).agg(n=("treatment", "size"), yes=("treatment", lambda x: (x.astype(str) == "Yes").sum())).reset_index()
    agg["rate"] = np.where(agg["n"] > 0, agg["yes"] / agg["n"] * 100, 0)
    fig = px.bar(
        agg,
        x="age_bin",
        y="rate",
        color="gender",
        barmode="group",
        category_orders={"age_bin": age_order},
        custom_data=["age_bin"],
        labels={"rate": "Treatment rate (%)", "age_bin": "Age group"},
    )
    fig.update_traces(hovertemplate="Age: %{x}<br>Rate: %{y:.1f}%<extra></extra>")
    return style_fig(fig)


def fig_interference(dff):
    if dff.empty:
        return empty_fig()
    order = _order_interfere(dff["work_interfere"])
    sub = dff[dff["treatment"].astype(str) == "Yes"]
    agg = sub.groupby("work_interfere", dropna=False).size().reset_index(name="count")
    total = agg["count"].sum()
    agg["pct"] = np.where(total > 0, agg["count"] / total * 100, 0)
    fig = px.bar(
        agg,
        x="work_interfere",
        y="pct",
        category_orders={"work_interfere": order},
        labels={"pct": "Percent", "work_interfere": "Work interference"},
    )
    return style_fig(fig)


def fig_support_donut(dff):
    if dff.empty:
        return empty_fig()
    agg = dff.groupby("benefits", dropna=False).size().reset_index(name="count")
    fig = px.pie(agg, names="benefits", values="count", hole=0.58)
    fig.update_traces(textposition="inside", textinfo="percent+label")
    return style_fig(fig)


def fig_region_support_heatmap(dff):
    if dff.empty:
        return empty_fig()
    metrics = ["treatment", "benefits", "seek_help"]
    rows = []
    for region, sub in dff.groupby("region", dropna=False):
        for m in metrics:
            rows.append({"region": region, "metric": m, "rate": pct_yes(sub[m])})
    heat = pd.DataFrame(rows)
    metric_name = {"treatment": "Treatment", "benefits": "Benefits", "seek_help": "Seek help"}
    heat["metric"] = heat["metric"].map(metric_name)
    fig = px.imshow(
        heat.pivot(index="region", columns="metric", values="rate"),
        text_auto=".1f",
        aspect="auto",
        color_continuous_scale="Teal",
        labels=dict(color="Rate (%)"),
    )
    return style_fig(fig, height=390)


def fig_year_trend(dff):
    if dff.empty or "year" not in dff.columns or dff["year"].dropna().nunique() == 0:
        return empty_fig("Year trend unavailable")
    agg = dff.groupby("year", dropna=False).agg(n=("treatment", "size"), rate=("treatment", lambda x: (x.astype(str) == "Yes").mean() * 100)).reset_index()
    fig = px.line(agg, x="year", y="rate", markers=True, labels={"rate": "Treatment rate (%)"})
    return style_fig(fig)


def fig_gender_treemap(dff):
    if dff.empty:
        return empty_fig()
    agg = dff.groupby(["gender", "age_bin"], dropna=False).size().reset_index(name="count")
    fig = px.treemap(agg, path=[px.Constant("All respondents"), "gender", "age_bin"], values="count")
    return style_fig(fig, height=400)


def fig_age_box(dff):
    if dff.empty or dff["age_numeric"].dropna().empty:
        return empty_fig("Numeric age unavailable")
    fig = px.box(dff, x="gender", y="age_numeric", color="gender", labels={"age_numeric": "Age"})
    return style_fig(fig)


def fig_support_scatter(dff):
    if dff.empty:
        return empty_fig()
    agg = dff.groupby(["region", "country"], dropna=False).agg(
        n=("treatment", "size"),
        treatment_rate=("treatment", lambda x: (x.astype(str) == "Yes").mean() * 100),
        benefits_rate=("benefits", lambda x: (x.astype(str) == "Yes").mean() * 100),
        seek_help_rate=("seek_help", lambda x: (x.astype(str) == "Yes").mean() * 100),
    ).reset_index()
    fig = px.scatter(
        agg,
        x="benefits_rate",
        y="treatment_rate",
        size="n",
        color="region",
        hover_name="country",
        labels={"benefits_rate": "Benefits rate (%)", "treatment_rate": "Treatment rate (%)"},
    )
    return style_fig(fig)


def fig_stacked_support(dff):
    if dff.empty:
        return empty_fig()
    order = _order_yes_no_unknown(pd.concat([dff["benefits"], dff["seek_help"]]))
    long = pd.concat([
        dff[["benefits"]].rename(columns={"benefits": "response"}).assign(metric="Benefits"),
        dff[["seek_help"]].rename(columns={"seek_help": "response"}).assign(metric="Seek help"),
    ], ignore_index=True)
    agg = long.groupby(["metric", "response"], dropna=False).size().reset_index(name="count")
    fig = px.bar(agg, x="metric", y="count", color="response", barmode="stack", category_orders={"response": order})
    return style_fig(fig)


def fig_geo_map(dff):
    if dff.empty:
        return empty_fig()
    agg = dff.groupby("country", dropna=False).agg(n=("treatment", "size"), treatment_rate=("treatment", lambda x: (x.astype(str) == "Yes").mean() * 100)).reset_index()
    geo = agg.merge(country_geo, on="country", how="left")
    geo["iso_alpha"] = geo["iso_alpha"].fillna("UNK")
    fig = px.choropleth(
        geo[geo["iso_alpha"] != "UNK"],
        locations="iso_alpha",
        color="treatment_rate",
        hover_name="country",
        custom_data=["country"],
        color_continuous_scale="Blues",
        labels={"treatment_rate": "Treatment rate (%)"},
    )
    fig.update_geos(showframe=False, showcoastlines=True, coastlinecolor="#D4DCE8")
    return style_fig(fig, height=420)


def fig_remote_donut(dff):
    if dff.empty:
        return empty_fig()
    agg = dff.groupby("remote_work", dropna=False).size().reset_index(name="count")
    fig = px.pie(agg, names="remote_work", values="count", hole=0.55)
    fig.update_traces(textinfo="percent+label")
    return style_fig(fig)


def current_selection_badges(age, country, region):
    vals = []
    if age:
        vals.append(("Age", age))
    if country:
        vals.append(("Country", country))
    if region:
        vals.append(("Region", region))
    if not vals:
        return dbc.Alert("No linked selection active. Click charts to filter related views.", color="light", style={"borderRadius": "12px", "marginBottom": "12px"})

    return html.Div(
        [
            dbc.Badge(f"{k}: {v}", color="primary", pill=True, className="me-2", style={"fontSize": "0.9rem", "padding": "8px 12px"})
            for k, v in vals
        ],
        style={"marginBottom": "12px"},
    )


app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], title="Mental Health Dashboard")
server = app.server

years = sorted(df["year"].dropna().unique().tolist()) if "year" in df.columns else []
regions = sorted(_safe_unique(df["region"]))
genders = sorted(_safe_unique(df["gender"]))
age_bins = _order_age_bin(df["age_bin"])
company_sizes = _order_company_size(df["company_size"])
remote_vals = sorted(_safe_unique(df["remote_work"]))

hero = dbc.Card(
    dbc.CardBody([
        html.Div("Executive dashboard", style={"fontSize": "13px", "fontWeight": "700", "color": COLORS["primary"], "textTransform": "uppercase", "letterSpacing": "0.08em"}),
        html.H2("Workplace Mental Health Intelligence Hub", style={"marginTop": "8px", "marginBottom": "8px"}),
        html.P("Commercial-style analytics dashboard with multi-tab navigation, cross-chart interaction, geographic drilldown, and business-facing support metrics.", style={"color": COLORS["muted"], "marginBottom": 0}),
    ]),
    style={**CARD_STYLE, "marginBottom": "14px", "background": "linear-gradient(135deg, #FFFFFF 0%, #F5F8FF 100%)"},
)

sidebar = dbc.Card(
    dbc.CardBody([
        html.Div("Global filters", style={"fontWeight": "700", "fontSize": "15px", "marginBottom": "14px"}),
        html.Label("Year", style={"fontWeight": "600", "fontSize": "13px"}),
        dcc.Dropdown(id="f-year", options=[{"label": str(int(y)), "value": int(y)} for y in years], value=int(years[0]) if years else None, clearable=False),
        html.Div(style={"height": "12px"}),
        html.Label("Region", style={"fontWeight": "600", "fontSize": "13px"}),
        dcc.Dropdown(id="f-region", options=[{"label": x, "value": x} for x in regions], value=regions, multi=True),
        html.Div(style={"height": "12px"}),
        html.Label("Gender", style={"fontWeight": "600", "fontSize": "13px"}),
        dcc.Dropdown(id="f-gender", options=[{"label": x, "value": x} for x in genders], value=genders, multi=True),
        html.Div(style={"height": "12px"}),
        html.Label("Age group", style={"fontWeight": "600", "fontSize": "13px"}),
        dcc.Dropdown(id="f-agebin", options=[{"label": x, "value": x} for x in age_bins], value=age_bins, multi=True),
        html.Div(style={"height": "12px"}),
        html.Label("Company size", style={"fontWeight": "600", "fontSize": "13px"}),
        dcc.Dropdown(id="f-company", options=[{"label": x, "value": x} for x in company_sizes], value=company_sizes, multi=True),
        html.Div(style={"height": "12px"}),
        html.Label("Remote work", style={"fontWeight": "600", "fontSize": "13px"}),
        dcc.Dropdown(id="f-remote", options=[{"label": x, "value": x} for x in remote_vals], value=remote_vals, multi=True),
        html.Hr(),
        dbc.Button("Reset linked selection", id="reset-linked", color="primary", className="w-100"),
        html.Div(style={"height": "10px"}),
        html.Div(id="selection-state"),
        dcc.Store(id="store-age"),
        dcc.Store(id="store-country"),
        dcc.Store(id="store-region"),
    ]),
    style={**CARD_STYLE, "height": "100%"},
)


def graph_card(title, graph_id, height=340):
    return dbc.Card(
        dbc.CardBody([
            html.Div(title, style={"fontWeight": "700", "fontSize": "16px", "marginBottom": "14px", "lineHeight": "1.35", "color": COLORS["text"]}),
            html.Div(
                dcc.Graph(id=graph_id, config={"displayModeBar": False}, style={"height": f"{height}px"}),
                style={"marginTop": "6px"},
            ),
        ], style={"padding": "20px 20px 18px 20px"}),
        style={**CARD_STYLE, "height": "100%"},
    )


overview_tab = html.Div([
    html.Div(id="kpi-row", style={"marginBottom": "14px"}),
    dbc.Row([
        dbc.Col(graph_card("Linked selection source", "g-age-gender", 360), md=6),
        dbc.Col(graph_card("Support composition", "g-support-donut", 360), md=6),
    ], className="g-3 mb-3"),
    dbc.Row([
        dbc.Col(graph_card("Interference", "g-interference", 360), md=6),
        dbc.Col(graph_card("Regional heatmap", "g-heatmap", 390), md=6),
    ], className="g-3"),
])

demographics_tab = html.Div([
    dbc.Row([
        dbc.Col(graph_card("Demographic treemap", "g-treemap", 420), md=6),
        dbc.Col(graph_card("Age distribution", "g-age-box", 420), md=6),
    ], className="g-3 mb-3"),
    dbc.Row([
        dbc.Col(graph_card("Trend over time", "g-year-trend", 360), md=12),
    ], className="g-3"),
])

support_tab = html.Div([
    dbc.Row([
        dbc.Col(graph_card("Treatment vs benefits", "g-support-scatter", 380), md=7),
        dbc.Col(graph_card("Support stack", "g-support-stack", 380), md=5),
    ], className="g-3"),
])

geo_tab = html.Div([
    dbc.Row([
        dbc.Col(graph_card("Country map", "g-geo-map", 430), md=8),
        dbc.Col(graph_card("Remote work", "g-remote-donut", 430), md=4),
    ], className="g-3"),
])

main_tabs = dbc.Card(
    dbc.CardBody([
        dbc.Tabs([
            dbc.Tab(overview_tab, label="Overview"),
            dbc.Tab(demographics_tab, label="Demographics"),
            dbc.Tab(support_tab, label="Support Systems"),
            dbc.Tab(geo_tab, label="Geography & Work Style"),
        ])
    ]),
    style={**CARD_STYLE, "height": "100%"},
)

app.layout = dbc.Container(
    fluid=True,
    style={"backgroundColor": COLORS["bg"], "minHeight": "100vh", "padding": "18px"},
    children=[
        hero,
        dbc.Row([
            dbc.Col(sidebar, md=3),
            dbc.Col(main_tabs, md=9),
        ], className="g-3"),
    ],
)


@app.callback(
    Output("store-age", "data"),
    Output("store-country", "data"),
    Output("store-region", "data"),
    Input("g-age-gender", "clickData"),
    Input("g-geo-map", "clickData"),
    Input("g-heatmap", "clickData"),
    Input("reset-linked", "n_clicks"),
    State("store-age", "data"),
    State("store-country", "data"),
    State("store-region", "data"),
    prevent_initial_call=True,
)
def update_linked_filters(age_click, geo_click, heat_click, reset_clicks, current_age, current_country, current_region):
    trig = callback_context.triggered_id
    if trig == "reset-linked":
        return None, None, None

    if trig == "g-age-gender" and age_click:
        pt = age_click["points"][0]
        age_val = (pt.get("customdata") or [pt.get("x")])[0]
        return (None if current_age == age_val else age_val), current_country, current_region

    if trig == "g-geo-map" and geo_click:
        pt = geo_click["points"][0]
        country_val = (pt.get("customdata") or [pt.get("hovertext")])[0]
        return current_age, (None if current_country == country_val else country_val), current_region

    if trig == "g-heatmap" and heat_click:
        pt = heat_click["points"][0]
        region_val = pt.get("y")
        return current_age, current_country, (None if current_region == region_val else region_val)

    return current_age, current_country, current_region


@app.callback(
    Output("selection-state", "children"),
    Output("kpi-row", "children"),
    Output("g-age-gender", "figure"),
    Output("g-support-donut", "figure"),
    Output("g-interference", "figure"),
    Output("g-heatmap", "figure"),
    Output("g-treemap", "figure"),
    Output("g-age-box", "figure"),
    Output("g-year-trend", "figure"),
    Output("g-support-scatter", "figure"),
    Output("g-support-stack", "figure"),
    Output("g-geo-map", "figure"),
    Output("g-remote-donut", "figure"),
    Input("f-year", "value"),
    Input("f-region", "value"),
    Input("f-gender", "value"),
    Input("f-agebin", "value"),
    Input("f-company", "value"),
    Input("f-remote", "value"),
    Input("store-age", "data"),
    Input("store-country", "data"),
    Input("store-region", "data"),
)
def update_dashboard(year, regions_v, genders_v, age_bins_v, company_sizes_v, remote_v, linked_age, linked_country, linked_region):
    try:
        dff = filtered_df(df, year, regions_v, genders_v, age_bins_v, company_sizes_v, remote_v, linked_age, linked_country, linked_region)
        return (
            current_selection_badges(linked_age, linked_country, linked_region),
            kpi_cards(dff),
            fig_treatment_age_gender(dff),
            fig_support_donut(dff),
            fig_interference(dff),
            fig_region_support_heatmap(dff),
            fig_gender_treemap(dff),
            fig_age_box(dff),
            fig_year_trend(dff),
            fig_support_scatter(dff),
            fig_stacked_support(dff),
            fig_geo_map(dff),
            fig_remote_donut(dff),
        )
    except Exception as e:
        traceback.print_exc()
        err = empty_fig(f"Callback error: {e}")
        return current_selection_badges(linked_age, linked_country, linked_region), html.Div(), err, err, err, err, err, err, err, err, err, err, err


if __name__ == "__main__":
    app.run(debug=True)
