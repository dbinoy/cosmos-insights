from dash import html, dcc
import dash_bootstrap_components as dbc

def get_assignee_workload_layout():
    return dbc.Card([
        dbc.CardHeader([
            dbc.Row([
                dbc.Col([
                    html.H5("Workload by Assignee/Team", className="mb-0")
                ], width=6),
                dbc.Col([
                    html.Label("Top Count:", className="form-label me-2", style={'margin-bottom': '0'}),
                    dcc.Dropdown(
                        id="workflow-assignee-count-dropdown",
                        options=[
                            {'label': '10', 'value': 10},
                            {'label': '15', 'value': 15},
                            {'label': '20', 'value': 20}
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
                dcc.Graph(id="workflow-assignee-workload-chart", style={'height': '400px'}),
                type="default"
            ),
            html.Div(id="workflow-assignee-insights", className="mt-3")
        ])
    ], className="mb-4")