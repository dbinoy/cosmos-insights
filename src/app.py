import os
from dotenv import load_dotenv

# Load environment-specific configuration BEFORE importing anything else
def load_environment():
    """Load environment configuration based on ENVIRONMENT variable"""
    environment = os.getenv('ENVIRONMENT', 'development')
    env_file = f'.env.{environment}'
    
    # Try to load environment-specific file first
    if os.path.exists(env_file):
        load_dotenv(env_file)
        print(f"✅ Loaded configuration from {env_file}")
    else:
        # Fallback to default .env
        load_dotenv()
        print("✅ Loaded default .env configuration")
    
    return environment

# Load environment first
current_env = load_environment()

from src.config.settings import config
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
        html.Div(
            dcc.Link(
                html.Img(
                    src="/assets/CRMLSLogoGreen.png",
                    style={"width": "140px", "margin": "24px auto 32px auto", "display": "block"}
                ),
                href="/"
            ),
            className="sidebar-logo"
        ), 
        dbc.Nav(
            [
                dbc.NavLink(
                    [
                        html.Span("Comply Dashboard", className="sidebar-label"),
                        html.I(className="bi bi-person-check sidebar-icon me-2", **{"aria-hidden": "true"}),
                        html.I(className="bi bi-chevron-right sidebar-arrow", **{"aria-hidden": "true"}),
                    ],
                    href="/compliance-dashboard",
                    active="exact",
                    className="text-light"
                ),
                dbc.NavLink(
                    [
                        html.Span("Assist Dashboard", className="sidebar-label"),                        
                        html.I(className="bi bi-heart sidebar-icon me-2", **{"aria-hidden": "true"}),
                        html.I(className="bi bi-chevron-right sidebar-arrow", **{"aria-hidden": "true"}),
                    ],
                    href="/workflow-dashboard",
                    active="exact",
                    className="text-light"
                ),
                dbc.NavLink(
                    [
                        html.Span("Instruct Dashboard", className="sidebar-label"),
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
    className="bg-dark vh-100 p-2 sidebar"
)

# Main content placeholder
content = dbc.Col(id="page-content", width=10, className="p-4 main-content")

# Register callbacks BEFORE defining layout
register_all_callbacks(app) 

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

# register_all_callbacks(app) 

# Run app
if __name__ == "__main__":
    print(f"🚀 Starting Cosmos Insights in {config.ENVIRONMENT} mode")
    print(f"📊 Performance monitoring: {'enabled' if config.ENABLE_PERFORMANCE_MONITORING else 'disabled'}")    
    app.run(host='0.0.0.0', port=8060, debug=config.IS_DEVELOPMENT)