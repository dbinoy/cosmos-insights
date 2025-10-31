from dash import html, dcc
import dash_bootstrap_components as dbc

def get_summary_cards_layout():
    """Summary cards showing key training metrics"""
    
    cards = dbc.Row([
        # Total Classes Card
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("0", id="total-classes-card", className="card-title text-primary mb-0"),
                    html.P("Total Classes", className="card-text text-muted mb-0"),
                    html.Small("Scheduled across all AORs", className="text-muted")
                ])
            ], className="h-100 shadow-sm border-0")
        ], width=12, lg=3, className="mb-3"),
        
        # Total Attendances Card  
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("0", id="total-attendances-card", className="card-title text-success mb-0"),
                    html.P("Total Attendances", className="card-text text-muted mb-0"),
                    html.Small("Across all sessions", className="text-muted")
                ])
            ], className="h-100 shadow-sm border-0")
        ], width=12, lg=3, className="mb-3"),
        
        # Average Attendance Rate Card
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("0", id="total-requests-card", className="card-title text-success mb-0"),
                    html.P("Total Requests", className="card-text text-muted mb-0"),
                    html.Small("Across all topics", className="text-muted")
                ])
            ], className="h-100 shadow-sm border-0")
        ], width=12, lg=3, className="mb-3"),
        
        # Active Members Card
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("0", id="active-members-card", className="card-title text-warning mb-0"),
                    html.P("Active Members", className="card-text text-muted mb-0"),
                    html.Small("With training activity", className="text-muted")
                ])
            ], className="h-100 shadow-sm border-0")
        ], width=12, lg=3, className="mb-3")
    ], className="mb-4")
    
    return cards