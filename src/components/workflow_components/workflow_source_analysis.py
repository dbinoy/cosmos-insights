from dash import html, dcc
import dash_bootstrap_components as dbc

def get_source_analysis_layout():
    return html.Div([
        dbc.Card([
            dbc.CardHeader([
                html.H5("Ticket Source/Origin Analysis", className="mb-0")
            ]),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            dbc.Button([
                                html.I(className="fas fa-table me-2"),
                                "View Details"
                            ], 
                            id="workflow-source-details-btn",
                            color="outline-primary", 
                            size="sm",
                            style={'whiteSpace': 'nowrap'})
                        ], className="d-flex justify-content-end mb-2")
                    ], width=12)
                ]),
                html.Div(
                    id="workflow-source-analysis-chart-container",
                    children=[
                        html.Div([
                            dcc.Loading(
                                dcc.Graph(id="workflow-source-analysis-chart", style={'height': '450px'}),
                                type="dot"
                            )
                        ], id="workflow-source-analysis-chart-wrapper", style={'cursor': 'pointer'})
                    ]
                ),                  
                html.Div(id="workflow-source-insights", className="mt-3")
            ])
        ], className="mb-4"),
        dbc.Modal([
            dbc.ModalHeader([
                dbc.ModalTitle([
                    html.I(className="fas fa-table me-2"),
                    "Source/Origin Details"
                ], id="workflow-source-details-modal-title")
            ]),
            dbc.ModalBody([
                html.Div(id="workflow-source-details-content")
            ]),
            dbc.ModalFooter([
                dbc.Button(
                    "Close", 
                    id="workflow-source-details-close-btn", 
                    className="ms-auto",
                    n_clicks=0
                )
            ])
        ],
        id="workflow-source-details-modal",
        is_open=False,
        size="xl",
        backdrop=True,
        scrollable=True,
        centered=True)
    ])