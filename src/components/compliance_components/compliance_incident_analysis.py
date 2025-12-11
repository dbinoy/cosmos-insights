from dash import html, dcc
import dash_bootstrap_components as dbc

def get_incident_analysis_layout():
    return dbc.Card([
        dbc.CardHeader([
            dbc.Row([
                dbc.Col([
                    html.H5("Incident Analysis", className="mb-0"),
                    html.Small("Types and frequency of compliance incidents", className="text-muted")
                ], width=8),
                dbc.Col([
                    dcc.Dropdown(
                        id="compliance-incident-view-dropdown",
                        options=[
                            {"label": "By Category", "value": "category"},
                            {"label": "By Rule Type", "value": "rule"},
                            {"label": "By Disposition", "value": "disposition"},
                            {"label": "By Frequency", "value": "frequency"}
                        ],
                        value="category",
                        clearable=False,
                        className="form-select-sm"
                    )
                ], width=4)
            ])
        ]),
        dbc.CardBody([
            dcc.Loading([
                dcc.Graph(id="compliance-incident-analysis-chart")
            ], type="dot")
        ])
    ], className="mb-4")