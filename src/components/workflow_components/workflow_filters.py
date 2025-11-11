from dash import html
import dash_bootstrap_components as dbc

def get_filters_layout():
    return dbc.Card([
        dbc.CardBody([
            html.H5("Filters", className="card-title mb-3"),
            dbc.Row([
                # Date Range Filter
                dbc.Col([
                    html.Label("Date Range", className="form-label"),
                    dbc.Row([
                        dbc.Col([
                            html.Div(id="workflow-date-from-spinner", className="spinner-container"),
                            html.Div(id="workflow-date-from-dropdown-container")
                        ], width=6),
                        dbc.Col([
                            html.Div(id="workflow-date-to-spinner", className="spinner-container"),
                            html.Div(id="workflow-date-to-dropdown-container")
                        ], width=6)
                    ])
                ], width=12, md=3),

                # Status Filter
                dbc.Col([
                    html.Label("Status", className="form-label"),
                    html.Div(id="workflow-status-spinner", className="spinner-container"),
                    html.Div(id="workflow-status-dropdown-container")
                ], width=12, md=2),

                # Priority Filter
                dbc.Col([
                    html.Label("Priority", className="form-label"),
                    html.Div(id="workflow-priority-spinner", className="spinner-container"),
                    html.Div(id="workflow-priority-dropdown-container")
                ], width=12, md=2),

                # Product Filter
                dbc.Col([
                    html.Label("Product", className="form-label"),
                    html.Div(id="workflow-product-spinner", className="spinner-container"),
                    html.Div(id="workflow-product-dropdown-container")
                ], width=12, md=2),

                # Assignee Filter
                dbc.Col([
                    html.Label("Assignee", className="form-label"),
                    html.Div(id="workflow-assignee-spinner", className="spinner-container"),
                    html.Div(id="workflow-assignee-dropdown-container")
                ], width=12, md=2),

                # Case Origin Filter
                dbc.Col([
                    html.Label("Origin", className="form-label"),
                    html.Div(id="workflow-origin-spinner", className="spinner-container"),
                    html.Div(id="workflow-origin-dropdown-container")
                ], width=12, md=1)
            ])
        ])
    ], className="mb-4")