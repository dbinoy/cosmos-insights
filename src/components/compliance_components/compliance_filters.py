from dash import html, dcc
import dash_bootstrap_components as dbc

def get_filters_layout():
    filters_layout = dbc.Card([
        dbc.CardBody([
            # First row of filters
            dbc.Row([
                # Date Range Filter
                dbc.Col([
                    html.Div([
                        html.Label("Date Range", className="form-label"),
                        dcc.DatePickerRange(
                            id="compliance-date-range-picker",
                            start_date_placeholder_text="Start Date",
                            end_date_placeholder_text="End Date",
                            display_format='YYYY-MM-DD',
                            style={'width': '100%'}
                        )
                    ], className="d-grid gap-1")
                ], width=4),
                
                # Case Disposition Filter
                dbc.Col([
                    html.Div([
                        html.Label("Case Disposition", className="form-label"),
                        dcc.Dropdown(
                            id="compliance-disposition-dropdown",
                            options=[],
                            placeholder="Loading Dispositions...",
                            multi=True,
                            disabled=False,
                            style={'width': '100%'}
                        ),
                        dbc.Spinner(
                            id="compliance-disposition-spinner",
                            size="sm",
                            color="primary",
                            spinner_style={"position": "relative", "top": "-30px", "right": "-30px"}
                        )
                    ], className="d-grid gap-1")
                ], width=4),
                
                # Assigned User Filter
                dbc.Col([
                    html.Div([
                        html.Label("Assigned Agent", className="form-label"),
                        dcc.Dropdown(
                            id="compliance-assigned-agent-dropdown",
                            options=[],
                            placeholder="Loading Assigned Agents...",
                            multi=True,
                            disabled=False,
                            style={'width': '100%'}
                        ),
                        dbc.Spinner(
                            id="compliance-assigned-agent-spinner",
                            size="sm",
                            color="primary",
                            spinner_style={"position": "relative", "top": "-30px", "right": "-30px"}
                        )
                    ], className="d-grid gap-1")
                ], width=4)
            ], className="mb-2"),
            
            # Second row of filters
            dbc.Row([
                # Rule Number Filter
                dbc.Col([
                    html.Div([
                        html.Label("Rule Numbers", className="form-label"),
                        dcc.Dropdown(
                            id="compliance-rule-number-dropdown",
                            options=[],
                            placeholder="Loading Rule Numbers...",
                            multi=True,
                            disabled=False,
                            style={'width': '100%'}
                        ),
                        dbc.Spinner(
                            id="compliance-rule-number-spinner",
                            size="sm",
                            color="primary",
                            spinner_style={"position": "relative", "top": "-30px", "right": "-30px"}
                        )
                    ], className="d-grid gap-1")
                ], width=4),
                
                # Rule Title Filter (searchable, next to Rule Numbers)
                dbc.Col([
                    html.Div([
                        html.Label("Rule Title", className="form-label"),
                        dcc.Dropdown(
                            id="compliance-rule-title-dropdown",
                            options=[],
                            placeholder="Loading Rule Titles...",
                            multi=True,
                            searchable=True,
                            disabled=False,
                            style={'width': '100%'}
                        ),
                        dbc.Spinner(
                            id="compliance-rule-title-spinner",
                            size="sm",
                            color="primary",
                            spinner_style={"position": "relative", "top": "-30px", "right": "-30px"}
                        )
                    ], className="d-grid gap-1")
                ], width=8)
                
            ], className="mb-2"),

            # Third row - Clear Filters Button
            dbc.Row([
                # Violation Name Filter
                dbc.Col([
                    html.Div([
                        html.Label("Violation Names", className="form-label"),
                        dcc.Dropdown(
                            id="compliance-violation-name-dropdown",
                            options=[],
                            placeholder="Loading Violation Names...",
                            multi=True,
                            disabled=False,
                            style={'width': '100%'}
                        ),
                        dbc.Spinner(
                            id="compliance-violation-name-spinner",
                            size="sm",
                            color="primary",
                            spinner_style={"position": "relative", "top": "-30px", "right": "-30px"}
                        )
                    ], className="d-grid gap-1")
                ], width=4),

                # Fine Type Filter
                dbc.Col([
                    html.Div([
                        html.Label("Fine Type", className="form-label"),
                        dcc.Dropdown(
                            id="compliance-fine-type-dropdown",
                            options=[],
                            placeholder="Loading Fine Types...",
                            multi=True,
                            disabled=False,
                            style={'width': '100%'}
                        ),
                        dbc.Spinner(
                            id="compliance-fine-type-spinner",
                            size="sm",
                            color="primary",
                            spinner_style={"position": "relative", "top": "-30px", "right": "-30px"}
                        )
                    ], className="d-grid gap-1")
                ], width=2),
                
                # Citation Fee Filter
                dbc.Col([
                    html.Div([
                        html.Label("Citation Fee", className="form-label"),
                        dcc.Dropdown(
                            id="compliance-citation-fee-dropdown",
                            options=[],
                            placeholder="Loading Citation Fees...",
                            multi=True,
                            disabled=False,
                            style={'width': '100%'}
                        ),
                        dbc.Spinner(
                            id="compliance-citation-fee-spinner",
                            size="sm",
                            color="primary",
                            spinner_style={"position": "relative", "top": "-30px", "right": "-30px"}
                        )
                    ], className="d-grid gap-1")
                ], width=3),
                
                # Associated Reports Filter
                dbc.Col([
                    html.Div([
                        html.Label("Associated Reports", className="form-label"),
                        dcc.Dropdown(
                            id="compliance-num-reports-dropdown",
                            options=[],
                            placeholder="Loading Report Counts...",
                            multi=True,
                            disabled=False,
                            style={'width': '100%'}
                        ),
                        dbc.Spinner(
                            id="compliance-num-reports-spinner",
                            size="sm",
                            color="primary",
                            spinner_style={"position": "relative", "top": "-30px", "right": "-30px"}
                        )
                    ], className="d-grid gap-1")
                ], width=3)
            ])
        ])
    ], className="mb-4")
    return filters_layout