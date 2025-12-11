from dash import html, dcc
import dash_bootstrap_components as dbc

def get_violation_trends_layout():
    return dbc.Card([
        dbc.CardHeader([
            dbc.Row([
                dbc.Col([
                    html.H5("Violation Trends", className="mb-0"),
                    html.Small("Historical trends in compliance violations", className="text-muted")
                ], width=6),
                dbc.Col([
                    dcc.Dropdown(
                        id="compliance-trends-period-dropdown",
                        options=[
                            {"label": "Daily", "value": "daily"},
                            {"label": "Weekly", "value": "weekly"},
                            {"label": "Monthly", "value": "monthly"},
                            {"label": "Quarterly", "value": "quarterly"}
                        ],
                        value="monthly",
                        clearable=False,
                        className="form-select-sm"
                    )
                ], width=3),
                dbc.Col([
                    dcc.Dropdown(
                        id="compliance-trends-metric-dropdown",
                        options=[
                            {"label": "Case Count", "value": "cases"},
                            {"label": "Report Count", "value": "reports"},
                            {"label": "Total Fines", "value": "fines"},
                            {"label": "Resolution Time", "value": "resolution"}
                        ],
                        value="cases",
                        clearable=False,
                        className="form-select-sm"
                    )
                ], width=3)
            ])
        ]),
        dbc.CardBody([
            dcc.Loading([
                dcc.Graph(id="compliance-violation-trends-chart")
            ], type="dot")
        ])
    ], className="mb-4")