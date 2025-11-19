from dash import html, dcc
import dash_bootstrap_components as dbc

def get_classification_analysis_layout():
    return dbc.Card([
        # Hidden stores for state persistence
        dcc.Store(id="workflow-class-display-state", data="top5"),
        dcc.Store(id="workflow-class-view-state", data="stacked"),  # ADDED: View state store
        
        dbc.CardHeader([
            dbc.Row([
                dbc.Col([
                    html.H5("Tickets Classification", className="mb-0")
                ], width=6),
                dbc.Col([
                    dbc.ButtonGroup([
                        dbc.Button("Stacked", id="workflow-class-stacked-btn", size="sm", outline=True, active=True),
                        dbc.Button("Heatmap", id="workflow-class-heatmap-btn", size="sm", outline=True)
                    ], size="sm")
                ], width=6, className="text-end")
            ])
        ]),
        dbc.CardBody([
            # Control container with same styling as Resolution Times
            html.Div([
                dbc.Row([
                    dbc.Col([
                        html.Label("Display:", className="form-label mb-1", style={'fontSize': '13px', 'fontWeight': '500'}),
                        dcc.Dropdown(
                            id="workflow-class-display-selector",
                            options=[
                                {'label': 'Top 3', 'value': 'top3'},
                                {'label': 'Top 5', 'value': 'top5'},
                                {'label': 'Top 10', 'value': 'top10'},
                                {'label': 'All', 'value': 'all'}
                            ],
                            value='top5',  # Default to Top 5
                            clearable=False,
                            style={'fontSize': '12px'},
                            className="mb-3"
                        )
                    ], width=3),
                    dbc.Col([
                        # Space for future controls - matches Resolution Times pattern
                    ], width=9)
                ])
            ], style={'display': 'block', 'marginBottom': '15px'}),  # Same styling as Resolution Times container

            # Chart container
            html.Div([
                dcc.Loading(
                    dcc.Graph(id="workflow-classification-chart", style={'height': '450px'}),
                    type="dot"
                )
            ], id="workflow-classification-chart-wrapper", style={'cursor': 'pointer'}),
            
            # Insights container
            html.Div(id="workflow-classification-insights", className="mt-3")
        ])
    ], className="mb-4")