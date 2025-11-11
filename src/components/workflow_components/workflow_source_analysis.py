from dash import html, dcc
import dash_bootstrap_components as dbc

def get_source_analysis_layout():
    return dbc.Card([
        dbc.CardHeader([
            html.H5("Ticket Source/Origin Analysis", className="mb-0")
        ]),
        dbc.CardBody([
            dcc.Loading(
                dcc.Graph(id="workflow-source-analysis-chart", style={'height': '400px'}),
                type="default"
            ),
            html.Div(id="workflow-source-insights", className="mt-3")
        ])
    ], className="mb-4")