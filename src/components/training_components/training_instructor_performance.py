from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

def get_instructor_performance_layout():
    """Create instructor performance analysis with consistent layout pattern"""
    
    empty_fig = go.Figure()
    empty_fig.update_layout(
        title={
            'text': "Instructor Performance Analysis",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 16, 'color': '#2c3e50'}
        },
        xaxis={
            'title': 'Instructors',
            'showgrid': False,
            'tickfont': {'size': 10}
        },
        yaxis={
            'title': 'Performance Metric',
            'showgrid': True,
            'gridcolor': '#f0f0f0'
        },
        showlegend=True,
        height=500,  
        margin={'l': 60, 'r': 50, 't': 80, 'b': 100}, 
        plot_bgcolor='white',
        paper_bgcolor='white',
        annotations=[{
            'text': 'Select filters to view instructor performance',
            'xref': 'paper', 'yref': 'paper',
            'x': 0.5, 'y': 0.5,
            'xanchor': 'center', 'yanchor': 'middle',
            'showarrow': False,
            'font': {'size': 14, 'color': 'gray'}
        }]
    )
    
    return dbc.Card([
        dbc.CardHeader([
            dbc.Row([
                dbc.Col([
                    html.H5("Instructor Performance", className="mb-0")
                ], width=5),
                dbc.Col([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Performance Metric", className="form-label-sm mb-1"),
                            dcc.Dropdown(
                                id="instructor-performance-metric-dropdown",
                                options=[
                                    {"label": "Attendance Rate %", "value": "attendance_rate"},
                                    {"label": "Total Students Taught", "value": "total_students"},
                                    {"label": "Average Class Size", "value": "avg_class_size"},
                                    {"label": "Classes Conducted", "value": "classes_conducted"},
                                    {"label": "Sessions per Month", "value": "sessions_per_month"}
                                ],
                                value="attendance_rate",
                                clearable=False,
                                className="form-control-sm"
                            )
                        ], width=6),
                        dbc.Col([
                            html.Label("Chart Type", className="form-label-sm mb-1"),
                            dcc.Dropdown(
                                id="instructor-chart-type-dropdown",
                                options=[
                                    {"label": "Bar Chart", "value": "bar"},
                                    {"label": "Horizontal Bar", "value": "horizontal_bar"},
                                    {"label": "Scatter Plot", "value": "scatter"}
                                ],
                                value="bar",
                                clearable=False,
                                className="form-control-sm"
                            )
                        ], width=6)
                    ])
                ], width=7)
            ])
        ]),
        dbc.CardBody([
            html.Div([  
                dcc.Loading(
                    id="loading-instructor-performance-chart",
                    type="dot", 
                    children=[
                        dcc.Graph(
                            id="instructor-performance-chart",
                            figure=empty_fig,
                            config={
                                'displayModeBar': True, 
                                'modeBarButtonsToRemove': ['pan2d', 'lasso2d'],
                                'doubleClick': 'reset'
                            },
                            style={'cursor': 'pointer'}
                        )
                    ]
                ),
                html.Div(
                    id="instructor-performance-insights-summary", 
                    className="mt-3 p-3 bg-light rounded",
                    style={'minHeight': '60px'}
                )                
            ], 
            id="instructor-performance-chart-wrapper",  
            style={
                'cursor': 'pointer',
                'border': '1px solid transparent',
                'borderRadius': '4px',
                'transition': 'border-color 0.2s'
            },
            className="chart-clickable-area"  
            )
        ])        
    ], className="mb-4")