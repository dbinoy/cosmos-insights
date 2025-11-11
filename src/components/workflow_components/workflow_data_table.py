from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc

def get_data_table_layout():
    """Create comprehensive workflow data table with download capability"""
    
    return dbc.Card([
        dbc.CardHeader([
            dbc.Row([
                dbc.Col([
                    html.H5("Workflow Activity Details", className="mb-0")
                ], width=2), 
                dbc.Col([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Report Type:", className="form-label mb-0 text-end", 
                                     style={'lineHeight': '2.25rem'})  
                        ], width=3, className="text-end"),  
                        dbc.Col([
                            dcc.Dropdown(
                                id="workflow-data-table-report-type-dropdown",
                                options=[
                                    {"label": "Ticket Summary", "value": "ticket_summary"},
                                    {"label": "Resolution Details", "value": "resolution_details"},
                                    {"label": "User Performance", "value": "user_performance"},
                                    {"label": "Escalation History", "value": "escalation_history"},
                                    {"label": "Product Impact", "value": "product_impact"}
                                ],
                                value="ticket_summary",
                                placeholder="Select Report Type",
                                className="mb-0"
                            )
                        ], width=9, className="text-start")  
                    ], className="g-1 align-items-center") 
                ], width=4),
                dbc.Col([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Records per page:", className="form-label mb-0 text-end",
                                     style={'lineHeight': '2.25rem'})  
                        ], width=7, className="text-end"),  
                        dbc.Col([
                            dcc.Dropdown(
                                id="workflow-table-page-size-dropdown",
                                options=[
                                    {"label": "10 records", "value": 10},
                                    {"label": "25 records", "value": 25},
                                    {"label": "50 records", "value": 50},
                                    {"label": "100 records", "value": 100}
                                ],
                                value=25,
                                placeholder="Records per page",
                                className="mb-0"
                            )
                        ], width=5, className="text-start")  
                    ], className="g-1 align-items-center") 
                ], width=3),  
                dbc.Col([
                    dbc.ButtonGroup([
                        dbc.Button("Export CSV", id="workflow-export-csv-btn", color="primary", outline=True, size="sm"),
                        dbc.Button("Export Excel", id="workflow-export-excel-btn", color="success", outline=True, size="sm"),
                        dbc.Button("Export PDF", id="workflow-export-pdf-btn", color="danger", outline=True, size="sm")
                    ], className="float-end")
                ], width=3) 
            ], className="align-items-center")
        ]),
        dbc.CardBody([
            html.Div([
                dcc.Loading(
                    id="loading-workflow-data-table",
                    type="default", 
                    children=[
                        html.Div(id="workflow-data-table-container")
                    ]
                )
            ], 
            id="workflow-data-table-chart-wrapper", 
            style={
                'cursor': 'pointer',
                'border': '1px solid #dee2e6', 
                'borderRadius': '4px',
                'padding': '15px',  
                'transition': 'border-color 0.2s, box-shadow 0.2s', 
                'backgroundColor': 'white' 
            },
            className="chart-clickable-area"  
            ),
            
            dcc.Download(id="workflow-download-csv"),
            dcc.Download(id="workflow-download-excel"),
            dcc.Download(id="workflow-download-pdf") 
        ])
    ], className="mb-4")