from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

def get_session_scheduling_layout():
    """Create session scheduling trends over time with consistent layout pattern"""
    
    empty_fig = go.Figure()
    empty_fig.update_layout(
        title={
            'text': "Training Session Scheduling Trends",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 16, 'color': '#2c3e50'}
        },
        xaxis={
            'title': 'Time Period',
            'showgrid': False,
            'tickfont': {'size': 10}
        },
        yaxis={
            'title': 'Number of Sessions',
            'showgrid': True,
            'gridcolor': '#f0f0f0'
        },
        showlegend=True,
        height=500,  
        margin={'l': 60, 'r': 50, 't': 80, 'b': 100}, 
        plot_bgcolor='white',
        paper_bgcolor='white',
        annotations=[{
            'text': 'Select filters to view scheduling trends',
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
                    html.H5("Scheduling Trends", className="mb-0")
                ], width=4),
                dbc.Col([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Scheduling Metric", className="form-label-sm mb-1"),
                            dcc.Dropdown(
                                id="scheduling-trend-type-dropdown",  
                                options=[
                                    {"label": "All Sessions", "value": "all"},
                                    {"label": "By AOR", "value": "by_aor"},
                                    {"label": "By Topic", "value": "by_topic"},
                                    {"label": "By Instructor", "value": "by_instructor"}
                                ],
                                value="all",
                                clearable=False,
                                className="form-control-sm"
                            )
                        ], width=7),
                        dbc.Col([
                            html.Label("Granularity", className="form-label-sm mb-1"),
                            dcc.Dropdown(
                                id="scheduling-aggregation-dropdown",
                                options=[
                                    {"label": "Monthly", "value": "monthly"},
                                    {"label": "Quarterly", "value": "quarterly"},
                                    {"label": "Yearly", "value": "yearly"}
                                ],
                                value="monthly",
                                clearable=False,
                                className="form-control-sm"
                            )
                        ], width=5)
                    ])
                ], width=8)
            ])
        ]),
        dbc.CardBody([
            html.Div([  
                dcc.Loading(
                    id="loading-session-scheduling-chart",
                    type="dot", 
                    children=[
                        dcc.Graph(
                            id="session-scheduling-trends-chart",
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
                    id="scheduling-insights-summary", 
                    className="mt-3 p-3 bg-light rounded",
                    style={'minHeight': '60px'}
                )                
            ], 
            id="scheduling-chart-wrapper",  
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