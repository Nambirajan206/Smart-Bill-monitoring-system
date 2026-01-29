from flask import jsonify, request
from models import db, HighBill
from services.drive_service import download_excel_files
from services.processor import process_excel_files
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def register_routes(app):

    @app.route('/', methods=['GET'])
    def home():
        return jsonify({
            "status": "Backend is running successfully",
            "version": "1.0.0",
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
            return jsonify({
                "status": "healthy",
                "database": "connected"
            }), 200
        except Exception as e:
            return jsonify({
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e)
            }), 500

    @app.route('/api/sync', methods=['POST'])
    def sync_data():
        
        try:
            data = request.json
            folder_id = data.get('folder_id')

            if not folder_id:
                return jsonify({"error": "Folder ID is required"}), 400

            logger.info(f"Starting sync for folder: {folder_id}")

            excel_files = download_excel_files(folder_id)
            
            if not excel_files:
                return jsonify({"warning": "No Excel files found"}), 404

            all_high_bills = process_excel_files(excel_files)

            new_records_count = 0
            for item in all_high_bills:
                exists = HighBill.query.filter_by(
                    house_id=str(item['House_ID']),
                    month=str(item['Month'])
                ).first()

                if not exists:
                    bill = HighBill(
                        house_id=str(item['House_ID']),
                        owner_name=str(item.get('Owner_Name', 'N/A')),
                        address=str(item.get('Address', 'N/A')),
                        month=str(item['Month']),
                        units_consumed=int(item.get('Units_Consumed', 0)),
                        bill_amount=float(item['Bill_Amount'])
                    )
                    db.session.add(bill)
                    new_records_count += 1

            db.session.commit()
            return jsonify({
                "message": "Sync completed",
                "new_records": new_records_count
            }), 200

        except Exception as e:
            db.session.rollback()
            return jsonify({"error": "Sync failed", "details": str(e)}), 500

    @app.route('/api/dashboard', methods=['GET'])
    def get_dashboard_data():
        """Get all high-bill records for dashboard"""
        try:
            bills = HighBill.query.order_by(HighBill.bill_amount.desc()).all()
            return jsonify({
                "count": len(bills),
                "data": [bill.to_dict() for bill in bills]
            }), 200
        except Exception as e:
            return jsonify({"error": "Failed to fetch data", "details": str(e)}), 500

    @app.route('/api/stats', methods=['GET'])
    def get_statistics():
        """Get statistical summary"""
        try:
            from sqlalchemy import func
            total_records = db.session.query(func.count(HighBill.id)).scalar()
            
            if total_records == 0:
                return jsonify({"message": "No data", "stats": {}}), 200

            stats = db.session.query(
                func.sum(HighBill.bill_amount).label('total_amount'),
                func.avg(HighBill.bill_amount).label('avg_amount'),
                func.max(HighBill.bill_amount).label('max_amount'),
                func.sum(HighBill.units_consumed).label('total_units')
            ).first()

            return jsonify({
                "total_records": total_records,
                "overall": {
                    "total_bill_amount": float(stats.total_amount or 0),
                    "average_bill_amount": float(stats.avg_amount or 0),
                    "max_bill_amount": float(stats.max_amount or 0),
                    "total_units_consumed": int(stats.total_units or 0)
                }
            }), 200
        except Exception as e:
            return jsonify({"error": "Failed to fetch stats", "details": str(e)}), 500

    @app.route('/api/clear', methods=['DELETE'])
    def clear_data():
        try:
            num_rows_deleted = db.session.query(HighBill).delete()
            db.session.commit()
            logger.info("Database cleared by user.")
            return jsonify({
                "message": "Data cleared successfully",
                "records_removed": num_rows_deleted
            }), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": "Clear failed", "details": str(e)}), 500

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Endpoint not found"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({"error": "Internal server error"}), 500