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
                                {'label': 'All', 'value': 'all'}  # ADDED: All option
                            ],
                            value=10,
                            clearable=False,
                            style={'fontSize': '12px'},
                            className="mb-3"
                        )
                    ], width=3),
                    dbc.Col([
                        # Space for future controls (consistent with Classification layout)
                    ], width=9)
                ])
            ], style={'display': 'block', 'marginBottom': '15px'}),

            # Chart container
            html.Div([
                dcc.Loading(
                    dcc.Graph(
                        id="workflow-assignee-workload-chart", 
                        style={'height': '450px', 'cursor': 'pointer'},  # Consistent height with Classification
                        config={'displayModeBar': True}
                    ),
                    type="dot"
                )
            ], id="workflow-assignee-workload-chart-wrapper", style={'cursor': 'pointer'}),
            
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