from dash import html, dcc
import dash_bootstrap_components as dbc

def get_office_engagement_layout():
    """Create office-level engagement trend analysis with 2x2 control layout"""
    
    component = dbc.Card([
        dbc.CardHeader([
            html.H5("Training Engagement Trends", className="mb-0"),
            html.Small("Track training participation trends across AORs and offices over time", className="text-muted")
        ]),
        dbc.CardBody([
            # Enhanced chart controls in 2x2 layout
            dbc.Row([
                # First row of controls
                dbc.Col([
                    html.Label("Group By:", className="form-label"),
                    dcc.Dropdown(
                        id="engagement-grouping-dropdown",
                        options=[
                            {"label": "By AOR", "value": "aor"},
                            {"label": "By Office", "value": "office"},
                            {"label": "Top 10 Performers", "value": "top10"}
                        ],
                        value="aor",
                        className="mb-3"
                    )
                ], width=6),
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
                ], width=6)
            ], className="mb-2"),
            
            dbc.Row([
                # Second row of controls
                dbc.Col([
                    html.Label("Time Granularity:", className="form-label"),
                    dcc.Dropdown(
                        id="engagement-time-granularity-dropdown",
                        options=[
                            {"label": "Monthly", "value": "monthly"},
                            {"label": "Quarterly", "value": "quarterly"},
                            {"label": "Yearly", "value": "yearly"}
                        ],
                        value="monthly",
                        className="mb-3"
                    )
                ], width=6),
                dbc.Col([
                    html.Label("Show Benchmarks:", className="form-label"),
                    dcc.Dropdown(
                        id="engagement-benchmark-dropdown",
                        options=[
                            {"label": "None", "value": "none"},
                            {"label": "Average Line", "value": "average"},
                            {"label": "Target Line", "value": "target"},
                            {"label": "Both", "value": "both"}
                        ],
                        value="average",
                        className="mb-3"
                    )
                ], width=6)
            ], className="mb-3"),
            
            # Trend chart
            dcc.Graph(
                id="engagement-trends-chart", 
                config={'displayModeBar': True, 'modeBarButtonsToRemove': ['pan2d', 'lasso2d']}
            ),
            
            # Summary insights below chart
            html.Div(id="engagement-insights-summary", className="mt-3 p-3 bg-light rounded")
        ])
    ], className="mb-4 shadow-sm border-0")
    
    return component