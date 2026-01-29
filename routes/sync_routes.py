from flask import jsonify, request
from models import db, HighBill
from services.drive_service import download_excel_files
from services.processor import process_excel_files
import logging

logger = logging.getLogger(__name__)


def register_sync_routes(app):

    @app.route('/api/sync', methods=['POST'])
    def sync_data():
        
        try:
            data = request.json if request.json else {}
            folder_id = data.get('folder_id') or app.config.get('GOOGLE_DRIVE_FOLDER_ID')

            if not folder_id:
                return jsonify({
                    "error": "Folder ID not configured",
                    "message": "Please set GOOGLE_DRIVE_FOLDER_ID in your .env file or provide folder_id in the request",
                    "example": {"folder_id": "1ABC123xyz"}
                }), 400

            logger.info(f"Starting sync for folder: {folder_id}")

            excel_files = download_excel_files(folder_id)
            
            if not excel_files:
                return jsonify({
                    "warning": "No Excel files found in the specified folder",
                    "folder_id": folder_id,
                    "message": "Please ensure the folder contains .xlsx or .xls files"
                }), 404

            logger.info(f"Found {len(excel_files)} Excel file(s) to process")

            all_high_bills = process_excel_files(excel_files)

            logger.info(f"Filtered {len(all_high_bills)} high-bill records from all files")

            new_records_count = 0
            duplicate_count = 0
            errors = []

            for item in all_high_bills:
                try:
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
                    else:
                        duplicate_count += 1

                except Exception as e:
                    error_msg = f"Error processing record {item.get('House_ID')}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)

            db.session.commit()
            logger.info(f"Successfully committed {new_records_count} new records")

            response = {
                "message": "Sync completed successfully",
                "summary": {
                    "files_processed": len(excel_files),
                    "total_high_bills_found": len(all_high_bills),
                    "new_records_added": new_records_count,
                    "duplicates_skipped": duplicate_count
                },
                "status": "success"
            }

            if errors:
                response["errors"] = errors[:10]  # Limit to first 10 errors
                response["warning"] = f"{len(errors)} records had processing errors"

            return jsonify(response), 200

        except Exception as e:
            db.session.rollback()
            logger.error(f"Sync failed: {str(e)}")
            return jsonify({
                "error": "Sync failed",
                "details": str(e),
                "status": "failed"
            }), 500

    @app.route('/api/clear', methods=['DELETE'])
    def clear_data():
        
        try:
            num_rows_deleted = db.session.query(HighBill).delete()
            db.session.commit()
            
            logger.info(f"Database cleared: {num_rows_deleted} records removed")
            
            return jsonify({
                "message": "Data cleared successfully",
                "records_removed": num_rows_deleted,
                "status": "success"
            }), 200
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Clear operation failed: {str(e)}")
            return jsonify({
                "error": "Clear failed",
                "details": str(e),
                "status": "failed"
            }), 500