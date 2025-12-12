from dash import html, dcc
import dash_bootstrap_components as dbc

def get_filters_layout():
    filters_layout = dbc.Card([
        dbc.CardBody([
            # First row of filters
            dbc.Row([
                # Date Range Filter
                dbc.Col([
                    html.Label("Date Range", className="form-label"),
                    dcc.DatePickerRange(
                        id="compliance-date-range-picker",
                        start_date_placeholder_text="Start Date",
                        end_date_placeholder_text="End Date",
                        display_format='YYYY-MM-DD',
                        style={'width': '100%'}
                    )
                ], width=4),
                
                # Case Disposition Filter
                dbc.Col([
                    html.Label("Case Disposition", className="form-label"),
                    dcc.Dropdown(
                        id="compliance-disposition-dropdown",
                        placeholder="Select Disposition...",
                        multi=True,
                        style={'width': '100%'}
                    )
                ], width=2),
                
                # Assigned User Filter
                dbc.Col([
                    html.Label("Assigned User", className="form-label"),
                    dcc.Dropdown(
                        id="compliance-assigned-user-dropdown",
                        placeholder="Select Assigned User...",
                        multi=True,
                        style={'width': '100%'}
                    )
                ], width=3),
                
                # Violation Name Filter
                dbc.Col([
                    html.Label("Violation Names", className="form-label"),
                    dcc.Dropdown(
                        id="compliance-violation-name-dropdown",
                        placeholder="Select Violation Names...",
                        multi=True,
                        style={'width': '100%'}
                    )
                ], width=3)
            ]),
            
            # Second row of filters
            dbc.Row([
                # Rule Number Filter
                dbc.Col([
                    html.Label("Rule Numbers", className="form-label"),
                    dcc.Dropdown(
                        id="compliance-rule-number-dropdown",
                        placeholder="Select Rule Numbers...",
                        multi=True,
                        style={'width': '100%'}
                    )
                ], width=2),
                
                # Rule Title Filter (searchable, next to Rule Numbers)
                dbc.Col([
                    html.Label("Rule Title", className="form-label"),
                    dcc.Dropdown(
                        id="compliance-rule-title-dropdown",
                        placeholder="Select Rule Title...",
                        multi=True,
                        searchable=True,
                        style={'width': '100%'}
                    )
                ], width=5),
                
                # Fine Type Filter
                dbc.Col([
                    html.Label("Fine", className="form-label"),
                    dcc.Dropdown(
                        id="compliance-fine-type-dropdown",
                        placeholder="Fine...",
                        multi=True,
                        style={'width': '100%'}
                    )
                ], width=1),
                
                # Citation Fee Filter
                dbc.Col([
                    html.Label("Citation Fee", className="form-label"),
                    dcc.Dropdown(
                        id="compliance-citation-fee-dropdown",
                        placeholder="Select Citation Fee...",
                        multi=True,
                        style={'width': '100%'}
                    )
                ], width=2),
                
                # Associated Reports Filter
                dbc.Col([
                    html.Label("Associated Reports", className="form-label"),
                    dcc.Dropdown(
                        id="compliance-num-reports-dropdown",
                        placeholder="Select Number of Reports...",
                        multi=True,
                        style={'width': '100%'}
                    )
                ], width=2)
            ], className="mt-3")
        ])
    ], className="mb-4")
    return filters_layout