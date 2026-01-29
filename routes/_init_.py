from .sync_routes import register_sync_routes
from .dashboard_routes import register_dashboard_routes
from .stats_routes import register_stats_routes
from .health_routes import register_health_routes


def register_routes(app):
    register_health_routes(app)
    register_sync_routes(app)
    register_dashboard_routes(app)
    register_stats_routes(app)