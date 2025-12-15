from dash import html, dcc
import dash_bootstrap_components as dbc

def get_violation_status_layout():
    return html.Div([
        # Main violation analysis card
        dbc.Card([
            dbc.CardHeader([
                dbc.Row([
                    dbc.Col([
                        html.H5("Case Status", className="mb-0")
                    ], width=3),
                    dbc.Col([
                            dbc.ButtonGroup([
                                dbc.Button("Disposition", id="violation-disposition-view-btn", size="sm", outline=True, active=True),
                                dbc.Button("Violation", id="violation-types-view-btn", size="sm", outline=True),
                                dbc.Button("Category", id="violation-categories-view-btn", size="sm", outline=True),
                                dbc.Button("Rule", id="violation-rules-view-btn", size="sm", outline=True),
                                dbc.Button("Fees", id="violation-fees-view-btn", size="sm", outline=True),
                                dbc.Button("Reports", id="violation-reports-view-btn", size="sm", outline=True)
                            ], size="sm")
                    ], width=9, className="px-0", style={"textAlign": "right"})
                ])
            ]),
            dbc.CardBody([
                # Store for chart view state
                dcc.Store(id="compliance-violation-status-view-state", data="disposition"),
                
                # Details button row
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            dbc.Button([
                                html.I(className="fas fa-table me-2"),
                                "View Details"
                            ], 
                            id="compliance-violation-details-btn",
                            color="outline-primary", 
                            size="sm",
                            style={'whiteSpace': 'nowrap'})
                        ], className="d-flex justify-content-end mb-2")
                    ], width=12)
                ]),
                
                # Chart wrapper for modal functionality
                html.Div([
                    dcc.Loading(
                        dcc.Graph(id="compliance-violation-status-chart"),
                        type="dot"
                    )
                ], id="compliance-violation-status-chart-wrapper", 
                   style={"cursor": "pointer"}),
                
                html.Hr(),
                
                # Insights section
                html.Div(id="compliance-violation-status-insights", className="insights-container")
            ])
        ], className="mb-4 h-100"),
        
        # Violation Details Modal
        dbc.Modal([
            dbc.ModalHeader([
                dbc.ModalTitle([
                    html.I(className="fas fa-gavel me-2"),
                    "Violation Analysis Details"
                ], id="compliance-violation-details-modal-title")
            ]),
            dbc.ModalBody([
                html.Div(id="compliance-violation-details-content")
            ]),
            dbc.ModalFooter([
                dbc.Button(
                    "Close", 
                    id="compliance-violation-details-close-btn", 
                    className="ms-auto",
                    n_clicks=0
                )
            ])
        ],
        id="compliance-violation-details-modal",
        is_open=False,
        size="xl",
        backdrop=True,
        scrollable=True,
        centered=True)
    ])