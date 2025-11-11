from dash import html, dcc
import dash_bootstrap_components as dbc

def get_status_distribution_layout():
    return dbc.Card([
        dbc.CardHeader([
            html.H5("Ticket Status Distribution", className="mb-0")
        ]),
        dbc.CardBody([
            dcc.Loading(
                dcc.Graph(id="workflow-status-distribution-chart", style={'height': '400px'}),
                type="default"
            ),
            html.Div(id="workflow-status-insights", className="mt-3")
        ])
    ], className="mb-4")