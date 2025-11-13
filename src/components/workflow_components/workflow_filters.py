from dash import html, dcc
import dash_bootstrap_components as dbc

def get_filters_layout():
    filters_layout = dbc.Card([
        dbc.CardBody([
            # Row 1: Date Range, AOR, Case Type (3 items - width 4 each)
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Label("Date Range"),
                        dcc.DatePickerRange(
                            id="workflow-date-range-picker",
                            start_date_placeholder_text="",
                            end_date_placeholder_text="",
                            disabled=False
                        )
                    ], className="d-grid gap-1")
                ], width=4),                
                dbc.Col([
                    html.Div([
                        html.Label("AOR"),                     
                        dcc.Dropdown(
                            id="workflow-aor-dropdown", 
                            options=[],
                            placeholder="Loading AORs...",
                            multi=True,
                            disabled=False
                        ),
                        dbc.Spinner(
                            id="workflow-aor-spinner",
                            size="sm",
                            color="primary",
                            spinner_style={"position": "relative", "top": "-30px", "right": "-30px"}
                        )                        
                    ], className="d-grid gap-1")
                ], width=4),   
                dbc.Col([
                    html.Div([
                        html.Label("Case Type"),
                        dcc.Dropdown(
                            id="workflow-case-type-dropdown", 
                            options=[],
                            placeholder="Loading Case Types...",
                            multi=True,
                            disabled=False
                        ),
                        dbc.Spinner(
                            id="workflow-case-type-spinner",
                            size="sm",
                            color="primary",
                            spinner_style={"position": "relative", "top": "-30px", "right": "-30px"}
                        )                           
                    ], className="d-grid gap-1")
                ], width=4)                                       
            ], className="mb-2"),
            
            # Row 2: Product, Module, Feature, Issue (4 items - width 3 each)
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Label("Product"),
                        dcc.Dropdown(
                            id="workflow-product-dropdown", 
                            options=[],
                            placeholder="Loading Products...",
                            multi=True,
                            disabled=False
                        ),
                        dbc.Spinner(
                            id="workflow-product-spinner",
                            size="sm",
                            color="primary",
                            spinner_style={"position": "relative", "top": "-30px", "right": "-30px"}
                        )                           
                    ], className="d-grid gap-1")
                ], width=3),
                dbc.Col([
                    html.Div([
                        html.Label("Module"),
                        dcc.Dropdown(
                            id="workflow-module-dropdown", 
                            options=[],
                            placeholder="Loading Modules...",
                            multi=True,
                            disabled=False
                        ),
                        dbc.Spinner(
                            id="workflow-module-spinner",
                            size="sm",
                            color="primary",
                            spinner_style={"position": "relative", "top": "-30px", "right": "-30px"}
                        )                           
                    ], className="d-grid gap-1")
                ], width=3),
                dbc.Col([
                    html.Div([
                        html.Label("Feature"),
                        dcc.Dropdown(
                            id="workflow-feature-dropdown", 
                            options=[],
                            placeholder="Loading Features...",
                            multi=True,
                            disabled=False
                        ),
                        dbc.Spinner(
                            id="workflow-feature-spinner",
                            size="sm",
                            color="primary",
                            spinner_style={"position": "relative", "top": "-30px", "right": "-30px"}
                        )                           
                    ], className="d-grid gap-1")
                ], width=3),
                dbc.Col([
                    html.Div([
                        html.Label("Issue"),
                        dcc.Dropdown(
                            id="workflow-issue-dropdown", 
                            options=[],
                            placeholder="Loading Issues...",
                            multi=True,
                            disabled=False
                        ),
                        dbc.Spinner(
                            id="workflow-issue-spinner",
                            size="sm",
                            color="primary",
                            spinner_style={"position": "relative", "top": "-30px", "right": "-30px"}
                        )                           
                    ], className="d-grid gap-1")
                ], width=3)              
            ], className="mb-2"),
            
            # Row 3: Case Origin, Case Reason, Status, Priority (4 items - width 3 each)
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Label("Case Origin"),
                        dcc.Dropdown(
                            id="workflow-origin-dropdown", 
                            options=[],
                            placeholder="Loading Case Origins...",
                            multi=True,
                            disabled=False
                        ),
                        dbc.Spinner(
                            id="workflow-origin-spinner",
                            size="sm",
                            color="primary",
                            spinner_style={"position": "relative", "top": "-30px", "right": "-30px"}
                        )                           
                    ], className="d-grid gap-1")
                ], width=3),
                dbc.Col([
                    html.Div([
                        html.Label("Case Reason"),
                        dcc.Dropdown(
                            id="workflow-case-reason-dropdown", 
                            options=[],
                            placeholder="Loading Case Reasons...",
                            multi=True,
                            disabled=False
                        ),
                        dbc.Spinner(
                            id="workflow-case-reason-spinner",
                            size="sm",
                            color="primary",
                            spinner_style={"position": "relative", "top": "-30px", "right": "-30px"}
                        )                           
                    ], className="d-grid gap-1")
                ], width=3),
                dbc.Col([
                    html.Div([
                        html.Label("Status"),
                        dcc.Dropdown(
                            id="workflow-status-dropdown", 
                            options=[],
                            placeholder="Loading Statuses...",
                            multi=True,
                            disabled=False
                        ),
                        dbc.Spinner(
                            id="workflow-status-spinner",
                            size="sm",
                            color="primary",
                            spinner_style={"position": "relative", "top": "-30px", "right": "-30px"}
                        )                           
                    ], className="d-grid gap-1")
                ], width=3),
                dbc.Col([
                    html.Div([
                        html.Label("Priority"),
                        dcc.Dropdown(
                            id="workflow-priority-dropdown", 
                            options=[],
                            placeholder="Loading Priorities...",
                            multi=True,
                            disabled=False
                        ),
                        dbc.Spinner(
                            id="workflow-priority-spinner",
                            size="sm",
                            color="primary",
                            spinner_style={"position": "relative", "top": "-30px", "right": "-30px"}
                        )                           
                    ], className="d-grid gap-1")
                ], width=3)              
            ], className="mb-2"),
        ]),
        ], className="mb-3"
    )    
    return filters_layout