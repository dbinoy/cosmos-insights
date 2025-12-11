from dash import html, dcc
import dash_bootstrap_components as dbc

def get_data_table_layout():
    return dbc.Card([
        dbc.CardHeader([
            dbc.Row([
                dbc.Col([
                    html.H5("Compliance Data", className="mb-0"),
                    html.Small("Detailed compliance case and report information", className="text-muted")
                ], width=6),
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
                ], width=3),
                dbc.Col([
                    dcc.Dropdown(
                        id="compliance-table-page-size-dropdown",
                        options=[
                            {"label": "25 rows", "value": 25},
                            {"label": "50 rows", "value": 50},
                            {"label": "100 rows", "value": 100},
                            {"label": "200 rows", "value": 200}
                        ],
                        value=50,
                        clearable=False,
                        className="form-select-sm"
                    )
                ], width=2),
                dbc.Col([
                    dbc.ButtonGroup([
                        dbc.Button("CSV", id="compliance-export-csv-btn", color="primary", outline=True, size="sm"),
                        dbc.Button("Excel", id="compliance-export-excel-btn", color="success", outline=True, size="sm"),
                        dbc.Button("PDF", id="compliance-export-pdf-btn", color="danger", outline=True, size="sm")
                    ])
                ], width=1)
            ])
        ]),
        dbc.CardBody([
            dcc.Loading([
                html.Div(id="compliance-data-table-container")
            ], type="dot")
        ]),
        # Download components
        dcc.Download(id="compliance-download-csv"),
        dcc.Download(id="compliance-download-excel"),
        dcc.Download(id="compliance-download-pdf")
    ], className="mt-4")