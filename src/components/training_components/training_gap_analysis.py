from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

def get_gap_analysis_layout():
    """Create registration vs attendance gap analysis with consistent layout pattern"""
    
    empty_fig = go.Figure()
    empty_fig.update_layout(
        title={
            'text': "Registration vs Attendance Analysis",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 16, 'color': '#2c3e50'}
        },
        xaxis={
            'title': 'Analysis Category',
            'showgrid': False,
            'tickfont': {'size': 10}
        },
        yaxis={
            'title': 'Count',
            'showgrid': True,
            'gridcolor': '#f0f0f0'
        },
        showlegend=True,
        height=500,  
        margin={'l': 60, 'r': 50, 't': 80, 'b': 100}, 
        plot_bgcolor='white',
        paper_bgcolor='white',
        annotations=[{
            'text': 'Select filters to view registration vs attendance gap analysis',
            'xref': 'paper', 'yref': 'paper',
            'x': 0.5, 'y': 0.5,
            'xanchor': 'center', 'yanchor': 'middle',
            'showarrow': False,
            'font': {'size': 14, 'color': 'gray'}
        }]
    )
    
    empty_gauge = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = 0,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Overall Attendance Rate"},
        gauge = {
            'axis': {'range': [None, 100]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 50], 'color': "lightgray"},
                {'range': [50, 85], 'color': "gray"},
                {'range': [85, 100], 'color': "lightgreen"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))
    
    empty_gauge.update_layout(
        height=400,
        margin={'l': 20, 'r': 20, 't': 60, 'b': 20},
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    return dbc.Card([
        dbc.CardHeader([
            dbc.Row([
                dbc.Col([
                    html.H5("Registration vs Attendance Analysis", className="mb-0"),
                    html.Small("Compare registered participants with actual attendees", className="text-muted")
                ], width=4),
                dbc.Col([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Analysis Level", className="form-label-sm mb-1"),
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
                                clearable=False,
                                className="form-control-sm"
                            )
                        ], width=6),
                        dbc.Col([
                            html.Label("Sort by", className="form-label-sm mb-1"),
                            dcc.Dropdown(
                                id="gap-analysis-sort-dropdown",
                                options=[
                                    {"label": "Highest Gap %", "value": "gap_percent_desc"},
                                    {"label": "Lowest Gap %", "value": "gap_percent_asc"},
                                    {"label": "Most Registrations", "value": "registrations_desc"},
                                    {"label": "Most Attendances", "value": "attendances_desc"}
                                ],
                                value="gap_percent_desc",
                                clearable=False,
                                className="form-control-sm"
                            )
                        ], width=6)
                    ])
                ], width=8)
            ])
        ]),
        dbc.CardBody([
            # Charts row
            dbc.Row([
                dbc.Col([
                    html.Div([
                        dcc.Loading(
                            id="loading-registration-attendance-comparison-chart",
                            type="dot", 
                            children=[
                                dcc.Graph(
                                    id="registration-attendance-comparison-chart",
                                    figure=empty_fig,
                                    config={
                                        'displayModeBar': True, 
                                        'modeBarButtonsToRemove': ['pan2d', 'lasso2d'],
                                        'doubleClick': 'reset'
                                    },
                                    style={'cursor': 'pointer'}
                                )
                            ]
                        )
                    ], 
                    id="registration-comparison-chart-wrapper",  
                    style={
                        'cursor': 'pointer',
                        'border': '1px solid transparent',
                        'borderRadius': '4px',
                        'transition': 'border-color 0.2s'
                    },
                    className="chart-clickable-area"
                    )
                ], width=8),
                dbc.Col([
                    html.Div([
                        dcc.Loading(
                            id="loading-attendance-rate-gauge",
                            type="dot", 
                            children=[
                                dcc.Graph(
                                    id="attendance-rate-gauge",
                                    figure=empty_gauge,
                                    config={'displayModeBar': False},
                                    style={'cursor': 'pointer'}
                                )
                            ]
                        )
                    ], 
                    id="attendance-gauge-chart-wrapper",  
                    style={
                        'cursor': 'pointer',
                        'border': '1px solid transparent',
                        'borderRadius': '4px',
                        'transition': 'border-color 0.2s'
                    },
                    className="chart-clickable-area"
                    )
                ], width=4)
            ]),
            
            # Insights row
            html.Div(
                id="gap-analysis-insights-summary", 
                className="mt-3 p-3 bg-light rounded",
                style={'minHeight': '60px'}
            )
        ])        
    ], className="mb-4")