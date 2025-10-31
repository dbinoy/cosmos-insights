from dash import html, dcc
import dash_bootstrap_components as dbc

def get_instructor_performance_layout():
    """Create instructor performance ranking"""
    
    component = dbc.Card([
        dbc.CardHeader([
            html.H5("Instructor Performance Analysis", className="mb-0"),
            html.Small("Instructor effectiveness based on attendance rates and engagement", className="text-muted")
        ]),
        dbc.CardBody([
            # Chart controls
            dbc.Row([
                dbc.Col([
                    html.Label("Performance Metric:", className="form-label"),
                    dcc.Dropdown(
                        id="instructor-performance-metric-dropdown",
                        options=[
                            {"label": "Attendance Rate %", "value": "attendance_rate"},
                            {"label": "Total Students Taught", "value": "total_students"},
                            {"label": "Average Class Size", "value": "avg_class_size"},
                            {"label": "Classes Conducted", "value": "classes_conducted"},
                            {"label": "Member Satisfaction Score", "value": "satisfaction_score"}
                        ],
                        value="attendance_rate",
                        className="mb-3"
                    )
                ], width=6),
                dbc.Col([
                    html.Label("Minimum Classes:", className="form-label"),
                    dcc.Dropdown(
                        id="instructor-min-classes-dropdown",
                        options=[
                            {"label": "Any (1+)", "value": 1},
                            {"label": "5+ Classes", "value": 5},
                            {"label": "10+ Classes", "value": 10},
                            {"label": "20+ Classes", "value": 20}
                        ],
                        value=5,
                        className="mb-3"
                    )
                ], width=6)
            ]),
            
            # Chart
            dcc.Graph(id="instructor-performance-chart", config={'displayModeBar': False})
        ])
    ], className="mb-4 shadow-sm border-0")
    
    return component