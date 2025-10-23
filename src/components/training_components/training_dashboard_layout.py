from dash import html, dcc
import dash_bootstrap_components as dbc
from src.components.training_components.filters import get_filters_layout

def create_training_dashboard_layout():
    return dbc.Container([
        # Include external JavaScript modules in correct order
        html.Script(src="/assets/js/core/cache-manager.js"),
        html.Script(src="/assets/js/core/data-manager.js"),
        html.Script(src="/assets/js/core/filter-utils.js"),
        
        # Training-specific modules (load after core modules)
        html.Script(src="/assets/js/training/training-data-manager.js"),
        html.Script(src="/assets/js/training/training-dropdown-handlers.js"),

        # Data stores
        dcc.Store(id="training-filtered-query-store"),
        dcc.Store(id="training-all-data-store"),
        dcc.Store(id="training-data-ready"),

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