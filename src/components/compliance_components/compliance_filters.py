from dash import html, dcc
import dash_bootstrap_components as dbc

def get_filters_layout():
    return dbc.Card([
        dbc.CardHeader([
            html.H5("Filters", className="mb-0"),
            html.Small("Filter compliance data by various criteria", className="text-muted")
        ]),
        dbc.CardBody([
            dbc.Row([
                # Date Range Filter
                dbc.Col([
                    html.Label("Date Range:", className="form-label"),
                    dcc.DatePickerRange(
                        id="compliance-date-range-picker",
                        start_date_placeholder_text="Start Date",
                        end_date_placeholder_text="End Date",
                        display_format='YYYY-MM-DD',
                        style={'width': '100%'}
                    )
                ], width=12, lg=3),
                
                # Case Status Filter
                dbc.Col([
                    html.Label("Case Status:", className="form-label"),
                    dcc.Dropdown(
                        id="compliance-status-dropdown",
                        placeholder="Select Status...",
                        multi=True,
                        style={'width': '100%'}
                    )
                ], width=12, lg=2),
                
                # Member/Agent Filter
                dbc.Col([
                    html.Label("Members:", className="form-label"),
                    dcc.Dropdown(
                        id="compliance-members-dropdown",
                        placeholder="Select Members...",
                        multi=True,
                        style={'width': '100%'}
                    )
                ], width=12, lg=2),
                
                # Office Filter
                dbc.Col([
                    html.Label("Offices:", className="form-label"),
                    dcc.Dropdown(
                        id="compliance-offices-dropdown",
                        placeholder="Select Offices...",
                        multi=True,
                        style={'width': '100%'}
                    )
                ], width=12, lg=2),
                
                # Violation Category Filter
                dbc.Col([
                    html.Label("Violation Categories:", className="form-label"),
                    dcc.Dropdown(
                        id="compliance-categories-dropdown",
                        placeholder="Select Categories...",
                        multi=True,
                        style={'width': '100%'}
                    )
                ], width=12, lg=2),
                
                # Rule Number Filter
                dbc.Col([
                    html.Label("Rule Numbers:", className="form-label"),
                    dcc.Dropdown(
                        id="compliance-rules-dropdown",
                        placeholder="Select Rules...",
                        multi=True,
                        style={'width': '100%'}
                    )
                ], width=12, lg=1)
            ])
        ])
    ], className="mb-4")