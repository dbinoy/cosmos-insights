from dash import html, dcc
import dash_bootstrap_components as dbc

def get_ticket_volume_layout():
    return dbc.Card([
        dbc.CardHeader([
            dbc.Row([
                dbc.Col([
                    html.H5("Ticket Volume Over Time", className="mb-0")
                ], width=8),
                dbc.Col([
                    dbc.ButtonGroup([
                        dbc.Button("Daily", id="workflow-volume-daily-btn", size="sm", outline=True),
                        dbc.Button("Weekly", id="workflow-volume-weekly-btn", size="sm", outline=True, active=True),
                        dbc.Button("Monthly", id="workflow-volume-monthly-btn", size="sm", outline=True)
                    ], size="sm")
                ], width=4, className="text-end")
            ])
        ]),
        dbc.CardBody([
            dcc.Loading(
                dcc.Graph(id="workflow-ticket-volume-chart", style={'height': '400px'}),
                type="default"
            ),
            html.Div(id="workflow-volume-insights", className="mt-3")
        ])
    ], className="mb-4")