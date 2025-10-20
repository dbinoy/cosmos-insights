from dash import html, dcc
import dash_bootstrap_components as dbc
import pandas as pd

def get_filters_layout():
    filters_layout = dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Label("Date Range"),
                        dcc.DatePickerRange(
                            id="training-date-range-picker",
                            start_date_placeholder_text="",
                            end_date_placeholder_text="",
                            disabled=False
                        )
                    ], className="d-grid gap-1")
                ], width=4),                
                dbc.Col([
                    html.Div([
                        html.Label("Aor"),
                        dcc.Dropdown(
                            id="training-aor-dropdown", 
                            options=[],
                            placeholder="Select Aor",
                            multi=True,
                            disabled=False
                        )
                    ], className="d-grid gap-1")
                ], width=6),   
                dbc.Col([
                    html.Div([
                        html.Label("Office"),
                        dcc.Dropdown(
                            id="training-office-dropdown", 
                            options=[],
                            placeholder="Select Office",
                            multi=True,
                            disabled=False
                        )
                    ], className="d-grid gap-1")
                ], width=2)                
            ], className="mb-2"),
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Label("Topics"),
                        dcc.Dropdown(
                            id="training-topics-dropdown", 
                            options=[],
                            placeholder="Select Topics",
                            multi=True,
                            disabled=False
                        )
                    ], className="d-grid gap-1")
                ], width=4), 
                dbc.Col([
                    html.Div([
                        html.Label("Instructor"),
                        # dcc.Dropdown(
                        #     id="training-instructor-dropdown", 
                        #     options=[],
                        #     placeholder="Select Instructor",
                        #     multi=True,
                        #     disabled=False
                        # )
                    ], className="d-grid gap-1")
                ], width=3), 
                dbc.Col([
                    html.Div([
                        html.Label("Location"),
                        # dcc.Dropdown(
                        #     id="training-location-dropdown", 
                        #     options=[],
                        #     placeholder="Select Location",
                        #     multi=True,
                        #     disabled=False
                        # )
                    ], className="d-grid gap-1")
                ], width=5),                   
            ], className="mb-2"),
            dbc.Row([                
                dbc.Col([
                    html.Div([
                        html.Label("Class"),
                        # dcc.Dropdown(
                        #     id="training-class-dropdown", 
                        #     options=[],
                        #     placeholder="Select Class",
                        #     multi=True,
                        #     disabled=False
                        # )
                    ], className="d-grid gap-1")
                ], width=12)                                             
            ], className="mb-2"),
        ]),
        ], className="mb-3"
    )    
    return filters_layout