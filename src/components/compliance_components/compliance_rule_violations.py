from dash import html, dcc
import dash_bootstrap_components as dbc

def get_rule_violations_layout():
    return dbc.Card([
        dbc.CardHeader([
            dbc.Row([
                dbc.Col([
                    html.H5("Rule Violations", className="mb-0"),
                    html.Small("Most commonly violated rules and regulations", className="text-muted")
                ], width=6),
                dbc.Col([
                    dcc.Dropdown(
                        id="compliance-rule-count-dropdown",
                        options=[
                            {"label": "Top 10", "value": 10},
                            {"label": "Top 20", "value": 20},
                            {"label": "All Rules", "value": "all"}
                        ],
                        value=10,
                        clearable=False,
                        className="form-select-sm"
                    )
                ], width=3),
                dbc.Col([
                    dcc.Dropdown(
                        id="compliance-rule-metric-dropdown",
                        options=[
                            {"label": "Violation Count", "value": "count"},
                            {"label": "Total Fines", "value": "fines"},
                            {"label": "Avg Resolution", "value": "resolution"},
                            {"label": "Repeat Offenses", "value": "repeat"}
                        ],
                        value="count",
                        clearable=False,
                        className="form-select-sm"
                    )
                ], width=3)
            ])
        ]),
        dbc.CardBody([
            dcc.Loading([
                dcc.Graph(id="compliance-rule-violations-chart")
            ], type="dot")
        ])
    ], className="mb-4")