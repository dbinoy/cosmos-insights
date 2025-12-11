from dash import html, dcc
import dash_bootstrap_components as dbc

def get_office_performance_layout():
    return dbc.Card([
        dbc.CardHeader([
            dbc.Row([
                dbc.Col([
                    html.H5("Office Performance", className="mb-0"),
                    html.Small("Compliance performance by office and region", className="text-muted")
                ], width=6),
                dbc.Col([
                    dcc.Dropdown(
                        id="compliance-office-count-dropdown",
                        options=[
                            {"label": "Top 10", "value": 10},
                            {"label": "Top 20", "value": 20},
                            {"label": "All Offices", "value": "all"}
                        ],
                        value=10,
                        clearable=False,
                        className="form-select-sm"
                    )
                ], width=3),
                dbc.Col([
                    dcc.Dropdown(
                        id="compliance-office-metric-dropdown",
                        options=[
                            {"label": "Violation Rate", "value": "rate"},
                            {"label": "Total Cases", "value": "cases"},
                            {"label": "Total Fines", "value": "fines"},
                            {"label": "Compliance Score", "value": "score"}
                        ],
                        value="rate",
                        clearable=False,
                        className="form-select-sm"
                    )
                ], width=3)
            ])
        ]),
        dbc.CardBody([
            dcc.Loading([
                dcc.Graph(id="compliance-office-performance-chart")
            ], type="dot")
        ])
    ], className="mb-4")