from dash import html, dcc
import dash_bootstrap_components as dbc

def get_session_scheduling_layout():
    """Create session scheduling trends over time"""
    
    component = dbc.Card([
        dbc.CardHeader([
            html.H5("Training Session Scheduling Trends", className="mb-0"),
            html.Small("Number of sessions scheduled by month and year", className="text-muted")
        ]),
        dbc.CardBody([
            # Chart controls
            dbc.Row([
                dbc.Col([
                    html.Label("Aggregation Level:", className="form-label"),
                    dcc.Dropdown(
                        id="scheduling-aggregation-dropdown",
                        options=[
                            {"label": "By Month", "value": "month"},
                            {"label": "By Quarter", "value": "quarter"},
                            {"label": "By Year", "value": "year"}
                        ],
                        value="month",
                        className="mb-3"
                    )
                ], width=4),
                dbc.Col([
                    html.Label("Show Trend for:", className="form-label"),
                    dcc.Dropdown(
                        id="scheduling-trend-type-dropdown",
                        options=[
                            {"label": "All Sessions", "value": "all"},
                            {"label": "By AOR", "value": "by_aor"},
                            {"label": "By Topic", "value": "by_topic"},
                            {"label": "By Instructor", "value": "by_instructor"}
                        ],
                        value="all",
                        className="mb-3"
                    )
                ], width=4),
                dbc.Col([
                    # dbc.CardGroup([
                        dbc.Checkbox(
                            id="show-forecast-checkbox",
                            label="Show 3-month forecast",
                            value=False,
                            className="mb-3"
                        )
                    # ])
                ], width=4)
            ]),
            
            # Chart
            dcc.Graph(id="session-scheduling-trends-chart", config={'displayModeBar': False})
        ])
    ], className="mb-4 shadow-sm border-0")
    
    return component