from dash import html, dcc
import dash_bootstrap_components as dbc

def get_recent_activities_layout():
    return html.Div([
        # Main recent activities card
        dbc.Card([
            dbc.CardHeader([
                dbc.Row([
                    dbc.Col([
                        html.H5("Recent Activities", className="mb-0"),
                    ], width=4),
                    dbc.Col([
                        # Timeframe dropdown
                        dcc.Dropdown(
                            id="compliance-recent-activities-timeframe-dropdown",
                            options=[
                                {"label": "Last 7 Days", "value": "7d"},
                                {"label": "Last 30 Days", "value": "30d"},
                                {"label": "Last 90 Days", "value": "90d"},
                                {"label": "Last 6 Months", "value": "6m"}
                            ],
                            value="30d",
                            clearable=False,
                            className="form-select-sm"
                        )
                    ], width=4),                    
                    dbc.Col([
                        # View selection dropdown (replacing buttons)
                        dcc.Dropdown(
                            id="compliance-activities-view-dropdown",
                            options=[
                                {"label": "Timeline View", "value": "timeline"},
                                {"label": "Activity Type", "value": "activity_type"},
                                {"label": "Daily Volume", "value": "volume"},
                                {"label": "Case Activity", "value": "case_activity"}
                            ],
                            value="timeline",
                            clearable=False,
                            className="form-select-sm"
                        )
                    ], width=4)
                ])
            ]),
            dbc.CardBody([
                # Store for chart view state
                dcc.Store(id="compliance-recent-activities-view-state", data="timeline"),
                
                # Details button row
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            dbc.Button([
                                html.I(className="fas fa-list me-2"),
                                "View Details"
                            ], 
                            id="compliance-activities-details-btn",
                            color="outline-primary", 
                            size="sm",
                            style={'whiteSpace': 'nowrap'})
                        ], className="d-flex justify-content-end mb-2")
                    ], width=12)
                ]),
                
                # Chart wrapper for modal functionality
                html.Div([
                    dcc.Loading(
                        dcc.Graph(id="compliance-recent-activities-chart"),
                        type="dot"
                    )
                ], id="compliance-recent-activities-chart-wrapper", 
                   style={"cursor": "pointer"}),
                
                html.Hr(),
                
                # Insights section
                html.Div(id="compliance-recent-activities-insights", className="insights-container")
            ])
        ], className="mb-4 h-100"),
        
        # Recent Activities Details Modal
        dbc.Modal([
            dbc.ModalHeader([
                dbc.ModalTitle([
                    html.I(className="fas fa-clock me-2"),
                    "Recent Activities Details"
                ], id="compliance-activities-details-modal-title")
            ]),
            dbc.ModalBody([
                html.Div(id="compliance-activities-details-content")
            ]),
            dbc.ModalFooter([
                dbc.Button(
                    "Close", 
                    id="compliance-activities-details-close-btn", 
                    className="ms-auto",
                    n_clicks=0
                )
            ])
        ],
        id="compliance-activities-details-modal",
        is_open=False,
        size="xl",
        backdrop=True,
        scrollable=True,
        centered=True)
    ])