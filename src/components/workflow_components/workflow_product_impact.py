from dash import html, dcc
import dash_bootstrap_components as dbc

def get_product_impact_layout():
    return dbc.Card([
        dbc.CardHeader([
            dbc.Row([
                dbc.Col([
                    html.H5("Product/Feature Impact", className="mb-0")
                ], width=6),
                dbc.Col([
                    html.Label("Top Count:", className="form-label me-2", style={'margin-bottom': '0'}),
                    dcc.Dropdown(
                        id="workflow-product-count-dropdown",
                        options=[
                            {'label': '10', 'value': 10},
                            {'label': '15', 'value': 15},
                            {'label': '20', 'value': 20}
                        ],
                        value=15,
                        clearable=False,
                        style={'width': '80px', 'display': 'inline-block'}
                    )
                ], width=6, className="text-end")
            ])
        ]),
        dbc.CardBody([
            dcc.Loading(
                dcc.Graph(id="workflow-product-impact-chart", style={'height': '400px'}),
                type="default"
            ),
            html.Div(id="workflow-product-insights", className="mt-3")
        ])
    ], className="mb-4")