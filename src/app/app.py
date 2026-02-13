# src/app/app.py
from __future__ import annotations

import pandas as pd
import altair as alt

from dash import Dash, html, dcc, Input, Output
import dash_bootstrap_components as dbc

from src.config import DATA_PROCESSED


def chart_to_html(chart: alt.Chart) -> str:

    return chart.to_html()


def benefits_bar(df: pd.DataFrame) -> alt.Chart:
    return (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("benefits:N", title="Mental health benefits"),
            y=alt.Y("count():Q", title="Count"),
            tooltip=["benefits:N", "count():Q"],
        )
        .properties(height=280)
    )


def treatment_by_gender(df: pd.DataFrame) -> alt.Chart:
    return (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("gender:N", sort="-y", title="Gender (normalized)"),
            y=alt.Y("count():Q", title="Count"),
            color=alt.Color("treatment:N", title="Sought treatment"),
            tooltip=["gender:N", "treatment:N", "count():Q"],
        )
        .properties(height=280)
    )


def load_data() -> pd.DataFrame:
    df = pd.read_parquet(DATA_PROCESSED)

    for col in ["benefits", "treatment", "gender", "region", "company_size"]:
        if col not in df.columns:
            df[col] = "Unknown"
    return df


def make_app() -> Dash:
    app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    df = load_data()

    region_options = sorted([x for x in df["region"].dropna().unique()])
    size_options = [str(x) for x in df["company_size"].dropna().unique()]

    app.layout = dbc.Container(
        [
            html.H1("Mental Health in Tech Dashboard (Prototype)"),
            html.P(
                "Prototype for DATA 551 Milestone 1. This app will evolve into a "
                "multi-view interactive dashboard in later milestones."
            ),
            html.Hr(),

            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label("Filter by region"),
                            dcc.Dropdown(
                                id="region_filter",
                                options=[{"label": r, "value": r} for r in region_options],
                                value=None,
                                placeholder="All regions",
                                clearable=True,
                            ),
                        ],
                        md=6,
                    ),
                    dbc.Col(
                        [
                            html.Label("Filter by company size"),
                            dcc.Dropdown(
                                id="size_filter",
                                options=[{"label": s, "value": s} for s in size_options],
                                value=None,
                                placeholder="All sizes",
                                clearable=True,
                            ),
                        ],
                        md=6,
                    ),
                ],
                className="g-3",
            ),

            html.Br(),

            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H4("Benefits distribution"),
                            html.Iframe(
                                id="chart_benefits",
                                style={"width": "100%", "height": "320px", "border": "none"},
                            ),
                        ],
                        md=6,
                    ),
                    dbc.Col(
                        [
                            html.H4("Treatment by gender"),
                            html.Iframe(
                                id="chart_treatment_gender",
                                style={"width": "100%", "height": "320px", "border": "none"},
                            ),
                        ],
                        md=6,
                    ),
                ],
                className="g-3",
            ),

            html.Hr(),
            html.P(
                "Next steps (Milestone 2): add linked selections between plots, "
                "additional views (e.g., work interference), and improved layout."
            ),
        ],
        fluid=True,
        className="p-4",
    )

    @app.callback(
        Output("chart_benefits", "srcDoc"),
        Output("chart_treatment_gender", "srcDoc"),
        Input("region_filter", "value"),
        Input("size_filter", "value"),
    )
    def update_charts(region_value, size_value):
        dff = df.copy()
        if region_value:
            dff = dff[dff["region"] == region_value]
        if size_value:

            dff = dff[dff["company_size"].astype(str) == str(size_value)]

        c1 = benefits_bar(dff)
        c2 = treatment_by_gender(dff)
        return chart_to_html(c1), chart_to_html(c2)



    return app


if __name__ == "__main__":
    app = make_app()
    app.run(debug=True)