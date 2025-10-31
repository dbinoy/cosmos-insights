from dash import html, dcc, dash_table

import dash_bootstrap_components as dbc

def get_data_table_layout():
    """Create comprehensive training data table with download capability"""
    
    component = dbc.Card([
        dbc.CardHeader([
            html.Div([
                html.H5("Training Activity Details", className="mb-0 flex-grow-1"),
                dbc.ButtonGroup([
                    dbc.Button("Export CSV", id="export-csv-btn", color="primary", outline=True, size="sm"),
                    dbc.Button("Export Excel", id="export-excel-btn", color="success", outline=True, size="sm")
                ])
            ], className="d-flex justify-content-between align-items-center")
        ]),
        dbc.CardBody([
            # Table controls
            dbc.Row([
                dbc.Col([
                    html.Label("Report Type:", className="form-label"),
                    dcc.Dropdown(
                        id="data-table-report-type-dropdown",
                        options=[
                            {"label": "Member Activity Summary", "value": "member_summary"},
                            {"label": "Class Attendance Details", "value": "class_details"},
                            {"label": "Instructor Performance", "value": "instructor_details"},
                            {"label": "Office Participation", "value": "office_summary"},
                            {"label": "Recent Activity Log", "value": "recent_activity"}
                        ],
                        value="member_summary",
                        className="mb-3"
                    )
                ], width=4),
                dbc.Col([
                    html.Label("Records per page:", className="form-label"),
                    dcc.Dropdown(
                        id="table-page-size-dropdown",
                        options=[
                            {"label": "10", "value": 10},
                            {"label": "25", "value": 25},
                            {"label": "50", "value": 50},
                            {"label": "100", "value": 100}
                        ],
                        value=25,
                        className="mb-3"
                    )
                ], width=4),
                dbc.Col([
                    dbc.Input(
                        id="table-search-input",
                        placeholder="Search records...",
                        type="text",
                        className="mb-3"
                    )
                ], width=4)
            ]),
            
            # Data table
            html.Div(id="training-data-table-container"),
            
            # Download components (hidden)
            dcc.Download(id="download-csv"),
            dcc.Download(id="download-excel")
        ])
    ], className="mb-4 shadow-sm border-0")
    
    return component