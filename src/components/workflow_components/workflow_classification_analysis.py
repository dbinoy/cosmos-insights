from dash import html, dcc
import dash_bootstrap_components as dbc

def get_classification_analysis_layout():
    return dbc.Card([
        dcc.Store(id="workflow-class-display-state", data="top5"),
        dcc.Store(id="workflow-class-view-state", data="stacked"),
        dcc.Store(id="workflow-class-dimension-store", data={'row': 'case_type', 'column': 'case_origin'}),  
        
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
            html.Div([
                dbc.Row([
                    dbc.Col([
                        html.Label("Rows (Y-axis):", className="form-label mb-1", style={'fontSize': '13px', 'fontWeight': '500'}),
                        dcc.Dropdown(
                            id="workflow-class-row-dimension",
                            options=[
                                {'label': 'Case Type', 'value': 'case_type'},
                                {'label': 'Case Origin', 'value': 'case_origin'},
                                {'label': 'AOR', 'value': 'aor'},                         
                                {'label': 'Case Reason', 'value': 'case_reason'},          
                                {'label': 'Priority', 'value': 'priority'},
                                {'label': 'Product', 'value': 'product'},
                                {'label': 'Module', 'value': 'module'},
                                {'label': 'Feature', 'value': 'feature'},
                                {'label': 'Issue', 'value': 'issue'},
                                {'label': 'Status', 'value': 'status'}
                            ],
                            value='case_type',  # Default to Case Type
                            clearable=False,
                            style={'fontSize': '12px'},
                            className="mb-3"
                        )
                    ], width=3),
                    dbc.Col([
                        html.Label("Columns (X-axis):", className="form-label mb-1", style={'fontSize': '13px', 'fontWeight': '500'}),
                        dcc.Dropdown(
                            id="workflow-class-column-dimension",
                            options=[
                                {'label': 'Case Origin', 'value': 'case_origin'},
                                {'label': 'Case Type', 'value': 'case_type'},
                                {'label': 'AOR', 'value': 'aor'},                          
                                {'label': 'Case Reason', 'value': 'case_reason'},          
                                {'label': 'Priority', 'value': 'priority'},
                                {'label': 'Product', 'value': 'product'},
                                {'label': 'Module', 'value': 'module'},
                                {'label': 'Feature', 'value': 'feature'},
                                {'label': 'Issue', 'value': 'issue'},
                                {'label': 'Status', 'value': 'status'}
                            ],
                            value='case_origin',  # Default to Case Origin
                            clearable=False,
                            style={'fontSize': '12px'},
                            className="mb-3"
                        )
                    ], width=3),
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
                            value='top5',  
                            clearable=False,
                            style={'fontSize': '12px'},
                            className="mb-3"
                        )
                    ], width=3),
                    dbc.Col([
                        # Space for future controls
                    ], width=3)
                ])
            ], style={'display': 'block', 'marginBottom': '15px'}),

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