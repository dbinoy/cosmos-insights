from dash import html, dcc
import dash_bootstrap_components as dbc

def get_product_impact_layout():
    return dbc.Card([
        dcc.Store(id="workflow-product-impact-chart-type", data="bar"),
        dbc.CardHeader([
            dbc.Row([
                dbc.Col([
                    html.H5("Product/Feature Impact", className="mb-0")
                ], width=6),
                dbc.Col([
                    # View type selector buttons - UPDATED: Make Box Plot active by default
                    dbc.ButtonGroup([
                        dbc.Button("Bar", id="product-impact-bar-btn", size="sm", outline=True, active=True),
                        dbc.Button("Stacked", id="product-impact-stacked-btn", size="sm", outline=True, active=False),
                        dbc.Button("Bubble", id="product-impact-bubble-btn", size="sm", outline=True, active=False),
                        dbc.Button("Treemap", id="product-impact-treemap-btn", size="sm", outline=True, active=False)
                    ], size="sm")
                ], width=6, className="text-end")
            ])
        ]),        
        dbc.CardBody([
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
                                {'label': 'Top 50', 'value': 50},
                                {'label': 'All', 'value': 'all'}
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