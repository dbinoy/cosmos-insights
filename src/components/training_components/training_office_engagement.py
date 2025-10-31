from dash import html, dcc
import dash_bootstrap_components as dbc

def get_office_engagement_layout():
    """Create office-level engagement heatmap"""
    
    component = dbc.Card([
        dbc.CardHeader([
            html.H5("Office-Level Training Engagement", className="mb-0"),
            html.Small("Training participation across different offices and AORs", className="text-muted")
        ]),
        dbc.CardBody([
            # Chart controls
            dbc.Row([
                dbc.Col([
                    html.Label("Engagement Metric:", className="form-label"),
                    dcc.Dropdown(
                        id="office-engagement-metric-dropdown",
                        options=[
                            {"label": "Total Attendances", "value": "total_attendances"},
                            {"label": "Unique Members Trained", "value": "unique_members"},
                            {"label": "Average Attendance Rate", "value": "avg_attendance_rate"},
                            {"label": "Classes per Member", "value": "classes_per_member"}
                        ],
                        value="total_attendances",
                        className="mb-3"
                    )
                ], width=6),
                dbc.Col([
                    html.Label("Time Period:", className="form-label"),
                    dcc.Dropdown(
                        id="office-engagement-period-dropdown",
                        options=[
                            {"label": "All Time", "value": "all"},
                            {"label": "Last 12 Months", "value": "12m"},
                            {"label": "Last 6 Months", "value": "6m"},
                            {"label": "Last 3 Months", "value": "3m"}
                        ],
                        value="12m",
                        className="mb-3"
                    )
                ], width=6)
            ]),
            
            # Chart
            dcc.Graph(id="office-engagement-heatmap", config={'displayModeBar': False})
        ])
    ], className="mb-4 shadow-sm border-0")
    
    return component