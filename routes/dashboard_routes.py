"""
Dashboard routes
Handles retrieval and filtering of high-bill records for dashboard display
"""
from flask import jsonify, request
from models import db, HighBill
import logging

logger = logging.getLogger(__name__)


def register_dashboard_routes(app):
    """Register dashboard-related routes"""

    @app.route('/api/dashboard', methods=['GET'])
    def get_dashboard_data():
        """
        Get all high-bill records for dashboard
        
        Query Parameters:
            limit (int): Number of records to return (default: all)
            month (str): Filter by specific month
            sort_by (str): Column to sort by (default: bill_amount)
            order (str): Sort order - 'asc' or 'desc' (default: desc)
            
        Returns:
            JSON response with bill records
        """
        try:
            # Get query parameters
            limit = request.args.get('limit', type=int)
            month = request.args.get('month', type=str)
            sort_by = request.args.get('sort_by', 'bill_amount')
            order = request.args.get('order', 'desc')

            # Build query
            query = HighBill.query

            # Filter by month if provided
            if month:
                query = query.filter_by(month=month)

            # Sort by specified column
            if sort_by == 'bill_amount':
                sort_column = HighBill.bill_amount
            elif sort_by == 'units_consumed':
                sort_column = HighBill.units_consumed
            elif sort_by == 'month':
                sort_column = HighBill.month
            elif sort_by == 'house_id':
                sort_column = HighBill.house_id
            else:
                sort_column = HighBill.bill_amount

            # Apply sort order
            if order.lower() == 'asc':
                query = query.order_by(sort_column.asc())
            else:
                query = query.order_by(sort_column.desc())

            # Apply limit if provided
            if limit and limit > 0:
                query = query.limit(limit)

            # Execute query
            bills = query.all()

            logger.info(f"Dashboard query returned {len(bills)} records")

            return jsonify({
                "count": len(bills),
                "data": [bill.to_dict() for bill in bills],
                "filters": {
                    "month": month,
                    "sort_by": sort_by,
                    "order": order,
                    "limit": limit
                }
            }), 200

        except Exception as e:
            logger.error(f"Dashboard query failed: {str(e)}")
            return jsonify({
                "error": "Failed to fetch dashboard data",
                "details": str(e)
            }), 500

    @app.route('/api/dashboard/search', methods=['GET'])
    def search_bills():
        """
        Search bills by various criteria
        
        Query Parameters:
            q (str): Search term (searches across house_id, owner_name, address)
            min_amount (float): Minimum bill amount
            max_amount (float): Maximum bill amount
            
        Returns:
            JSON response with matching bill records
        """
        try:
            search_term = request.args.get('q', '').strip()
            min_amount = request.args.get('min_amount', type=float)
            max_amount = request.args.get('max_amount', type=float)

            query = HighBill.query

            # Text search across multiple fields
            if search_term:
                search_filter = db.or_(
                    HighBill.house_id.ilike(f'%{search_term}%'),
                    HighBill.owner_name.ilike(f'%{search_term}%'),
                    HighBill.address.ilike(f'%{search_term}%')
                )
                query = query.filter(search_filter)

            # Filter by amount range
            if min_amount is not None:
                query = query.filter(HighBill.bill_amount >= min_amount)
            if max_amount is not None:
                query = query.filter(HighBill.bill_amount <= max_amount)

            bills = query.order_by(HighBill.bill_amount.desc()).all()

            logger.info(f"Search query returned {len(bills)} results")

            return jsonify({
                "count": len(bills),
                "data": [bill.to_dict() for bill in bills],
                "search_criteria": {
                    "term": search_term,
                    "min_amount": min_amount,
                    "max_amount": max_amount
                }
            }), 200

        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            return jsonify({
                "error": "Search failed",
                "details": str(e)
            }), 500

    @app.route('/api/dashboard/months', methods=['GET'])
    def get_available_months():
        """
        Get list of all unique months in the database
        
        Returns:
            JSON response with list of months
        """
        try:
            from sqlalchemy import distinct

            months = db.session.query(distinct(HighBill.month)).all()
            month_list = [month[0] for month in months]

            return jsonify({
                "months": sorted(month_list),
                "count": len(month_list)
            }), 200

        except Exception as e:
            logger.error(f"Failed to fetch months: {str(e)}")
            return jsonify({
                "error": "Failed to fetch months",
                "details": str(e)
            }), 500
