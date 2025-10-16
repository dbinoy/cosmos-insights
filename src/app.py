import dash
from dash import html, dcc, Input, Output
import dash_bootstrap_components as dbc
from src.utils.cache import cache
from src.components.training_components.training_dashboard_layout import create_training_dashboard_layout
from src.components.workflow_components.workflow_dashboard_layout import create_workflow_dashboard_layout
from src.components.compliance_components.compliance_dashboard_layout import create_compliance_dashboard_layout
from src.components.welcome_layout import welcome_layout
from src.callbacks import register_all_callbacks


external_scripts = [
    "https://code.jquery.com/jquery-3.6.0.min.js",
    "https://code.jquery.com/ui/1.13.2/jquery-ui.min.js"
]


app = dash.Dash(
    __name__, 
    external_stylesheets=[ 
        dbc.themes.BOOTSTRAP,
        "https://code.jquery.com/ui/1.13.2/themes/base/jquery-ui.css",
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css"
    ], 
    external_scripts=external_scripts,
    suppress_callback_exceptions=True
)
app.title = "Cosmos Insights"
server = app.server
cache.init_app(server)

with server.app_context():
    cache.clear()

# Sidebar layout

sidebar = dbc.Col(
    [
        html.H2(
            html.A("Menu", href="/", className="text-light text-decoration-none"),
            className="mb-4"
        ),
        dbc.Nav(
            [
                dbc.NavLink(
                    [
                        html.Span("Compliance Dashboard", className="sidebar-label"),
                        html.I(className="bi bi-person-check sidebar-icon me-2", **{"aria-hidden": "true"}),
                        html.I(className="bi bi-chevron-right sidebar-arrow", **{"aria-hidden": "true"}),
                    ],
                    href="/compliance-dashboard",
                    active="exact",
                    className="text-light"
                ),
                dbc.NavLink(
                    [
                        html.Span("Workflow Dashboard", className="sidebar-label"),                        
                        html.I(className="bi bi-heart sidebar-icon me-2", **{"aria-hidden": "true"}),
                        html.I(className="bi bi-chevron-right sidebar-arrow", **{"aria-hidden": "true"}),
                    ],
                    href="/workflow-dashboard",
                    active="exact",
                    className="text-light"
                ),
                dbc.NavLink(
                    [
                        html.Span("Training Dashboard", className="sidebar-label"),
                        html.I(className="bi bi-mortarboard sidebar-icon me-2", **{"aria-hidden": "true"}),                        
                        html.I(className="bi bi-chevron-right sidebar-arrow", **{"aria-hidden": "true"}),
                    ],
                    href="/training-dashboard",
                    active="exact",
                    className="text-light"
                )

            ],
            vertical=True,
            pills=True,
            className="flex-column"
        ),
    ],
    width=2,
    className="bg-dark vh-100 p-3 sidebar"
)
# sidebar = dbc.Col(
#     [
#         html.H2(
#             html.A("Menu", href="/", className="text-light text-decoration-none"),
#             className="mb-4"
#         ),
#         dbc.Nav(
#             [
#                 dbc.NavLink(
#                     [   html.Span("Compliance Dashboard", className="sidebar-label"),
#                         html.I(className="bi bi-chevron-right sidebar-arrow"),
#                         html.I(className="bi bi-person-check sidebar-icon")
#                     ],
#                     href="/compliance-dashboard",
#                     active="exact",
#                     className="text-light"
#                 ),
#                 dbc.NavLink(
#                     [   html.Span("Workflow Dashboard", className="sidebar-label"),
#                         html.I(className="bi bi-chevron-right sidebar-arrow"),
#                         html.I(className="bi bi-heart sidebar-icon")
#                     ],
#                     href="/workflow-dashboard",
#                     active="exact",
#                     className="text-light"
#                 ), 
#                 dbc.NavLink(
#                     [   html.Span("Training Dashboard", className="sidebar-label"),
#                         html.I(className="bi bi-chevron-right sidebar-arrow"),
#                         html.I(className="bi bi-mortarboard sidebar-icon")
#                     ],
#                     href="/training-dashboard",
#                     active="exact",
#                     className="text-light"
#                 )                            
#             ],
#             vertical=True,
#             pills=True,
#             className="flex-column"
#         ),
#     ],
#     width=2,
#     className="bg-dark vh-100 p-3"
# )


# Main content placeholder
content = dbc.Col(id="page-content", width=10, className="p-4")

# App layout with URL routing
app.layout = dbc.Container(
    [
        dcc.Location(id="url"),
        dbc.Row([sidebar, content], className="gx-0"),
    ],
    fluid=True
)

#Routing callback
@app.callback(
    Output('page-content', 'children'),
    Input('url', 'pathname')
)
def display_page(pathname):
    if pathname == '/training-dashboard':
        return create_training_dashboard_layout()
    elif pathname == '/workflow-dashboard':
        return create_workflow_dashboard_layout()
    elif pathname == '/compliance-dashboard':
        return create_compliance_dashboard_layout()
    else:
        return welcome_layout()

register_all_callbacks(app) 

# Run app
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8060, debug=True)