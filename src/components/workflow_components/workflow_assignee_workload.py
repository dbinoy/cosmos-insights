from dash import html, dcc
import dash_bootstrap_components as dbc

def get_assignee_workload_layout():
    return dbc.Card([
        dbc.CardHeader([
            dbc.Row([
                dbc.Col([
                    html.H5("Workload by Assignee", className="mb-0")
                ], width=6),
                dbc.Col([
                    html.Label("Top Count:", className="form-label me-2", style={'margin-bottom': '0'}),
                    dcc.Dropdown(
                        id="workflow-assignee-count-dropdown",
                        options=[
                            {'label': '10', 'value': 10},
                            {'label': '15', 'value': 15},
                            {'label': '20', 'value': 20},
                            {'label': '25', 'value': 25}
                        ],
                        value=10,
                        clearable=False,
                        style={'width': '80px', 'display': 'inline-block'}
                    )
                ], width=6, className="text-end")
            ])
        ]),
        dbc.CardBody([
            dcc.Loading(
                dcc.Graph(
                    id="workflow-assignee-workload-chart", 
                    style={'height': '400px', 'cursor': 'pointer'},
                    config={'displayModeBar': True}
                ),
                type="dot"
            ),
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