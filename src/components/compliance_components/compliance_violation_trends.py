from dash import html, dcc
import dash_bootstrap_components as dbc

def get_violation_trends_layout():
    return html.Div([
        # Main violation trends card
        dbc.Card([
            dbc.CardHeader([
                dbc.Row([
                    dbc.Col([
                        html.H5("Violation Trends", className="mb-0"),
                    ], width=4),
                    dbc.Col([
                        # Period selection dropdown
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
                        # Metric selection dropdown 
                        dcc.Dropdown(
                            id="compliance-trends-metric-dropdown",
                            options=[
                                {"label": "Violation Types", "value": "violation_types"},
                                {"label": "Rule Categories", "value": "rule_categories"},
                                {"label": "Violation Volume", "value": "violation_volume"},
                                {"label": "Case Severity", "value": "severity_trends"}
                            ],
                            value="violation_types",
                            clearable=False,
                            className="form-select-sm"
                        )
                    ], width=5)
                ])
            ]),
            dbc.CardBody([
                # Chart wrapper for modal functionality
                html.Div([
                    dcc.Loading([
                        dcc.Graph(id="compliance-violation-trends-chart")
                    ], type="dot")
                ], 
                id="compliance-violation-trends-chart-wrapper",
                style={"cursor": "pointer"}),
                
                html.Hr(),
                
                # Insights section
                html.Div(id="compliance-violation-trends-insights", className="insights-container")
            ])
        ], className="mb-4 h-100")
    ])