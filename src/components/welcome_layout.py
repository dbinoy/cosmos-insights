from dash import html
import dash_bootstrap_components as dbc

def welcome_layout():
    return dbc.Container(
        [
            dbc.Row(
                dbc.Col(
                    [
                        html.H1("Welcome to Cosmos Insights", className="display-4 mb-3"),
                        html.P(
                            "Select a dashboard from the menu on the left to get started.",
                            className="lead mb-4"
                        ),
                        html.Hr(),
                        html.P(
                            "Use the sidebar navigation to switch between Training, Workflow, and Compliance dashboards.",
                            className="text-muted"
                        ),
                    ],
                    width=12,
                    className="text-center mt-5"
                )
            )
        ],
        fluid=True,
        className="py-5"
    )