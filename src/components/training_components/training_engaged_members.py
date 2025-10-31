from dash import html, dcc
import dash_bootstrap_components as dbc

def get_engaged_members_layout():
    """Create top engaged members visualization"""
    
    component = dbc.Card([
        dbc.CardHeader([
            html.H5("Top Engaged Members", className="mb-0"),
            html.Small("Members with highest training participation", className="text-muted")
        ]),
        dbc.CardBody([
            # Chart controls
            dbc.Row([
                dbc.Col([
                    html.Label("Engagement Metric:", className="form-label"),
                    dcc.Dropdown(
                        id="engagement-metric-dropdown",
                        options=[
                            {"label": "Total Sessions Attended", "value": "sessions_attended"},
                            {"label": "Total Training Hours", "value": "training_hours"},
                            {"label": "Unique Topics Completed", "value": "topics_completed"},
                            {"label": "Attendance Rate %", "value": "attendance_rate"}
                        ],
                        value="sessions_attended",
                        className="mb-3"
                    )
                ], width=6),
                dbc.Col([
                    html.Label("Show Top:", className="form-label"),
                    dcc.Dropdown(
                        id="top-members-count-dropdown",
                        options=[
                            {"label": "Top 10", "value": 10},
                            {"label": "Top 20", "value": 20},
                            {"label": "Top 50", "value": 50}
                        ],
                        value=20,
                        className="mb-3"
                    )
                ], width=6)
            ]),
            
            # Chart
            dcc.Graph(id="top-engaged-members-chart", config={'displayModeBar': False})
        ])
    ], className="mb-4 shadow-sm border-0")
    
    return component