from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

def get_engaged_members_layout():
    """Create top engaged members visualization with control dropdowns (vertical bar style)"""
    
    # ✅ UPDATED: Empty figure matching vertical bar chart style
    empty_fig = go.Figure()
    empty_fig.update_layout(
        title={
            'text': "Top Engaged Members",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 16, 'color': '#2c3e50'}
        },
        xaxis={
            'title': 'Member Name',
            'showgrid': False,
            'tickfont': {'size': 10}
        },
        yaxis={
            'title': 'Sessions Attended',
            'showgrid': True,
            'gridcolor': '#f0f0f0'
        },
        showlegend=False,
        height=500,  # ✅ CHANGED: Match main chart height
        margin={'l': 60, 'r': 50, 't': 80, 'b': 100},  # ✅ CHANGED: Match main chart margins
        plot_bgcolor='white',
        paper_bgcolor='white',
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
                                    {'label': 'Topics Completed', 'value': 'topics_completed'}
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