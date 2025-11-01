from dash import html, dcc
import dash_bootstrap_components as dbc
from src.components.training_components.training_filters import get_filters_layout
from src.components.training_components.training_summary_cards import get_summary_cards_layout
from src.components.training_components.training_engaged_members import get_engaged_members_layout
from src.components.training_components.training_office_engagement import get_office_engagement_layout
from src.components.training_components.training_session_scheduling import get_session_scheduling_layout
from src.components.training_components.training_gap_analysis import get_gap_analysis_layout
from src.components.training_components.training_instructor_performance import get_instructor_performance_layout
from src.components.training_components.training_data_table import get_data_table_layout

def create_training_dashboard_layout():
    return dbc.Container([
        # Include external JavaScript modules in correct order
        html.Script(src="/assets/js/core/cache-manager.js"),
        html.Script(src="/assets/js/core/data-manager.js"),
        html.Script(src="/assets/js/core/filter-utils.js"),
        
        # Training-specific modules (load after core modules)
        html.Script(src="/assets/js/training/training-filter-utils.js"),
        html.Script(src="/assets/js/training/training-data-manager.js"),
        html.Script(src="/assets/js/training/training-dropdown-handlers.js"),
        html.Script(src="/assets/js/training/training-summary-utils.js"),

        # Data stores
        dcc.Store(id="training-filtered-query-store"),
        dcc.Store(id="training-cache-check-store"),
        # dcc.Store(id="training-all-data-store"),
        dcc.Store(id="training-data-ready"),
        dcc.Store(id="training-filtered-data-store"),    

        dbc.Row([
            dbc.Col([
                html.H2("Training Dashboard (Under Development)", className="mb-1"),
                html.P("Comprehensive insights into training engagement, performance, and trends", 
                      className="text-muted mb-3")
            ], width=8),
            dbc.Col([
                dbc.Button("Clear All Filters", 
                          id="training-clear-filters-btn", 
                          color="secondary", 
                          outline=True, 
                          className="mb-2")
            ], width=4, className="text-end")
        ]),
        # Filters Section
        html.Div(get_filters_layout(), id="training-filters-container"),
        html.Br(),             

        # Summary Cards Section
        html.Div(get_summary_cards_layout(), id="training-summary-cards-container"),

        # Charts Section - Row 1
        dbc.Row([
            dbc.Col([
                html.Div(get_engaged_members_layout(), id="training-engaged-members-container")
            ], width=6, lg=6),
            dbc.Col([
                # get_office_engagement_layout()
                html.Div(get_office_engagement_layout(), id="training-office-engagement-container")
            ], width=6, lg=6)
        ]),
        
        # Charts Section - Row 2
        dbc.Row([
            dbc.Col([
                html.Div(get_session_scheduling_layout(), id="training-session-scheduling-container")
            ], width=12)
        ]),
        
        # Charts Section - Row 3
        dbc.Row([
            dbc.Col([
                html.Div(get_gap_analysis_layout(), id="training-gap-analysis-container")
            ], width=6, lg=6),
            dbc.Col([
                html.Div(get_instructor_performance_layout(), id="training-instructor-performance-container")
            ], width=6, lg=6)
        ]),
        
        # # Data Table Section
        get_data_table_layout(),

        # Modal for enlarged chart view 
        dbc.Modal(
            [
                dbc.ModalHeader([
                    html.H4("Enlarged Chart View", className="modal-title")
                ]),                
                dbc.ModalBody(html.Div(id="training-modal-chart-content"))
            ],
            id="training-chart-modal",
            size="xl",
            is_open=False,
            centered=True,
            scrollable=True,
            backdrop="static",
            style={"padding": "0"},
            className="modal-90-viewport"
        )     

    ], fluid=True)