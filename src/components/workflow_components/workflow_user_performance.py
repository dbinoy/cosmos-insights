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
                            {'label': 'Notes/Tasks', 'value': 'notes_tasks'},
                            {'label': 'Top Performers', 'value': 'top_performers'}
                        ],
                        value='tickets_handled',
                        clearable=False,
                        style={'fontSize': '12px'},
                        className="mb-3"
                    )
                ], width=4),
                dbc.Col([], width=8)  # Space for future controls/info
            ]),
            dcc.Loading(
                dcc.Graph(id="workflow-user-performance-chart", style={'height': '400px'}),
                type="dot"
            ),
            html.Div(id="workflow-performance-insights", className="mt-3")
        ])
    ], className="mb-4")