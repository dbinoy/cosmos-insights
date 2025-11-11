from dash import html, dcc
import dash_bootstrap_components as dbc

def get_classification_analysis_layout():
    return dbc.Card([
        dbc.CardHeader([
            dbc.Row([
                dbc.Col([
                    html.H5("Tickets by Classification & Type", className="mb-0")
                ], width=8),
                dbc.Col([
                    dbc.ButtonGroup([
                        dbc.Button("Stacked", id="workflow-class-stacked-btn", size="sm", outline=True, active=True),
                        dbc.Button("Heatmap", id="workflow-class-heatmap-btn", size="sm", outline=True)
                    ], size="sm")
                ], width=4, className="text-end")
            ])
        ]),
        dbc.CardBody([
            dcc.Loading(
                dcc.Graph(id="workflow-classification-chart", style={'height': '400px'}),
                type="default"
            ),
            html.Div(id="workflow-classification-insights", className="mt-3")
        ])
    ], className="mb-4")