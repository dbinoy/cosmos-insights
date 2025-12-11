from dash import html, dcc
import dash_bootstrap_components as dbc

def get_recent_activities_layout():
    return dbc.Card([
        dbc.CardHeader([
            dbc.Row([
                dbc.Col([
                    html.H5("Recent Activities", className="mb-0"),
                    html.Small("Latest compliance activities and case events", className="text-muted")
                ], width=8),
                dbc.Col([
                    dcc.Dropdown(
                        id="compliance-recent-activities-timeframe-dropdown",
                        options=[
                            {"label": "Last 7 Days", "value": "7d"},
                            {"label": "Last 30 Days", "value": "30d"},
                            {"label": "Last 90 Days", "value": "90d"},
                            {"label": "Last 6 Months", "value": "6m"}
                        ],
                        value="30d",
                        clearable=False,
                        className="form-select-sm"
                    )
                ], width=4)
            ])
        ]),
        dbc.CardBody([
            dcc.Loading([
                dcc.Graph(id="compliance-recent-activities-chart")
            ], type="dot")
        ])
    ], className="mb-4")