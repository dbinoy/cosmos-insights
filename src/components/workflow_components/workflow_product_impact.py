from dash import html, dcc
import dash_bootstrap_components as dbc

def get_product_impact_layout():
    return dbc.Card([
        dbc.CardHeader([
            html.H5("Product/Feature Impact", className="mb-0")
        ]),
        dbc.CardBody([
            # Display dropdown control (same style as Workload by Assignee)
            html.Div([
                dbc.Row([
                    dbc.Col([
                        html.Label("Display:", className="form-label mb-1", style={'fontSize': '13px', 'fontWeight': '500'}),
                        dcc.Dropdown(
                            id="workflow-product-count-dropdown",
                            options=[
                                {'label': 'Top 5', 'value': 5},
                                {'label': 'Top 10', 'value': 10},
                                {'label': 'Top 15', 'value': 15},
                                {'label': 'Top 20', 'value': 20},
                                {'label': 'Top 25', 'value': 25},
                                {'label': 'Top 50', 'value': 50}
                            ],
                            value=15,
                            clearable=False,
                            style={'fontSize': '12px'},
                            className="mb-3"
                        )
                    ], width=3)
                ])
            ], style={'display': 'block', 'marginBottom': '15px'}),
            dcc.Loading(
                dcc.Graph(id="workflow-product-impact-chart", style={'height': '400px'}),
                type="dot"
            ),
            html.Div(id="workflow-product-insights", className="mt-3")
        ])
    ], className="mb-4")