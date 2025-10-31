from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

def get_engaged_members_layout():
    """Create top engaged members visualization with control dropdowns"""
    
    # Empty figure as placeholder
    empty_fig = go.Figure()
    empty_fig.update_layout(
        title="Top Engaged Members",
        showlegend=False,
        height=400,
        annotations=[{
            'text': 'Select filters to view data',
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
                    html.H5("Top Engaged Members", className="mb-0")
                ], width=6),
                dbc.Col([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Engagement Metric", className="form-label-sm mb-1"),
                            dcc.Dropdown(
                                id="engagement-metric-dropdown",
                                options=[
                                    {'label': 'Sessions Attended', 'value': 'sessions_attended'},
                                    {'label': 'Training Hours', 'value': 'training_hours'},
                                    {'label': 'Topics Completed', 'value': 'topics_completed'},
                                ],
                                value='sessions_attended',
                                clearable=False,
                                className="form-control-sm"
                            )
                        ], width=8),
                        dbc.Col([
                            html.Label("Show Top", className="form-label-sm mb-1"),
                            dcc.Dropdown(
                                id="top-members-count-dropdown",
                                options=[
                                    {'label': '10', 'value': 10},
                                    {'label': '20', 'value': 20},
                                    {'label': '30', 'value': 30},
                                    {'label': '50', 'value': 50}
                                ],
                                value=20,
                                clearable=False,
                                className="form-control-sm"
                            )
                        ], width=4)
                    ])
                ], width=6)
            ])
        ]),
        dbc.CardBody([
            dcc.Graph(
                id="top-engaged-members-chart",
                figure=empty_fig,
                config={'displayModeBar': False}
            )
        ])
    ], className="mb-4")