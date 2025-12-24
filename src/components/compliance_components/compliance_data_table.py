from dash import html, dcc
import dash_bootstrap_components as dbc

def get_data_table_layout():
    return dbc.Card([
        dbc.CardHeader([
            dbc.Row([
                dbc.Col([
                    html.H5("Compliance Activity", className="mb-0"),
                ], width=3),

                dbc.Col([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Report:", className="form-label mb-0 text-end", 
                                     style={'lineHeight': '2.25rem'})  
                        ], width=4, className="text-end"),  
                        dbc.Col([
                            dcc.Dropdown(
                                id="compliance-data-table-report-type-dropdown",
                                options=[
                                    {"label": "Case Summary", "value": "case_summary"},
                                    {"label": "Violation Details", "value": "violation_details"},
                                    {"label": "Member Violations", "value": "member_violations"},
                                    {"label": "Office Violations", "value": "office_violations"},
                                    {"label": "Rule Violations", "value": "rule_violations"},
                                    {"label": "Financial Summary", "value": "financial_summary"},
                                    {"label": "Activity Log", "value": "activity_log"}
                                ],
                                value="case_summary",
                                clearable=False,
                                className="form-select-sm"
                            )
                        ], width=8, className="text-start")  
                    ], className="g-1 align-items-center") 
                ], width=3),

                dbc.Col([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Records per page:", className="form-label mb-0 text-end",
                                     style={'lineHeight': '2.25rem'})  
                        ], width=7, className="text-end"),  
                        dbc.Col([
                            dcc.Dropdown(
                                id="compliance-table-page-size-dropdown",
                                options=[
                                    {"label": "10 records", "value": 10},
                                    {"label": "25 records", "value": 25},
                                    {"label": "50 records", "value": 50},
                                    {"label": "100 records", "value": 100}
                                ],
                                value=25,
                                clearable=False,
                                className="form-select-sm"
                            )
                        ], width=5, className="text-start")  
                    ], className="g-1 align-items-center") 
                ], width=3), 

                dbc.Col([
                    dbc.ButtonGroup([
                        dbc.Button("Export CSV", id="compliance-export-csv-btn", color="primary", outline=True, size="sm"),
                        dbc.Button("Export Excel", id="compliance-export-excel-btn", color="success", outline=True, size="sm"),
                        dbc.Button("Export PDF", id="compliance-export-pdf-btn", color="danger", outline=True, size="sm")
                    ], className="float-end")
                ], width=3) 

            ])
        ]),
        dbc.CardBody([
            dcc.Loading([
                html.Div(id="compliance-data-table-container")
            ], type="default")
        ]),
        # Download components
        dcc.Download(id="compliance-download-csv"),
        dcc.Download(id="compliance-download-excel"),
        dcc.Download(id="compliance-download-pdf")
    ], className="mt-4")