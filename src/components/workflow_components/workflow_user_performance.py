from dash import html, dcc
import dash_bootstrap_components as dbc

def get_user_performance_layout():
    return dbc.Card([
        dcc.Store(id="workflow-user-performance-chart-type", data="tickets_handled"),
        dbc.CardHeader([
            html.H5("User Activity & Performance", className="mb-0")
        ]),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("View:", className="form-label mb-1", style={'fontSize': '13px', 'fontWeight': '500'}),
                    dcc.Dropdown(
                        id="workflow-user-performance-view-dropdown",
                        options=[
                            {'label': 'Tickets Handled', 'value': 'tickets_handled'},
                            {'label': 'Resolution Time', 'value': 'avg_resolution'},
                            {'label': 'First Action Time', 'value': 'first_action'},
                            {'label': 'Actions/Tasks', 'value': 'actions_tasks'},
                            {'label': 'Top Performers', 'value': 'top_performers'}                        
                        ],
                        value='tickets_handled',
                        clearable=False,
                        style={'fontSize': '12px'},
                        className="mb-3"
                    )
                ], width=4),
                dbc.Col([
                    html.Label("Display Top:", className="form-label mb-1", style={'fontSize': '13px', 'fontWeight': '500'}),
                    dcc.Dropdown(
                        id="workflow-user-performance-count-top-dropdown",
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
                ], width=4),
                dbc.Col([
                    html.Label("Display Bottom:", className="form-label mb-1", style={'fontSize': '13px', 'fontWeight': '500'}),
                    dcc.Dropdown(
                        id="workflow-user-performance-count-bottom-dropdown",
                        options=[
                            {'label': 'Bottom 5', 'value': 5},
                            {'label': 'Bottom 10', 'value': 10},
                            {'label': 'Bottom 15', 'value': 15},
                            {'label': 'Bottom 20', 'value': 20},
                            {'label': 'Bottom 25', 'value': 25},
                            {'label': 'Bottom 50', 'value': 50},
                            {'label': 'All', 'value': 'all'}
                        ],
                        value='all',
                        clearable=False,
                        style={'fontSize': '12px'},
                        className="mb-3"
                    )
                ], width=4)
            ]),
            html.Div(
                id="workflow-user-performance-chart-container",
                children=[
                    html.Div([
                        dcc.Loading(
                            dcc.Graph(id="workflow-user-performance-chart", style={'height': '450px'}),
                            type="dot"
                        )
                    ], id="workflow-user-performance-chart-wrapper", style={'cursor': 'pointer'})
                ]
            ),            
            html.Div(id="workflow-performance-insights", className="mt-3")
        ])
    ], className="mb-4")