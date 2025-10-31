from dash import html, dcc
import dash_bootstrap_components as dbc

def get_gap_analysis_layout():
    """Create registration vs attendance gap analysis"""
    
    component = dbc.Card([
        dbc.CardHeader([
            html.H5("Registration vs Attendance Analysis", className="mb-0"),
            html.Small("Compare registered participants with actual attendees", className="text-muted")
        ]),
        dbc.CardBody([
            # Chart controls
            dbc.Row([
                dbc.Col([
                    html.Label("Analysis Level:", className="form-label"),
                    dcc.Dropdown(
                        id="gap-analysis-level-dropdown",
                        options=[
                            {"label": "By Training Class", "value": "class"},
                            {"label": "By Topic", "value": "topic"},
                            {"label": "By Instructor", "value": "instructor"},
                            {"label": "By Location", "value": "location"},
                            {"label": "By AOR", "value": "aor"}
                        ],
                        value="class",
                        className="mb-3"
                    )
                ], width=6),
                dbc.Col([
                    html.Label("Sort by:", className="form-label"),
                    dcc.Dropdown(
                        id="gap-analysis-sort-dropdown",
                        options=[
                            {"label": "Highest Gap %", "value": "gap_percent_desc"},
                            {"label": "Lowest Gap %", "value": "gap_percent_asc"},
                            {"label": "Most Registrations", "value": "registrations_desc"},
                            {"label": "Most Attendances", "value": "attendances_desc"}
                        ],
                        value="gap_percent_desc",
                        className="mb-3"
                    )
                ], width=6)
            ]),
            
            # Charts row
            dbc.Row([
                dbc.Col([
                    dcc.Graph(id="registration-attendance-comparison-chart", config={'displayModeBar': False})
                ], width=6),
                dbc.Col([
                    dcc.Graph(id="attendance-rate-gauge", config={'displayModeBar': False})
                ], width=6)
            ])
        ])
    ], className="mb-4 shadow-sm border-0")
    
    return component