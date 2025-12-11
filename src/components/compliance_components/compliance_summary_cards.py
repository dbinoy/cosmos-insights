from dash import html
import dash_bootstrap_components as dbc

def get_summary_cards_layout():
    return dbc.Row([
        # Total Cases Card
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(id="compliance-total-cases-value", className="card-title text-primary mb-1"),
                    html.P("Total Cases", className="card-text text-muted mb-1"),
                    html.Small(id="compliance-total-cases-change", className="text-success")
                ])
            ], className="h-100 border-start border-primary border-4")
        ], width=12, lg=2),
        
        # Open Cases Card
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(id="compliance-open-cases-value", className="card-title text-warning mb-1"),
                    html.P("Open Cases", className="card-text text-muted mb-1"),
                    html.Small(id="compliance-open-cases-change", className="text-warning")
                ])
            ], className="h-100 border-start border-warning border-4")
        ], width=12, lg=2),
        
        # Critical Violations Card
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(id="compliance-critical-violations-value", className="card-title text-danger mb-1"),
                    html.P("Critical Violations", className="card-text text-muted mb-1"),
                    html.Small(id="compliance-critical-violations-change", className="text-danger")
                ])
            ], className="h-100 border-start border-danger border-4")
        ], width=12, lg=2),
        
        # Average Resolution Time Card
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(id="compliance-avg-resolution-value", className="card-title text-info mb-1"),
                    html.P("Avg Resolution (Days)", className="card-text text-muted mb-1"),
                    html.Small(id="compliance-avg-resolution-change", className="text-info")
                ])
            ], className="h-100 border-start border-info border-4")
        ], width=12, lg=2),
        
        # Total Fines Card
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(id="compliance-total-fines-value", className="card-title text-success mb-1"),
                    html.P("Total Fines", className="card-text text-muted mb-1"),
                    html.Small(id="compliance-total-fines-change", className="text-success")
                ])
            ], className="h-100 border-start border-success border-4")
        ], width=12, lg=2),
        
        # Compliance Rate Card
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(id="compliance-compliance-rate-value", className="card-title text-secondary mb-1"),
                    html.P("Compliance Rate", className="card-text text-muted mb-1"),
                    html.Small(id="compliance-compliance-rate-change", className="text-secondary")
                ])
            ], className="h-100 border-start border-secondary border-4")
        ], width=12, lg=2)
    ], className="mb-4")