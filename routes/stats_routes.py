"""
Statistics and analytics routes
Handles statistical queries and data analysis
"""
from flask import jsonify, request
from models import db, HighBill
from sqlalchemy import func
import logging

logger = logging.getLogger(__name__)


def register_stats_routes(app):
    """Register statistics-related routes"""

    @app.route('/api/stats', methods=['GET'])
    def get_statistics():
        """
        Get comprehensive statistical summary of high bills
        
        Returns:
            JSON response with overall statistics and monthly breakdown
        """
        try:
            # Get total record count
            total_records = db.session.query(func.count(HighBill.id)).scalar()
            
            if total_records == 0:
                return jsonify({
                    "message": "No data available",
                    "total_records": 0,
                    "stats": {}
                }), 200

            # Get overall statistics
            stats = db.session.query(
                func.sum(HighBill.bill_amount).label('total_amount'),
                func.avg(HighBill.bill_amount).label('avg_amount'),
                func.max(HighBill.bill_amount).label('max_amount'),
                func.min(HighBill.bill_amount).label('min_amount'),
                func.sum(HighBill.units_consumed).label('total_units'),
                func.avg(HighBill.units_consumed).label('avg_units')
            ).first()

            # Get monthly breakdown
            monthly_stats = db.session.query(
                HighBill.month,
                func.count(HighBill.id).label('count'),
                func.sum(HighBill.bill_amount).label('total'),
                func.avg(HighBill.bill_amount).label('average'),
                func.max(HighBill.bill_amount).label('max')
            ).group_by(HighBill.month).all()

            # Build response
            response = {
                "total_records": total_records,
                "overall": {
                    "total_bill_amount": float(stats.total_amount or 0),
                    "average_bill_amount": float(stats.avg_amount or 0),
                    "max_bill_amount": float(stats.max_amount or 0),
                    "min_bill_amount": float(stats.min_amount or 0),
                    "total_units_consumed": int(stats.total_units or 0),
                    "average_units_consumed": float(stats.avg_units or 0)
                },
                "by_month": [
                    {
                        "month": month,
                        "count": count,
                        "total_amount": float(total),
                        "average_amount": float(average),
                        "max_amount": float(max_val)
                    }
                    for month, count, total, average, max_val in monthly_stats
                ]
            }

            logger.info(f"Statistics calculated for {total_records} records")

            return jsonify(response), 200

        except Exception as e:
            logger.error(f"Stats query failed: {str(e)}")
            return jsonify({
                "error": "Failed to fetch statistics",
                "details": str(e)
            }), 500

    @app.route('/api/stats/top', methods=['GET'])
    def get_top_bills():
        """
        Get top N highest bills
        
        Query Parameters:
            limit (int): Number of top bills to return (default: 10)
            
        Returns:
            JSON response with top bills
        """
        try:
            limit = request.args.get('limit', 10, type=int)
            
            # Ensure limit is reasonable
            if limit < 1:
                limit = 10
            elif limit > 100:
                limit = 100

            top_bills = HighBill.query.order_by(
                HighBill.bill_amount.desc()
            ).limit(limit).all()

            return jsonify({
                "count": len(top_bills),
                "limit": limit,
                "data": [bill.to_dict() for bill in top_bills]
            }), 200

        except Exception as e:
            logger.error(f"Top bills query failed: {str(e)}")
            return jsonify({
                "error": "Failed to fetch top bills",
                "details": str(e)
            }), 500

    @app.route('/api/stats/monthly/<month>', methods=['GET'])
    def get_monthly_stats(month):
        """
        Get statistics for a specific month
        
        Path Parameters:
            month (str): Month name (e.g., "January", "February")
            
        Returns:
            JSON response with month-specific statistics
        """
        try:
            # Check if month exists
            count = HighBill.query.filter_by(month=month).count()
            
            if count == 0:
                return jsonify({
                    "message": f"No data found for {month}",
                    "month": month,
                    "count": 0
                }), 404

            # Get statistics for the month
            stats = db.session.query(
                func.count(HighBill.id).label('count'),
                func.sum(HighBill.bill_amount).label('total'),
                func.avg(HighBill.bill_amount).label('average'),
                func.max(HighBill.bill_amount).label('max'),
                func.min(HighBill.bill_amount).label('min'),
                func.sum(HighBill.units_consumed).label('total_units')
            ).filter_by(month=month).first()

            # Get top 5 bills for the month
            top_bills = HighBill.query.filter_by(month=month).order_by(
                HighBill.bill_amount.desc()
            ).limit(5).all()

            response = {
                "month": month,
                "statistics": {
                    "total_records": stats.count,
                    "total_amount": float(stats.total or 0),
                    "average_amount": float(stats.average or 0),
                    "max_amount": float(stats.max or 0),
                    "min_amount": float(stats.min or 0),
                    "total_units": int(stats.total_units or 0)
                },
                "top_bills": [bill.to_dict() for bill in top_bills]
            }

            return jsonify(response), 200

        except Exception as e:
            logger.error(f"Monthly stats query failed: {str(e)}")
            return jsonify({
                "error": "Failed to fetch monthly statistics",
                "details": str(e)
            }), 500

    @app.route('/api/stats/summary', methods=['GET'])
    def get_quick_summary():
        """
        Get a quick summary of the data
        
        Returns:
            JSON response with quick summary statistics
        """
        try:
            total_records = db.session.query(func.count(HighBill.id)).scalar()
            
            if total_records == 0:
                return jsonify({
                    "total_records": 0,
                    "message": "No data available"
                }), 200

            # Quick aggregations
            total_amount = db.session.query(
                func.sum(HighBill.bill_amount)
            ).scalar()
            
            avg_amount = db.session.query(
                func.avg(HighBill.bill_amount)
            ).scalar()
            
            unique_houses = db.session.query(
                func.count(func.distinct(HighBill.house_id))
            ).scalar()
            
            unique_months = db.session.query(
                func.count(func.distinct(HighBill.month))
            ).scalar()

            return jsonify({
                "total_records": total_records,
                "total_amount": float(total_amount or 0),
                "average_amount": float(avg_amount or 0),
                "unique_houses": unique_houses,
                "unique_months": unique_months
            }), 200

        except Exception as e:
            logger.error(f"Summary query failed: {str(e)}")
            return jsonify({
                "error": "Failed to fetch summary",
                "details": str(e)
            }), 500
