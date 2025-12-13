from dash import html
import dash_bootstrap_components as dbc

def get_summary_cards_layout():
    summary_cards_layout = dbc.Row([
        # Total Cases Card
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("0", id="compliance-total-cases-value", className="card-title text-primary mb-0"),
                    html.P("Total Cases", className="card-text text-muted mb-0"),
                    html.Small("Across all filters", className="text-muted"),
                    html.Small(id="compliance-total-cases-change", className="text-success"),
                    dbc.Spinner(
                        id="compliance-total-cases-spinner",
                        size="sm",
                        color="warning",
                        spinner_style={"position": "absolute", "top": "10px", "right": "10px"}
                    )
                ], style={"position": "relative"})
            ], className="h-100 shadow-sm border-0")
        ], width=12, lg=2, className="mb-3"),
        
        # Open Cases Card
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("0", id="compliance-open-cases-value", className="card-title text-warning mb-0"),
                    html.P("Open Cases", className="card-text text-muted mb-0"),
                    html.Small("Currently active", className="text-muted"),
                    html.Small(id="compliance-open-cases-change", className="text-warning"),
                    dbc.Spinner(
                        id="compliance-open-cases-spinner",
                        size="sm",
                        color="warning",
                        spinner_style={"position": "absolute", "top": "10px", "right": "10px"}
                    )
                ], style={"position": "relative"})
            ], className="h-100 shadow-sm border-0")
        ], width=12, lg=2, className="mb-3"),
        
        # Average Resolution Time Card
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("0d", id="compliance-avg-resolution-value", className="card-title text-success mb-0"),
                    html.P("Avg Resolution Time", className="card-text text-muted mb-0"),
                    html.Small("Time to close", className="text-muted"),
                    html.Small(id="compliance-avg-resolution-change", className="text-success"),
                    dbc.Spinner(
                        id="compliance-avg-resolution-spinner",
                        size="sm",
                        color="warning",
                        spinner_style={"position": "absolute", "top": "10px", "right": "10px"}
                    )
                ], style={"position": "relative"})
            ], className="h-100 shadow-sm border-0")
        ], width=12, lg=2, className="mb-3"),
        
        # Total Citations Card
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("0", id="compliance-total-citations-value", className="card-title text-info mb-0"),
                    html.P("Total Citations", className="card-text text-muted mb-0"),
                    html.Small("Cases with citations", className="text-muted"),
                    html.Small(id="compliance-total-citations-change", className="text-info"),
                    dbc.Spinner(
                        id="compliance-total-citations-spinner",
                        size="sm",
                        color="warning",
                        spinner_style={"position": "absolute", "top": "10px", "right": "10px"}
                    )
                ], style={"position": "relative"})
            ], className="h-100 shadow-sm border-0")
        ], width=12, lg=2, className="mb-3"),
        
        # High-Risk Members Card
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("0", id="compliance-high-risk-members-value", className="card-title text-danger mb-0"),
                    html.P("High-Risk Members", className="card-text text-muted mb-0"),
                    html.Small("10+ cases", className="text-muted"),
                    html.Small(id="compliance-high-risk-members-change", className="text-danger"),
                    dbc.Spinner(
                        id="compliance-high-risk-members-spinner",
                        size="sm",
                        color="warning",
                        spinner_style={"position": "absolute", "top": "10px", "right": "10px"}
                    )
                ], style={"position": "relative"})
            ], className="h-100 shadow-sm border-0")
        ], width=12, lg=2, className="mb-3"),
        
        # Top Agent Card
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("N/A", id="compliance-top-agent-value", className="card-title text-secondary mb-0"),
                    html.P("Top Agent", className="card-text text-muted mb-0"),
                    html.Small("Highest case load", className="text-muted"),
                    html.Small(id="compliance-top-agent-change", className="text-secondary"),
                    dbc.Spinner(
                        id="compliance-top-agent-spinner",
                        size="sm",
                        color="warning",
                        spinner_style={"position": "absolute", "top": "10px", "right": "10px"}
                    )
                ], style={"position": "relative"})
            ], className="h-100 shadow-sm border-0")
        ], width=12, lg=2, className="mb-3")
    ], className="mb-4")

    return summary_cards_layout