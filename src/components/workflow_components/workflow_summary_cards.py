from dash import html
import dash_bootstrap_components as dbc

def get_summary_cards_layout():
    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(id="workflow-total-tickets-value", className="card-title text-primary"),
                    html.P("Total Tickets", className="card-text"),
                    html.Small(id="workflow-total-tickets-trend", className="text-muted")
                ])
            ])
        ], width=12, md=2),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(id="workflow-open-tickets-value", className="card-title text-warning"),
                    html.P("Open Tickets", className="card-text"),
                    html.Small(id="workflow-open-tickets-trend", className="text-muted")
                ])
            ])
        ], width=12, md=2),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(id="workflow-escalated-tickets-value", className="card-title text-danger"),
                    html.P("Escalated Tickets", className="card-text"),
                    html.Small(id="workflow-escalated-tickets-trend", className="text-muted")
                ])
            ])
        ], width=12, md=2),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(id="workflow-avg-resolution-value", className="card-title text-success"),
                    html.P("Avg Resolution Time", className="card-text"),
                    html.Small(id="workflow-avg-resolution-trend", className="text-muted")
                ])
            ])
        ], width=12, md=2),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(id="workflow-closed-tickets-value", className="card-title text-info"),
                    html.P("Closed This Month", className="card-text"),
                    html.Small(id="workflow-closed-tickets-trend", className="text-muted")
                ])
            ])
        ], width=12, md=2),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(id="workflow-sla-compliance-value", className="card-title text-secondary"),
                    html.P("SLA Compliance", className="card-text"),
                    html.Small(id="workflow-sla-compliance-trend", className="text-muted")
                ])
            ])
        ], width=12, md=2)
    ], className="mb-4")