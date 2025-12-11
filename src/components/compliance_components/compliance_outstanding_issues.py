from dash import html, dcc
import dash_bootstrap_components as dbc

def get_outstanding_issues_layout():
    return dbc.Card([
        dbc.CardHeader([
            dbc.Row([
                dbc.Col([
                    html.H5("Outstanding Issues", className="mb-0"),
                    html.Small("Unresolved violations with severity and priority", className="text-muted")
                ], width=8),
                dbc.Col([
                    dcc.Dropdown(
                        id="compliance-outstanding-issues-sort-dropdown",
                        options=[
                            {"label": "By Priority", "value": "priority"},
                            {"label": "By Severity", "value": "severity"},
                            {"label": "By Age", "value": "age"},
                            {"label": "By Fine Amount", "value": "fine"}
                        ],
                        value="priority",
                        clearable=False,
                        className="form-select-sm"
                    )
                ], width=4)
            ])
        ]),
        dbc.CardBody([
            dcc.Loading([
                dcc.Graph(id="compliance-outstanding-issues-chart")
            ], type="dot")
        ])
    ], className="mb-4")