from flask import jsonify, request
from models import db, HighBill
import logging

logger = logging.getLogger(__name__)


def register_dashboard_routes(app):
    

    @app.route('/api/dashboard', methods=['GET'])
    def get_dashboard_data():
        
        try:
            
            limit = request.args.get('limit', type=int)
            month = request.args.get('month', type=str)
            sort_by = request.args.get('sort_by', 'bill_amount')
            order = request.args.get('order', 'desc')

           
            query = HighBill.query

            
            if month:
                query = query.filter_by(month=month)

           
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

            
            if order.lower() == 'asc':
                query = query.order_by(sort_column.asc())
            else:
                query = query.order_by(sort_column.desc())

            
            if limit and limit > 0:
                query = query.limit(limit)

            
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
        
        try:
            search_term = request.args.get('q', '').strip()
            min_amount = request.args.get('min_amount', type=float)
            max_amount = request.args.get('max_amount', type=float)

            query = HighBill.query

           
            if search_term:
                search_filter = db.or_(
                    HighBill.house_id.ilike(f'%{search_term}%'),
                    HighBill.owner_name.ilike(f'%{search_term}%'),
                    HighBill.address.ilike(f'%{search_term}%')
                )
                query = query.filter(search_filter)

            
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