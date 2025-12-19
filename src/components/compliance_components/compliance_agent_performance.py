from dash import html, dcc
import dash_bootstrap_components as dbc

def get_agent_performance_layout():
    return html.Div([
        # Main agent performance card
        dbc.Card([
            dbc.CardHeader([
                dbc.Row([
                    dbc.Col([
                        html.H5("Agent Performance", className="mb-0"),
                    ], width=5),
                    dbc.Col([
                        dcc.Dropdown(
                            id="compliance-agent-count-dropdown",
                            options=[
                                {"label": "Top 10", "value": 10},
                                {"label": "Top 20", "value": 20},
                                {"label": "Top 50", "value": 50}
                            ],
                            value=10,
                            clearable=False,
                            className="form-select-sm"
                        )
                    ], width=3),
                    dbc.Col([
                        dcc.Dropdown(
                            id="compliance-agent-metric-dropdown",
                            options=[
                                {"label": "Active Caseload", "value": "count"},
                                {"label": "Cases Handled", "value": "handled"},
                                {"label": "Open Cases", "value": "open"},
                                {"label": "Risk Assessment", "value": "efficiency"}
                            ],
                            value="count",
                            clearable=False,
                            className="form-select-sm"
                        )
                    ], width=4)
                ])
            ]),
            dbc.CardBody([
                # Chart wrapper for modal functionality
                html.Div([
                    dcc.Loading([
                        dcc.Graph(id="compliance-agent-performance-chart")
                    ], type="dot")
                ], style={"cursor": "pointer"}),
                
                html.Hr(),
                
                # Insights section
                html.Div(id="compliance-agent-performance-insights", className="insights-container")
            ])
        ], className="mb-4 h-100")
    ])