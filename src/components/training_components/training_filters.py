from dash import html, dcc
import dash_bootstrap_components as dbc

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
                            placeholder="Loading AORs...",
                            multi=True,
                            disabled=False
                        ),
                        dbc.Spinner(
                            id="training-aor-spinner",
                            size="sm",
                            color="primary",
                            spinner_style={"position": "relative", "top": "-30px", "right": "-30px"}
                        )                        
                    ], className="d-grid gap-1")
                ], width=6),   
                dbc.Col([
                    html.Div([
                        html.Label("Office"),
                        dcc.Dropdown(
                            id="training-office-dropdown", 
                            options=[],
                            placeholder="Loading Offices...",
                            multi=True,
                            disabled=False
                        ),
                        dbc.Spinner(
                            id="training-office-spinner",
                            size="sm",
                            color="primary",
                            spinner_style={"position": "relative", "top": "-30px", "right": "-30px"}
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
                            placeholder="Loading Topics...",
                            multi=True,
                            disabled=False
                        ),
                        dbc.Spinner(
                            id="training-topics-spinner",
                            size="sm",
                            color="primary",
                            spinner_style={"position": "relative", "top": "-30px", "right": "-30px"}
                        )                           
                    ], className="d-grid gap-1")
                ], width=4), 
                dbc.Col([
                    html.Div([
                        html.Label("Instructor"),
                        dcc.Dropdown(
                            id="training-instructor-dropdown", 
                            options=[],
                            placeholder="Loading Instructors...",
                            multi=True,
                            disabled=False
                        ),
                        dbc.Spinner(
                            id="training-instructor-spinner",
                            size="sm",
                            color="primary",
                            spinner_style={"position": "relative", "top": "-30px", "right": "-30px"}
                        )                           
                    ], className="d-grid gap-1")
                ], width=3), 
                dbc.Col([
                    html.Div([
                        html.Label("Location"),
                        dcc.Dropdown(
                            id="training-location-dropdown", 
                            options=[],
                            placeholder="Loading Locations...",
                            multi=True,
                            disabled=False
                        ),
                        dbc.Spinner(
                            id="training-location-spinner",
                            size="sm",
                            color="primary",
                            spinner_style={"position": "relative", "top": "-30px", "right": "-30px"}
                        )                           
                    ], className="d-grid gap-1")
                ], width=5),                   
            ], className="mb-2"),
            dbc.Row([                
                dbc.Col([
                    html.Div([
                        html.Label("Class"),
                        dcc.Dropdown(
                            id="training-class-dropdown", 
                            options=[],
                            placeholder="Loading Classes...",
                            multi=True,
                            disabled=False
                        ),
                        dbc.Spinner(
                            id="training-class-spinner",
                            size="sm",
                            color="primary",
                            spinner_style={"position": "relative", "top": "-30px", "right": "-30px"}
                        )                           
                    ], className="d-grid gap-1")
                ], width=12)                                             
            ], className="mb-2"),
        ]),
        ], className="mb-3"
    )    
    return filters_layout