from dash import html, dcc
import dash_bootstrap_components as dbc

def get_user_performance_layout():
    return dbc.Card([
        dbc.CardHeader([
            dbc.Row([
                dbc.Col([
                    html.H5("User Activity & Performance", className="mb-0")
                ], width=8),
                dbc.Col([
                    dcc.Dropdown(
                        id="workflow-performance-metric-dropdown",
                        options=[
                            {'label': 'Tickets Handled', 'value': 'tickets_handled'},
                            {'label': 'Avg Resolution Time', 'value': 'avg_resolution'},
                            {'label': 'Escalation Rate', 'value': 'escalation_rate'}
                        ],
                        value='tickets_handled',
                        clearable=False
                    )
                ], width=4)
            ])
        ]),
        dbc.CardBody([
            dcc.Loading(
                dcc.Graph(id="workflow-user-performance-chart", style={'height': '400px'}),
                type="default"
            ),
            html.Div(id="workflow-performance-insights", className="mt-3")
        ])
    ], className="mb-4")