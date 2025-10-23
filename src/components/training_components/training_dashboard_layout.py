
from dash import html, dcc
import dash_bootstrap_components as dbc
from src.components.training_components.filters import get_filters_layout

def create_training_dashboard_layout():
    return dbc.Container([
        dcc.Store(id="training-filtered-query-store"),
        # dcc.Store(id="training-filter-data-store"),    
        dcc.Store(id="training-aors-data-store"),
        dcc.Store(id="training-offices-data-store"),
        dcc.Store(id="training-topics-data-store"),
        dcc.Store(id="training-instructors-data-store"),
        dcc.Store(id="training-locations-data-store"),
        dcc.Store(id="training-classes-data-store"),
        html.H3("Training Dashboard (Under Development)"),  
        html.Hr(),
        dbc.Row([
            dbc.Col(
                dbc.Button("Clear All Filters", id="training-clear-filters-btn", color="secondary", outline=True, className="mb-2"),
                width="auto"
            )
        ]),        
        html.Div(get_filters_layout(), id="training-filters-container"),
        html.Br(),             
    ], fluid=True)
