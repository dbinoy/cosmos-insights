from dash import html, dcc
import dash_bootstrap_components as dbc

def get_outstanding_issues_layout():
    return html.Div([
        # Main outstanding issues card
        dbc.Card([
            dbc.CardHeader([
                dbc.Row([
                    dbc.Col([
                        html.H5("Outstanding Cases", className="mb-0"),
                    ], width=5),
                    dbc.Col([
                        # View selection buttons
                        dbc.ButtonGroup([
                            dbc.Button("Severity", id="outstanding-severity-view-btn", size="sm", outline=True, active=True),
                            dbc.Button("Age", id="outstanding-age-view-btn", size="sm", outline=True),
                            dbc.Button("Assignment", id="outstanding-assignment-view-btn", size="sm", outline=True),
                            dbc.Button("Violation Type", id="outstanding-violation-view-btn", size="sm", outline=True)
                        ], size="sm")
                    ], width=7, className="px-0", style={"textAlign": "right"})
                ])
            ]),
            dbc.CardBody([
                # Store for chart view state
                dcc.Store(id="compliance-outstanding-issues-view-state", data="severity"),
                
                # Details button row
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            dbc.Button([
                                html.I(className="fas fa-list me-2"),
                                "View Details"
                            ], 
                            id="compliance-outstanding-details-btn",
                            color="outline-primary", 
                            size="sm",
                            style={'whiteSpace': 'nowrap'})
                        ], className="d-flex justify-content-end mb-2")
                    ], width=12)
                ]),
                
                # Chart wrapper for modal functionality
                html.Div([
                    dcc.Loading(
                        dcc.Graph(id="compliance-outstanding-issues-chart"),
                        type="dot"
                    )
                ], id="compliance-outstanding-issues-chart-wrapper", 
                   style={"cursor": "pointer"}),
                
                html.Hr(),
                
                # Insights section
                html.Div(id="compliance-outstanding-issues-insights", className="insights-container")
            ])
        ], className="mb-4 h-100"),
        
        # Outstanding Issues Details Modal
        dbc.Modal([
            dbc.ModalHeader([
                dbc.ModalTitle([
                    html.I(className="fas fa-exclamation-triangle me-2"),
                    "Outstanding Issues Details"
                ], id="compliance-outstanding-details-modal-title")
            ]),
            dbc.ModalBody([
                html.Div(id="compliance-outstanding-details-content")
            ]),
            dbc.ModalFooter([
                dbc.Button(
                    "Close", 
                    id="compliance-outstanding-details-close-btn", 
                    className="ms-auto",
                    n_clicks=0
                )
            ])
        ],
        id="compliance-outstanding-details-modal",
        is_open=False,
        size="xl",
        backdrop=True,
        scrollable=True,
        centered=True)
    ])