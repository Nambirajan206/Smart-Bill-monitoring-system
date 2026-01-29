"""
Health check and system status routes
"""
from flask import jsonify
from models import db
import logging

logger = logging.getLogger(__name__)


def register_health_routes(app):
    """Register health check and system status routes"""

    @app.route('/', methods=['GET'])
    def home():
        """Root endpoint with API information"""
        return jsonify({
            "status": "Backend is running successfully",
            "version": "1.0.0",
            "service": "Electricity Department - High Bill Monitoring System",
            "endpoints": {
                "Sync Excel from Google Drive": "POST /api/sync",
                "View Dashboard Data": "GET /api/dashboard",
                "Get Statistics": "GET /api/stats",
                "Clear All Data": "DELETE /api/clear",
                "Health Check": "GET /api/health"
            }
        })

    @app.route('/api/health', methods=['GET'])
    def health_check():
        """
        Health check endpoint
        Returns database connection status and system health
        """
        try:
            # Test database connection
            db.session.execute('SELECT 1')
            
            # Count total records
            from models import HighBill
            from sqlalchemy import func
            total_records = db.session.query(func.count(HighBill.id)).scalar()
            
            return jsonify({
                "status": "healthy",
                "database": "connected",
                "total_records": total_records,
                "message": "System is running smoothly"
            }), 200
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return jsonify({
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e)
            }), 500

    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors"""
        return jsonify({
            "error": "Endpoint not found",
            "message": str(error),
            "status_code": 404
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors"""
        db.session.rollback()
        logger.error(f"Internal server error: {str(error)}")
        return jsonify({
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "status_code": 500
        }), 500
