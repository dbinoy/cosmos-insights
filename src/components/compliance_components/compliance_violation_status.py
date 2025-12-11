from dash import html, dcc
import dash_bootstrap_components as dbc

def get_violation_status_layout():
    return dbc.Card([
        dbc.CardHeader([
            dbc.Row([
                dbc.Col([
                    html.H5("Current Violation Status", className="mb-0"),
                    html.Small("Overview of compliance violations by status", className="text-muted")
                ], width=8),
                dbc.Col([
                    dcc.Dropdown(
                        id="compliance-violation-status-view-dropdown",
                        options=[
                            {"label": "By Status", "value": "status"},
                            {"label": "By Severity", "value": "severity"},
                            {"label": "By Priority", "value": "priority"}
                        ],
                        value="status",
                        clearable=False,
                        className="form-select-sm"
                    )
                ], width=4)
            ])
        ]),
        dbc.CardBody([
            dcc.Loading([
                dcc.Graph(id="compliance-violation-status-chart")
            ], type="dot")
        ])
    ], className="mb-4")