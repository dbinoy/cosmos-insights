from dash import html, dcc
import dash_bootstrap_components as dbc

def get_status_distribution_layout():
    return html.Div([
        # Main status distribution card
        dbc.Card([
            dbc.CardHeader([
                html.H5("Ticket Status Distribution", className="mb-0")
            ]),
            dbc.CardBody([
                # Button row above chart - right aligned
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            dbc.Button([
                                html.I(className="fas fa-table me-2"),
                                "View Details"
                            ], 
                            id="workflow-status-details-btn",
                            color="outline-primary", 
                            size="sm",
                            style={'whiteSpace': 'nowrap'})
                        ], className="d-flex justify-content-end mb-2")  # Reduced from mb-3 to mb-2
                    ], width=12)
                ]),
                
                # Chart wrapper for modal functionality - with tighter spacing
                html.Div([
                    dcc.Loading(
                        dcc.Graph(id="workflow-status-distribution-chart", style={'height': '380px'}),
                        type="dot"
                    )
                ], id="workflow-status-chart-wrapper", 
                   style={'cursor': 'pointer', 'marginBottom': '10px'}),  # Added small margin bottom
                
                # Insights section with tighter spacing
                html.Div(id="workflow-status-insights", 
                        className="mt-1",  # Changed from mt-3 to mt-1
                        style={'paddingTop': '5px'})  # Added minimal padding
            ], className="p-3")  # Reduced card body padding
        ], className="mb-4"),
        
        # Status Details Modal
        dbc.Modal([
            dbc.ModalHeader([
                dbc.ModalTitle([
                    html.I(className="fas fa-table me-2"),
                    "Status Distribution Details"
                ], id="workflow-status-details-modal-title")
            ]),
            dbc.ModalBody([
                html.Div(id="workflow-status-details-content")
            ]),
            dbc.ModalFooter([
                dbc.Button(
                    "Close", 
                    id="workflow-status-details-close-btn", 
                    className="ms-auto",
                    n_clicks=0
                )
            ])
        ],
        id="workflow-status-details-modal",
        is_open=False,
        size="xl",  # Extra large modal for the table
        backdrop=True,
        scrollable=True,
        centered=True)
    ])