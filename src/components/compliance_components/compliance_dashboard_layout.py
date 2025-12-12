from dash import html, dcc
import dash_bootstrap_components as dbc
from src.components.compliance_components.compliance_filters import get_filters_layout
from src.components.compliance_components.compliance_summary_cards import get_summary_cards_layout
from src.components.compliance_components.compliance_violation_status import get_violation_status_layout
from src.components.compliance_components.compliance_outstanding_issues import get_outstanding_issues_layout
from src.components.compliance_components.compliance_recent_activities import get_recent_activities_layout
from src.components.compliance_components.compliance_agent_performance import get_agent_performance_layout
from src.components.compliance_components.compliance_violation_trends import get_violation_trends_layout
from src.components.compliance_components.compliance_incident_analysis import get_incident_analysis_layout
from src.components.compliance_components.compliance_resolution_metrics import get_resolution_metrics_layout
from src.components.compliance_components.compliance_rule_violations import get_rule_violations_layout
from src.components.compliance_components.compliance_office_performance import get_office_performance_layout
from src.components.compliance_components.compliance_risk_assessment import get_risk_assessment_layout
from src.components.compliance_components.compliance_data_table import get_data_table_layout

def create_compliance_dashboard_layout():
    return dbc.Container([
        # Data stores
        dcc.Store(id="compliance-filtered-query-store"),

        dbc.Row([
            dbc.Col([
                html.H2("Compliance Dashboard (Under Construction)", className="mb-1"),
                html.P("Comprehensive insights into compliance reporting, investigations of violations and case management", 
                      className="text-muted mb-3")
            ], width=9),
            dbc.Col([
                dbc.Button("Clear All Filters", 
                          id="compliance-clear-filters-btn", 
                          color="secondary", 
                          outline=True, 
                          className="mb-2")
            ], width=3, className="text-end")
        ]),

        # Filters Section
        html.Div(get_filters_layout(), id="compliance-filters-container"),
        html.Br(),

        # Summary Cards Section
        html.Div(get_summary_cards_layout(), id="compliance-summary-cards-container"),

        # Charts Section - Row 1: Status Overview & Outstanding Issues
        dbc.Row([
            dbc.Col([
                html.Div(get_violation_status_layout(), id="compliance-violation-status-container")
            ], width=6, lg=6),
            dbc.Col([
                html.Div(get_outstanding_issues_layout(), id="compliance-outstanding-issues-container")
            ], width=6, lg=6)
        ]),

        # Charts Section - Row 2: Recent Activities & Agent Performance
        dbc.Row([
            dbc.Col([
                html.Div(get_recent_activities_layout(), id="compliance-recent-activities-container")
            ], width=6, lg=6),
            dbc.Col([
                html.Div(get_agent_performance_layout(), id="compliance-agent-performance-container")
            ], width=6, lg=6)
        ]),

        # Charts Section - Row 3: Violation Trends & Incident Analysis
        dbc.Row([
            dbc.Col([
                html.Div(get_violation_trends_layout(), id="compliance-violation-trends-container")
            ], width=6, lg=6),
            dbc.Col([
                html.Div(get_incident_analysis_layout(), id="compliance-incident-analysis-container")
            ], width=6, lg=6)
        ]),

        # Charts Section - Row 4: Resolution Metrics & Rule Violations
        dbc.Row([
            dbc.Col([
                html.Div(get_resolution_metrics_layout(), id="compliance-resolution-metrics-container")
            ], width=6, lg=6),
            dbc.Col([
                html.Div(get_rule_violations_layout(), id="compliance-rule-violations-container")
            ], width=6, lg=6)
        ]),

        # Charts Section - Row 5: Office Performance & Risk Assessment
        dbc.Row([
            dbc.Col([
                html.Div(get_office_performance_layout(), id="compliance-office-performance-container")
            ], width=6, lg=6),
            dbc.Col([
                html.Div(get_risk_assessment_layout(), id="compliance-risk-assessment-container")
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
                dbc.ModalBody(html.Div(id="compliance-modal-chart-content"))
            ],
            id="compliance-chart-modal",
            size="xl",
            is_open=False,
            centered=True,
            scrollable=True,
            backdrop="static",
            style={"padding": "0"},
            className="modal-90-viewport"
        )

    ], fluid=True)