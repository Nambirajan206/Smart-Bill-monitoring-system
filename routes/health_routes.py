from flask import jsonify
from models import db
import logging

logger = logging.getLogger(__name__)


def register_health_routes(app):
    
    @app.route('/', methods=['GET'])
    def home():
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
       
        try:
            db.session.execute('SELECT 1')
            
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
        return jsonify({
            "error": "Endpoint not found",
            "message": str(error),
            "status_code": 404
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        logger.error(f"Internal server error: {str(error)}")
        return jsonify({
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "status_code": 500
        }), 500