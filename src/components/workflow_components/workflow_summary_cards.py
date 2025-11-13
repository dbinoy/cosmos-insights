from dash import html
import dash_bootstrap_components as dbc

def get_summary_cards_layout():
    """Summary cards showing key workflow metrics"""
    
    cards = dbc.Row([
        # Total Tickets
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("0", id="workflow-total-tickets-value", className="card-title text-primary mb-0"),
                    html.P("Total Tickets", className="card-text text-muted mb-0"),
                    html.Small("Across all filters", className="text-muted"),
                    dbc.Spinner(
                        id="workflow-total-tickets-spinner",
                        size="sm",
                        color="warning",
                        spinner_style={"position": "absolute", "top": "10px", "right": "10px"}
                    )
                ], style={"position": "relative"})
            ], className="h-100 shadow-sm border-0")
        ], width=12, lg=2, className="mb-3"),
        
        # Open Tickets
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("0", id="workflow-open-tickets-value", className="card-title text-warning mb-0"),
                    html.P("Open Tickets", className="card-text text-muted mb-0"),
                    html.Small("Currently active", className="text-muted"),
                    dbc.Spinner(
                        id="workflow-open-tickets-spinner",
                        size="sm",
                        color="warning",
                        spinner_style={"position": "absolute", "top": "10px", "right": "10px"}
                    )
                ], style={"position": "relative"})
            ], className="h-100 shadow-sm border-0")
        ], width=12, lg=2, className="mb-3"),
        
        # Escalated Tickets
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("0", id="workflow-escalated-tickets-value", className="card-title text-danger mb-0"),
                    html.P("Escalated Tickets", className="card-text text-muted mb-0"),
                    html.Small("Requiring attention", className="text-muted"),
                    dbc.Spinner(
                        id="workflow-escalated-tickets-spinner",
                        size="sm",
                        color="warning",
                        spinner_style={"position": "absolute", "top": "10px", "right": "10px"}
                    )
                ], style={"position": "relative"})
            ], className="h-100 shadow-sm border-0")
        ], width=12, lg=2, className="mb-3"),
        
        # Average Resolution Time
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("0h", id="workflow-avg-resolution-value", className="card-title text-success mb-0"),
                    html.P("Avg Resolution Time", className="card-text text-muted mb-0"),
                    html.Small("Time to close", className="text-muted"),
                    dbc.Spinner(
                        id="workflow-avg-resolution-spinner",
                        size="sm",
                        color="warning",
                        spinner_style={"position": "absolute", "top": "10px", "right": "10px"}
                    )
                ], style={"position": "relative"})
            ], className="h-100 shadow-sm border-0")
        ], width=12, lg=2, className="mb-3"),
        
        # Closed This Month
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("0", id="workflow-closed-tickets-value", className="card-title text-info mb-0"),
                    html.P("Closed This Month", className="card-text text-muted mb-0"),
                    html.Small("Recently resolved", className="text-muted"),
                    dbc.Spinner(
                        id="workflow-closed-tickets-spinner",
                        size="sm",
                        color="warning",
                        spinner_style={"position": "absolute", "top": "10px", "right": "10px"}
                    )
                ], style={"position": "relative"})
            ], className="h-100 shadow-sm border-0")
        ], width=12, lg=2, className="mb-3"),
        
        # Active Assignees
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("0", id="workflow-active-assignees-value", className="card-title text-secondary mb-0"),
                    html.P("Active Assignees", className="card-text text-muted mb-0"),
                    html.Small("Working on tickets", className="text-muted"),
                    dbc.Spinner(
                        id="workflow-active-assignees-spinner",
                        size="sm",
                        color="warning",
                        spinner_style={"position": "absolute", "top": "10px", "right": "10px"}
                    )
                ], style={"position": "relative"})
            ], className="h-100 shadow-sm border-0")
        ], width=12, lg=2, className="mb-3")
    ], className="mb-4")
    
    return cards