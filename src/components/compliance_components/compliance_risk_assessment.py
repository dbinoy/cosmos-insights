from dash import html, dcc
import dash_bootstrap_components as dbc

def get_risk_assessment_layout():
    return dbc.Card([
        dbc.CardHeader([
            dbc.Row([
                dbc.Col([
                    html.H5("Risk Assessment", className="mb-0"),
                    html.Small("Risk indicators and compliance risk matrix", className="text-muted")
                ], width=8),
                dbc.Col([
                    dcc.Dropdown(
                        id="compliance-risk-view-dropdown",
                        options=[
                            {"label": "Risk Matrix", "value": "matrix"},
                            {"label": "Risk Trends", "value": "trends"},
                            {"label": "High Risk Items", "value": "high_risk"},
                            {"label": "Mitigation Status", "value": "mitigation"}
                        ],
                        value="matrix",
                        clearable=False,
                        className="form-select-sm"
                    )
                ], width=4)
            ])
        ]),
        dbc.CardBody([
            dcc.Loading([
                dcc.Graph(id="compliance-risk-assessment-chart")
            ], type="dot")
        ])
    ], className="mb-4")