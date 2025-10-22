
from dash import html, dcc
import dash_bootstrap_components as dbc
from src.components.training_components.filters import get_filters_layout

def create_training_dashboard_layout():
    return dbc.Container([
        dcc.Store(id="training-filtered-query-store"),
        dcc.Store(id="training-filter-data-store"),    
        # dcc.Interval(id="training-filter-fetch-interval", interval=500, n_intervals=0, max_intervals=1),
        html.H3("Training Dashboard (Under Development)"),  
        html.Hr(),
        dbc.Row([
            dbc.Col(
                dbc.Button("Clear All Filters", id="training-clear-filters-btn", color="secondary", outline=True, className="mb-2"),
                width="auto"
            )
        ]),       
        dcc.Loading(
            id="training-loading-filters",
            type="cube",  # or "circle", "dot", "default"
            children=html.Div(get_filters_layout(), id="training-filters-container")
        ),    
        html.Br(),             
    ], fluid=True)
