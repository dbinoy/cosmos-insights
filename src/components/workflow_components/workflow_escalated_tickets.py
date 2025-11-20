from dash import html, dcc
import dash_bootstrap_components as dbc

def get_escalated_tickets_layout():
    return dbc.Card([
        # Clean card header with analysis name
        dbc.CardHeader([
            html.H5("Escalated Tickets Overview", className="mb-0")
        ]),
        
        dbc.CardBody([
            # Controls section above the chart
            html.Div([
                dbc.Row([
                    dbc.Col([
                        html.Label("View Type:", className="form-label mb-1", style={'fontSize': '13px', 'fontWeight': '500'}),
                        dcc.Dropdown(
                            id="workflow-escalated-view-dropdown",
                            options=[
                                {'label': '📊 Escalated', 'value': 'current'},
                                {'label': '📈 Trends', 'value': 'trends'},
                                {'label': '👥 By Assignee', 'value': 'assignee'},
                                {'label': '⏱️ Duration', 'value': 'duration'}
                            ],
                            value='current',
                            clearable=False,
                            style={'fontSize': '12px'},
                            className="mb-3"
                        )
                    ], width=3),
                    dbc.Col([
                        html.Label("Period:", className="form-label mb-1", style={'fontSize': '13px', 'fontWeight': '500'}),
                        dcc.Dropdown(
                            id="workflow-escalated-period-dropdown",
                            options=[
                                {'label': 'Last 7', 'value': 7},
                                {'label': 'Last 30', 'value': 30},
                                {'label': 'Last 90', 'value': 90},
                                {'label': 'All Time', 'value': 'all'}
                            ],
                            value=30,
                            clearable=False,
                            style={'fontSize': '12px'},
                            className="mb-3"
                        )
                    ], width=2),
                    dbc.Col([
                        html.Label("Categories:", className="form-label mb-1", style={'fontSize': '13px', 'fontWeight': '500'}),
                        dcc.Dropdown(
                            id="workflow-escalated-categories-dropdown",
                            options=[
                                {'label': '🔴 Escalated', 'value': 'current_escalated'},
                                {'label': '✅ Resolved', 'value': 'recently_resolved'},
                                {'label': '⏰ Long Duration', 'value': 'long_duration'},
                                {'label': '📊 All Categories', 'value': 'all'}
                            ],
                            value=[],
                            multi=True,
                            clearable=False,
                            placeholder="Select categories to display",
                            style={'fontSize': '12px'},
                            className="mb-3"
                        )
                    ], width=3),
                    dbc.Col([
                        # Quick select buttons for common views
                        dbc.Col([
                            dbc.Row([
                                html.Label("Quick Select:", className="form-label mb-1", style={'fontSize': '13px', 'fontWeight': '500'})
                            ]),
                            dbc.Row([
                                dbc.ButtonGroup([
                                    dbc.Button("Active", id="btn-escalated-active", size="sm", outline=True, color="danger", style={'fontSize': '11px'}),
                                    dbc.Button("Critical", id="btn-escalated-critical", size="sm", outline=True, color="warning", style={'fontSize': '11px'}),
                                    dbc.Button("All", id="btn-escalated-all", size="sm", outline=True, color="primary", style={'fontSize': '11px'})
                                ], size="sm", className="mb-3")
                            ])
                        ])
                    ], width=4)
                ])
            ], style={'display': 'block', 'marginBottom': '15px'}),

            # Chart container
            html.Div([
                dcc.Loading(
                    dcc.Graph(
                        id="workflow-escalated-tickets-chart", 
                        style={'height': '450px', 'cursor': 'pointer'},
                        config={'displayModeBar': True}
                    ),
                    type="dot"
                )
            ], id="workflow-escalated-tickets-chart-wrapper", style={'cursor': 'pointer'}),
            
            # Insights container
            html.Div(id="workflow-escalated-insights", className="mt-3")
        ]),
        
        # Modal for enlarged view
        dbc.Modal([
            dbc.ModalHeader([
                dbc.ModalTitle("Escalated Tickets Overview - Detailed View"),
                dbc.Button("×", id="workflow-escalated-tickets-modal-close", className="btn-close", n_clicks=0, style={'border': 'none', 'background': 'none'})
            ]),
            dbc.ModalBody([
                dcc.Loading(
                    dcc.Graph(
                        id="workflow-escalated-tickets-modal-chart",
                        style={'height': '600px'},
                        config={'displayModeBar': True}
                    ),
                    type="default"
                )
            ])
        ],
        id="workflow-escalated-tickets-modal",
        size="xl",
        is_open=False)
    ], className="mb-4")