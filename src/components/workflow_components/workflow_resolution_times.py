from dash import html, dcc
import dash_bootstrap_components as dbc

def get_resolution_times_layout():
    return dbc.Card([
        # Hidden store for view state persistence
        dcc.Store(id="workflow-resolution-view-state", data="bar"),
        
        dbc.CardHeader([
            dbc.Row([
                dbc.Col([
                    html.H5("Resolution Times Analysis", className="mb-0")
                ], width=5),
                dbc.Col([
                    # View type selector buttons - moved to take more space
                    dbc.ButtonGroup([
                        dbc.Button("Bar Chart", id="workflow-resolution-bar-btn", size="sm", outline=True, active=True),
                        dbc.Button("Box Plot", id="workflow-resolution-box-btn", size="sm", outline=True),
                        dbc.Button("Statistics", id="workflow-resolution-stats-btn", size="sm", outline=True),
                        dbc.Button("Distribution", id="workflow-resolution-dist-btn", size="sm", outline=True)
                    ], size="sm")
                ], width=7, className="text-end")
            ])
        ]),
        dbc.CardBody([
            # Conditional dimension selector - only shown for Bar Chart and Box Plot
            html.Div(
                id="workflow-resolution-dimension-container",
                children=[
                    dbc.Row([
                        dbc.Col([
                            html.Label("Analyze by:", className="form-label mb-1", style={'fontSize': '13px', 'fontWeight': '500'}),
                            dcc.Dropdown(
                                id="workflow-resolution-dimension-selector",
                                options=[
                                    {'label': 'Work Item Type', 'value': 'WorkItemDefinitionShortCode'},
                                    {'label': 'Priority', 'value': 'Priority'},
                                    {'label': 'Product', 'value': 'Product'},
                                    {'label': 'Module', 'value': 'Module'},
                                    {'label': 'Feature', 'value': 'Feature'},
                                    {'label': 'Issue', 'value': 'Issue'},
                                    {'label': 'Case Origin', 'value': 'CaseOrigin'},
                                    {'label': 'AOR', 'value': 'AorShortName'}
                                ],
                                value='WorkItemDefinitionShortCode',
                                placeholder="Select dimension...",
                                style={'fontSize': '12px'},
                                className="mb-3"
                            )
                        ], width=4),
                        dbc.Col([
                            # Space for future controls or info
                        ], width=8)
                    ])
                ],
                style={'display': 'block'}  # Will be controlled by callback
            ),
            
            # Chart container - will be conditionally hidden for statistics
            html.Div(
                id="workflow-resolution-chart-container",
                children=[
                    dcc.Loading(
                        dcc.Graph(id="workflow-resolution-times-chart", style={'height': '450px'}),
                        type="dot"
                    )
                ]
            ),
            # Insights container
            html.Div(id="workflow-resolution-insights", className="mt-3")
        ])
    ], className="mb-4")