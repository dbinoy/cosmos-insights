from dash import html, dcc
import dash_bootstrap_components as dbc

def get_escalated_tickets_layout():
    return dbc.Card([
        dbc.CardHeader([
            html.H5("Escalated Tickets Overview", className="mb-0")
        ]),
        dbc.CardBody([
            dcc.Loading(
                dcc.Graph(id="workflow-escalated-tickets-chart", style={'height': '400px'}),
                type="default"
            ),
            html.Div(id="workflow-escalation-insights", className="mt-3")
        ])
    ], className="mb-4")