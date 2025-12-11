from dash import html, dcc
import dash_bootstrap_components as dbc

def get_agent_performance_layout():
    return dbc.Card([
        dbc.CardHeader([
            dbc.Row([
                dbc.Col([
                    html.H5("Agent Performance", className="mb-0"),
                    html.Small("Agents with highest violation counts and risk scores", className="text-muted")
                ], width=6),
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
                            {"label": "Violation Count", "value": "count"},
                            {"label": "Total Fines", "value": "fines"},
                            {"label": "Open Cases", "value": "open"},
                            {"label": "Risk Score", "value": "risk"}
                        ],
                        value="count",
                        clearable=False,
                        className="form-select-sm"
                    )
                ], width=3)
            ])
        ]),
        dbc.CardBody([
            dcc.Loading([
                dcc.Graph(id="compliance-agent-performance-chart")
            ], type="dot")
        ])
    ], className="mb-4")