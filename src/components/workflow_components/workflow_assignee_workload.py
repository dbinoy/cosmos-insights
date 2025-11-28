from dash import html, dcc
import dash_bootstrap_components as dbc

def get_assignee_workload_layout():
    return dbc.Card([
        # Clean card header with only the analysis name
        dbc.CardHeader([
            html.H5("Workload by Assignee", className="mb-0")
        ]),
        
        dbc.CardBody([
            # Controls section above the chart (consistent with Classification layout)
            html.Div([
                dbc.Row([
                    dbc.Col([
                        html.Label("Display:", className="form-label mb-1", style={'fontSize': '13px', 'fontWeight': '500'}),
                        dcc.Dropdown(
                            id="workflow-assignee-count-dropdown",
                            options=[
                                {'label': 'Top 10', 'value': 10},
                                {'label': 'Top 15', 'value': 15},
                                {'label': 'Top 20', 'value': 20},
                                {'label': 'Top 25', 'value': 25},
                                {'label': 'All', 'value': 'all'}
                            ],
                            value=10,
                            clearable=False,
                            style={'fontSize': '12px'},
                            className="mb-3"
                        )
                    ], width=3),
                    dbc.Col([
                        html.Label("Show Categories:", className="form-label mb-1", style={'fontSize': '13px', 'fontWeight': '500'}),
                        dcc.Dropdown(
                            id="workflow-assignee-categories-dropdown",
                            options=[
                                {'label': '✅ Closed', 'value': 'Closed'},
                                {'label': '🔄 Active', 'value': 'Active'},
                                {'label': '⏸️ Non-Actionable', 'value': 'Non-Actionable'},
                                {'label': '📊 Total Line', 'value': 'Total'}
                            ],
                            value=[],  
                            multi=True,
                            clearable=False,
                            placeholder="Select categories to display",
                            style={'fontSize': '12px'},
                            className="mb-3"
                        )
                    ], width=4),
                    dbc.Col([
                        # Quick select buttons for common combinations
                        dbc.Col([
                            dbc.Row([
                                html.Label("Quick Select:", className="form-label mb-1", style={'fontSize': '13px', 'fontWeight': '500'})
                            ]),
                            dbc.Row([
                                dbc.ButtonGroup([
                                    dbc.Button("All", id="btn-cat-all", size="sm", outline=True, color="primary", style={'fontSize': '11px'}),
                                    dbc.Button("Closed", id="btn-cat-closed", size="sm", outline=True, color="warning", style={'fontSize': '11px'}),
                                    dbc.Button("Open", id="btn-cat-open", size="sm", outline=True, color="info", style={'fontSize': '11px'})
                                ], size="lg", className="mb-3")
                            ])
                        ])
                    ], width=5)
                ])
            ], style={'display': 'block', 'marginBottom': '15px'}),
            html.Div(
                id="workflow-source-assignee-workload-chart-container",
                children=[
                    html.Div([
                        dcc.Loading(
                            dcc.Graph(id="workflow-assignee-workload-chart", style={'height': '450px'}),
                            type="dot"
                        )
                    ], id="workflow-assignee-workload-chart-wrapper", style={'cursor': 'pointer'})
                ]
            ),               
            
            # Insights container
            html.Div(id="workflow-assignee-insights", className="mt-3")
        ]),
        
        # Modal for enlarged view
        dbc.Modal([
            dbc.ModalHeader([
                dbc.ModalTitle("Workload by Assignee - Detailed View"),
                dbc.Button("×", id="workflow-assignee-workload-modal-close", className="btn-close", n_clicks=0, style={'border': 'none', 'background': 'none'})
            ]),
            dbc.ModalBody([
                dcc.Loading(
                    dcc.Graph(
                        id="workflow-assignee-workload-modal-chart",
                        style={'height': '600px'},
                        config={'displayModeBar': True}
                    ),
                    type="default"
                )
            ])
        ],
        id="workflow-assignee-workload-modal",
        size="xl",
        is_open=False)
    ], className="mb-4")