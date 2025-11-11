from dash import html, dcc
import dash_bootstrap_components as dbc

def get_trends_analysis_layout():
    return dbc.Card([
        dbc.CardHeader([
            html.H5("Trends in Case Reasons & Issues", className="mb-0")
        ]),
        dbc.CardBody([
            dcc.Loading(
                dcc.Graph(id="workflow-trends-analysis-chart", style={'height': '400px'}),
                type="default"
            ),
            html.Div(id="workflow-trends-insights", className="mt-3")
        ])
    ], className="mb-4")