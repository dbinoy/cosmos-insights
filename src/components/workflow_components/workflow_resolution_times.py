from dash import html, dcc
import dash_bootstrap_components as dbc

def get_resolution_times_layout():
    return dbc.Card([
        dbc.CardHeader([
            dbc.Row([
                dbc.Col([
                    html.H5("Resolution Times Analysis", className="mb-0")
                ], width=8),
                dbc.Col([
                    dbc.ButtonGroup([
                        dbc.Button("Box Plot", id="workflow-resolution-box-btn", size="sm", outline=True, active=True),
                        dbc.Button("Summary", id="workflow-resolution-summary-btn", size="sm", outline=True)
                    ], size="sm")
                ], width=4, className="text-end")
            ])
        ]),
        dbc.CardBody([
            dcc.Loading(
                dcc.Graph(id="workflow-resolution-times-chart", style={'height': '400px'}),
                type="default"
            ),
            html.Div(id="workflow-resolution-insights", className="mt-3")
        ])
    ], className="mb-4")