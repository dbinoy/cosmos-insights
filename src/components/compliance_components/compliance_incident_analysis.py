from dash import html, dcc
import dash_bootstrap_components as dbc

def get_incident_analysis_layout():
    return html.Div([
        # Main incident analysis card
        dbc.Card([
            dbc.CardHeader([
                dbc.Row([
                    dbc.Col([
                        html.H5("Incident Analysis", className="mb-0"),
                    ], width=6),
                    dbc.Col([
                        # View selection dropdown
                        dcc.Dropdown(
                            id="compliance-incident-view-dropdown",
                            options=[
                                {"label": "By Category", "value": "category"},
                                {"label": "By Rule Type", "value": "rule"},
                                {"label": "By Violation", "value": "violation"},
                                {"label": "By Disposition", "value": "disposition"}                             
                            ],
                            value="category",
                            clearable=False,
                            className="form-select-sm"
                        )
                    ], width=6)
                ])
            ]),
            dbc.CardBody([
                # Chart wrapper for modal functionality
                html.Div([
                    dcc.Loading([
                        dcc.Graph(id="compliance-incident-analysis-chart")
                    ], type="dot")
                ], 
                id="compliance-incident-analysis-chart-wrapper",
                style={"cursor": "pointer"}),
                
                html.Hr(),
                
                # Insights section
                html.Div(id="compliance-incident-analysis-insights", className="insights-container")
            ])
        ], className="mb-4 h-100")
    ])