from dash import html, dcc
import dash_bootstrap_components as dbc

def get_resolution_metrics_layout():
    return dbc.Card([
        dbc.CardHeader([
            dbc.Row([
                dbc.Col([
                    html.H5("Resolution Metrics", className="mb-0"),
                    html.Small("Time to resolution and recurring issues analysis", className="text-muted")
                ], width=8),
                dbc.Col([
                    dcc.Dropdown(
                        id="compliance-resolution-view-dropdown",
                        options=[
                            {"label": "Resolution Time", "value": "time"},
                            {"label": "Recurring Issues", "value": "recurring"},
                            {"label": "Resolution Rate", "value": "rate"},
                            {"label": "SLA Compliance", "value": "sla"}
                        ],
                        value="time",
                        clearable=False,
                        className="form-select-sm"
                    )
                ], width=4)
            ])
        ]),
        dbc.CardBody([
            dcc.Loading([
                dcc.Graph(id="compliance-resolution-metrics-chart")
            ], type="dot")
        ])
    ], className="mb-4")