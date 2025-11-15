from dash import html, dcc
import dash_bootstrap_components as dbc
from src.components.workflow_components.workflow_filters import get_filters_layout
from src.components.workflow_components.workflow_summary_cards import get_summary_cards_layout
from src.components.workflow_components.workflow_ticket_volume import get_ticket_volume_layout
from src.components.workflow_components.workflow_status_distribution import get_status_distribution_layout
from src.components.workflow_components.workflow_resolution_times import get_resolution_times_layout
from src.components.workflow_components.workflow_classification_analysis import get_classification_analysis_layout
from src.components.workflow_components.workflow_assignee_workload import get_assignee_workload_layout
from src.components.workflow_components.workflow_escalated_tickets import get_escalated_tickets_layout
from src.components.workflow_components.workflow_source_analysis import get_source_analysis_layout
from src.components.workflow_components.workflow_product_impact import get_product_impact_layout
from src.components.workflow_components.workflow_user_performance import get_user_performance_layout
from src.components.workflow_components.workflow_trends_analysis import get_trends_analysis_layout
from src.components.workflow_components.workflow_data_table import get_data_table_layout

def create_workflow_dashboard_layout():
    return dbc.Container([
        # Data stores
        dcc.Store(id="workflow-filtered-query-store"),

        dbc.Row([
            dbc.Col([
                html.H2("Workflow Dashboard (Under Construction)", className="mb-1"),
                html.P("Comprehensive insights into ticket management, performance tracking, and workload optimization", 
                      className="text-muted mb-3")
            ], width=8),
            dbc.Col([
                dbc.Button("Clear All Filters", 
                          id="workflow-clear-filters-btn", 
                          color="secondary", 
                          outline=True, 
                          className="mb-2")
            ], width=4, className="text-end")
        ]),

        # Filters Section
        html.Div(get_filters_layout(), id="workflow-filters-container"),
        html.Br(),

        # Summary Cards Section
        html.Div(get_summary_cards_layout(), id="workflow-summary-cards-container"),

        # Charts Section - Row 1: Volume & Status
        dbc.Row([
            dbc.Col([
                html.Div(get_ticket_volume_layout(), id="workflow-ticket-volume-container")
            ], width=6, lg=6),
            dbc.Col([
                html.Div(get_status_distribution_layout(), id="workflow-status-distribution-container")
            ], width=6, lg=6)
        ]),

        # Charts Section - Row 2: Resolution Times & Classification
        dbc.Row([
            dbc.Col([
                html.Div(get_resolution_times_layout(), id="workflow-resolution-times-container")
            ], width=6, lg=6),
            dbc.Col([
                html.Div(get_classification_analysis_layout(), id="workflow-classification-analysis-container")
            ], width=6, lg=6)
        ]),

        # Charts Section - Row 3: Workload & Escalations
        dbc.Row([
            dbc.Col([
                html.Div(get_assignee_workload_layout(), id="workflow-assignee-workload-container")
            ], width=6, lg=6),
            dbc.Col([
                html.Div(get_escalated_tickets_layout(), id="workflow-escalated-tickets-container")
            ], width=6, lg=6)
        ]),

        # Charts Section - Row 4: Source & Product Impact
        dbc.Row([
            dbc.Col([
                html.Div(get_source_analysis_layout(), id="workflow-source-analysis-container")
            ], width=6, lg=6),
            dbc.Col([
                html.Div(get_product_impact_layout(), id="workflow-product-impact-container")
            ], width=6, lg=6)
        ]),

        # Charts Section - Row 5: Performance & Trends
        dbc.Row([
            dbc.Col([
                html.Div(get_user_performance_layout(), id="workflow-user-performance-container")
            ], width=6, lg=6),
            dbc.Col([
                html.Div(get_trends_analysis_layout(), id="workflow-trends-analysis-container")
            ], width=6, lg=6)
        ]),

        # Data Table Section
        get_data_table_layout(),

        # Modal for enlarged chart view
        dbc.Modal(
            [
                dbc.ModalHeader([
                    html.H4("Enlarged Chart View", className="modal-title")
                ]),
                dbc.ModalBody(html.Div(id="workflow-modal-chart-content"))
            ],
            id="workflow-chart-modal",
            size="xl",
            is_open=False,
            centered=True,
            scrollable=True,
            backdrop="static",
            style={"padding": "0"},
            className="modal-90-viewport"
        )

    ], fluid=True)