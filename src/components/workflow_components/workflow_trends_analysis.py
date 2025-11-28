from dash import html, dcc
import dash_bootstrap_components as dbc

def get_trends_case_reasons_issues_layout():
    return dbc.Card([
        dbc.CardHeader([
            html.H5("Trends in Case Reasons & Issues", className="mb-0")
        ]),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("View:", className="form-label mb-1", style={'fontSize': '13px', 'fontWeight': '500'}),
                    dcc.Dropdown(
                        id="workflow-trends-case-view-dropdown",
                        options=[
                            {'label': 'Case Reasons', 'value': 'case_reason'},
                            {'label': 'Issues', 'value': 'issue'}
                        ],
                        value='case_reason',
                        clearable=False,
                        style={'fontSize': '12px'},
                        className="mb-3"
                    )
                ], width=3),
                dbc.Col([
                    html.Label("Time Granularity:", className="form-label mb-1", style={'fontSize': '13px', 'fontWeight': '500'}),
                    dcc.Dropdown(
                        id="workflow-trends-case-time-dropdown",
                        options=[
                            {'label': 'Weekly', 'value': 'week'},
                            {'label': 'Monthly', 'value': 'month'},
                            {'label': 'Quarterly', 'value': 'quarter'},
                            {'label': 'Yearly', 'value': 'year'}                            
                        ],
                        value='month',
                        clearable=False,
                        style={'fontSize': '12px'},
                        className="mb-3"
                    )
                ], width=3),
                dbc.Col([
                    html.Label("Display Top:", className="form-label mb-1", style={'fontSize': '13px', 'fontWeight': '500'}),
                    dcc.Dropdown(
                        id="workflow-trends-case-count-top-dropdown",
                        options=[
                            {'label': 'Top 5', 'value': 5},
                            {'label': 'Top 10', 'value': 10},
                            {'label': 'Top 15', 'value': 15},
                            {'label': 'Top 20', 'value': 20},
                            {'label': 'Top 25', 'value': 25},
                            {'label': 'Top 30', 'value': 30},
                            {'label': 'Top 35', 'value': 35},
                            {'label': 'All', 'value': 'all'}
                        ],
                        value=5,
                        clearable=False,
                        style={'fontSize': '12px'},
                        className="mb-3"
                    )
                ], width=3),
                dbc.Col([
                    html.Label("Display Bottom:", className="form-label mb-1", style={'fontSize': '13px', 'fontWeight': '500'}),
                    dcc.Dropdown(
                        id="workflow-trends-case-count-bottom-dropdown",
                        options=[
                            {'label': 'Bottom 5', 'value': 5},
                            {'label': 'Bottom 10', 'value': 10},
                            {'label': 'Bottom 15', 'value': 15},
                            {'label': 'Bottom 20', 'value': 20},
                            {'label': 'Bottom 25', 'value': 25},
                            {'label': 'Bottom 30', 'value': 30},
                            {'label': 'Bottom 35', 'value': 35},
                            {'label': 'All', 'value': 'all'}
                        ],
                        value='all',
                        clearable=False,
                        style={'fontSize': '12px'},
                        className="mb-3"
                    )
                ], width=3)
            ]),
            html.Div(
                id="workflow-trends-case-reasons-issues-chart-container",
                children=[
                    html.Div([
                        dcc.Loading(
                            dcc.Graph(id="workflow-trends-case-reasons-issues-chart", style={'height': '450px'}),
                            type="dot"
                        )
                    ], id="workflow-trends-case-reasons-issues-chart-wrapper", style={'cursor': 'pointer'})
                ]
            ),               
            html.Div(id="workflow-trends-case-reasons-issues-insights", className="mt-3")
        ])
    ], className="mb-4")