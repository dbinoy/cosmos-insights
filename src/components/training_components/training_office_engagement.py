from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

def get_office_engagement_layout():
    """Create office-level engagement trend analysis with clean layout"""
    
    empty_fig = go.Figure()
    empty_fig.update_layout(
        title={
            'text': "Training Engagement Trends",
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
            'title': 'Engagement Metric',
            'showgrid': True,
            'gridcolor': '#f0f0f0'
        },
        showlegend=True,
        height=500,  
        margin={'l': 60, 'r': 50, 't': 80, 'b': 100}, 
        plot_bgcolor='white',
        paper_bgcolor='white',
        annotations=[{
            'text': 'Select filters to view engagement trends',
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
                    html.H5("Engagement Trends", className="mb-0"),
                ], width=4),
                dbc.Col([
                    # ✅ Single row with all 3 controls aligned
                    dbc.Row([
                        dbc.Col([
                            html.Label("Show", className="form-label-sm mb-1"),
                            dcc.Dropdown(
                                id="engagement-grouping-dropdown",
                                options=[
                                    {"label": "By AOR", "value": "aor"},
                                    {"label": "By Office", "value": "office"},
                                    {"label": "Top 3", "value": "top3"},
                                    {"label": "Top 5", "value": "top5"},
                                    {"label": "Top 10", "value": "top10"}
                                ],
                                value="top3",
                                clearable=False,
                                className="form-control-sm"
                            )
                        ], width=3),
                        dbc.Col([
                            html.Label("Engagement Metric", className="form-label-sm mb-1"),
                            dcc.Dropdown(
                                id="office-engagement-metric-dropdown",
                                options=[
                                    {"label": "Sessions Held", "value": "sessions_held"},
                                    {"label": "Total Attendances", "value": "total_attendances"},
                                    {"label": "Members Trained", "value": "unique_members"}
                                ],
                                value="total_attendances",
                                clearable=False,
                                className="form-control-sm"
                            )
                        ], width=5),
                        dbc.Col([
                            html.Label("Granularity", className="form-label-sm mb-1"),
                            dcc.Dropdown(
                                id="engagement-time-granularity-dropdown",
                                options=[
                                    {"label": "Monthly", "value": "monthly"},
                                    {"label": "Quarterly", "value": "quarterly"},
                                    {"label": "Yearly", "value": "yearly"}
                                ],
                                value="quarterly",
                                clearable=False,
                                className="form-control-sm"
                            )
                        ], width=4)
                    ])
                ], width=8)
            ])
        ]),
        dbc.CardBody([
            html.Div([  
                dcc.Loading(
                    id="loading-engagement-trends-chart",
                    type="dot", 
                    children=[
                        dcc.Graph(
                            id="engagement-trends-chart",
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
                    id="engagement-insights-summary", 
                    className="mt-3 p-3 bg-light rounded",
                    style={'minHeight': '60px'}
                )                
            ], 
            id="engagement-chart-wrapper",  
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