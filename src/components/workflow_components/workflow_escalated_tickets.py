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
                        html.Label("View:", className="form-label mb-1", style={'fontSize': '13px', 'fontWeight': '500'}),
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
                            value=['current_escalated'],
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
                                ], size="lg", className="mb-3")
                            ])
                        ])
                    ], width=4)
                ])
            ], style={'display': 'block', 'marginBottom': '15px'}),

            # Button row above chart - right aligned
            dbc.Row([
                dbc.Col([
                    html.Div([
                        dbc.Button([
                            html.I(className="fas fa-table me-2"),
                            "View Details"
                        ], 
                        id="workflow-escalated-details-btn",
                        color="outline-primary", 
                        size="sm",
                        style={'whiteSpace': 'nowrap'})
                    ], className="d-flex justify-content-end mb-2")
                ], width=12)
            ]),

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
        
        # Modal for details table
        dbc.Modal([
            dbc.ModalHeader([
                dbc.ModalTitle([
                    html.I(className="fas fa-table me-2"),
                    "Escalated Tickets Details"
                ], id="workflow-escalated-details-modal-title")
            ]),
            dbc.ModalBody([
                html.Div(id="workflow-escalated-details-content")
            ]),
            dbc.ModalFooter([
                dbc.Button(
                    "Close", 
                    id="workflow-escalated-details-close-btn", 
                    className="ms-auto",
                    n_clicks=0
                )
            ])
        ],
        id="workflow-escalated-details-modal",
        is_open=False,
        size="xl",
        backdrop=True,
        scrollable=True,
        centered=True)
    ], className="mb-4")