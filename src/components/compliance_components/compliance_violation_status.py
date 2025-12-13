from dash import html, dcc
import dash_bootstrap_components as dbc

# def get_violation_status_layout():
#     return dbc.Card([
#         dbc.CardHeader([
#             dbc.Row([
#                 dbc.Col([
#                     html.H5("Current Violation Status", className="mb-0"),
#                     html.Small("Overview of compliance violations by status", className="text-muted")
#                 ], width=8),
#                 dbc.Col([
#                     dcc.Dropdown(
#                         id="compliance-violation-status-view-dropdown",
#                         options=[
#                             {"label": "By Status", "value": "status"},
#                             {"label": "By Severity", "value": "severity"},
#                             {"label": "By Priority", "value": "priority"}
#                         ],
#                         value="status",
#                         clearable=False,
#                         className="form-select-sm"
#                     )
#                 ], width=4)
#             ])
#         ]),
#         dbc.CardBody([
#             dcc.Loading([
#                 dcc.Graph(id="compliance-violation-status-chart")
#             ], type="dot")
#         ])
#     ], className="mb-4")


def get_violation_status_layout():
    return dbc.Card([
        dbc.CardHeader([
            dbc.Row([
                dbc.Col([
                    html.H5("Violation Status Overview", className="mb-0")
                ], width=6),
                dbc.Col([
                    dbc.ButtonGroup([
                        dbc.Button("Status", id="violation-status-view-btn", size="sm", outline=True, active=True),
                        dbc.Button("Disposition", id="violation-disposition-view-btn", size="sm", outline=True),
                        dbc.Button("Combined", id="violation-combined-view-btn", size="sm", outline=True)
                    ], size="sm")
                ], width=6, className="text-end")
            ])
        ]),
        dbc.CardBody([
            # Store for chart view state
            dcc.Store(id="compliance-violation-status-view-state", data="status"),
            
            # Chart wrapper for modal functionality
            html.Div(
                dcc.Graph(id="compliance-violation-status-chart"),
                id="compliance-violation-status-chart-wrapper",
                style={"cursor": "pointer"}
            ),
            
            html.Hr(),
            
            # Insights section
            html.Div(id="compliance-violation-status-insights", className="insights-container")
        ])
    ], className="mb-4 h-100")