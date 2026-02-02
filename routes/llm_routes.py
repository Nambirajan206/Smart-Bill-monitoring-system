from flask import jsonify, request
from werkzeug.utils import secure_filename
import pandas as pd
import io
import logging
import os

logger = logging.getLogger(__name__)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def convert_wide_to_long(df):
    """
    Convert wide format (12 months in columns) to long format (each row is one month)
    
    Wide format example:
    House_ID | Jan_bill | Jan_units | Feb_bill | Feb_units | ...
    
    Long format example:
    House_ID | Month | Bill_Amount | Units_Consumed
    """
    # Identify house identifier column
    id_columns = [col for col in df.columns if any(x in col.lower() for x in ['house_id', 'house', 'id', 's.no', 'sno'])]
    address_columns = [col for col in df.columns if 'address' in col.lower()]
    
    # Use House_ID or first identifier column
    house_id_col = None
    for col in df.columns:
        if col.lower() in ['house_id', 'houseid', 'house']:
            house_id_col = col
            break
    if not house_id_col:
        house_id_col = id_columns[0] if id_columns else df.columns[1]  # Skip S.No if present
    
    # Find all month columns
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    records = []
    
    for _, row in df.iterrows():
        house_id = row[house_id_col]
        address = row[address_columns[0]] if address_columns else str(house_id)
        
        for month in months:
            # Look for bill and units columns for this month
            bill_col = None
            units_col = None
            
            for col in df.columns:
                col_lower = col.lower()
                if month.lower() in col_lower:
                    if 'bill' in col_lower or 'amount' in col_lower:
                        bill_col = col
                    elif 'unit' in col_lower:
                        units_col = col
            
            if bill_col and pd.notna(row[bill_col]):
                bill_amount = row[bill_col]
                units_consumed = row[units_col] if units_col and pd.notna(row[units_col]) else 0
                
                records.append({
                    'house_id': str(house_id),
                    'address': str(address),
                    'month': month,
                    'bill_amount': float(bill_amount),
                    'units_consumed': int(units_consumed)
                })
    
    return pd.DataFrame(records)


def register_llm_routes(app):
    
    @app.route('/api/llm/analyze', methods=['POST'])
    def analyze_with_llm():
        """
        Analyze uploaded Excel/CSV file with LLM
        Expects multipart/form-data with 'file' field
        """
        try:
            # Check if file is present
            if 'file' not in request.files:
                return jsonify({
                    "error": "No file uploaded",
                    "message": "Please upload an Excel or CSV file"
                }), 400
            
            file = request.files['file']
            
            # Check if file has a name
            if file.filename == '':
                return jsonify({
                    "error": "No file selected",
                    "message": "Please select a file to upload"
                }), 400
            
            # Validate file extension
            if not allowed_file(file.filename):
                return jsonify({
                    "error": "Invalid file type",
                    "message": "Only .xlsx, .xls, and .csv files are allowed"
                }), 400
            
            filename = secure_filename(file.filename)
            logger.info(f"Processing file: {filename}")
            
            # Read file content
            file_content = file.read()
            
            # Process the file and extract data
            analysis_data = process_file_for_analysis(file_content, filename)
            
            if "error" in analysis_data:
                return jsonify(analysis_data), 400
            
            # Generate initial AI analysis
            from services.llm_service import generate_initial_analysis
            
            initial_analysis = generate_initial_analysis(analysis_data)
            
            return jsonify({
                "status": "success",
                "filename": filename,
                "summary": analysis_data["summary"],
                "analysis": initial_analysis,
                "anomalies": analysis_data["anomalies"],
                "data_hash": analysis_data.get("data_hash", "")  # For session tracking
            }), 200
            
        except Exception as e:
            logger.error(f"LLM analysis failed: {str(e)}")
            return jsonify({
                "error": "Analysis failed",
                "details": str(e)
            }), 500
    
    @app.route('/api/llm/chat', methods=['POST'])
    def chat_with_llm():
        """
        Chat endpoint for follow-up questions about analyzed data
        Expects JSON: { "question": "...", "context": {...} }
        """
        try:
            data = request.json
            
            if not data or 'question' not in data:
                return jsonify({
                    "error": "Missing question",
                    "message": "Please provide a question in the request body"
                }), 400
            
            question = data.get('question', '').strip()
            context = data.get('context', {})
            
            if not question:
                return jsonify({
                    "error": "Empty question",
                    "message": "Question cannot be empty"
                }), 400
            
            logger.info(f"Processing question: {question}")
            
            # Generate response using LLM
            from services.llm_service import answer_question
            
            response = answer_question(question, context)
            
            return jsonify({
                "status": "success",
                "question": question,
                "answer": response
            }), 200
            
        except Exception as e:
            logger.error(f"Chat failed: {str(e)}")
            return jsonify({
                "error": "Failed to process question",
                "details": str(e)
            }), 500


def process_file_for_analysis(file_content, filename):
    """
    Process uploaded file and prepare data for LLM analysis
    Handles both wide format (12 months in columns) and long format (each row is a month)
    """
    try:
        # Read file based on extension
        file_ext = filename.rsplit('.', 1)[1].lower()
        
        if file_ext == 'csv':
            df = pd.read_csv(io.BytesIO(file_content))
        else:  # xlsx or xls
            df = pd.read_excel(io.BytesIO(file_content))
        
        logger.info(f"File loaded: {len(df)} records, {len(df.columns)} columns")
        logger.info(f"Original columns: {list(df.columns)}")
        
        # Normalize column names
        df.columns = df.columns.str.strip().str.replace(' ', '_')
        
        # Detect if this is wide format (12 months in columns)
        month_columns = [col for col in df.columns if any(month in col.lower() for month in 
                        ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'])]
        
        if len(month_columns) >= 12:
            # Convert wide format to long format
            logger.info("Detected wide format (12 months in columns). Converting to long format...")
            df = convert_wide_to_long(df)
            logger.info(f"Converted to long format: {len(df)} records")
        
        # Now work with long format data
        # Map common column variations
        column_mapping = {
            'house_id': ['House_ID', 'HouseID', 'House_Id', 'house_id', 'ID', 'id'],
            'owner_name': ['Owner_Name', 'OwnerName', 'Owner', 'owner_name', 'Name'],
            'bill_amount': ['Bill_Amount', 'BillAmount', 'Amount', 'bill_amount', 'Bill', 'bill'],
            'units_consumed': ['Units_Consumed', 'UnitsConsumed', 'Units', 'units_consumed', 'units'],
            'month': ['Month', 'month', 'Billing_Month', 'Period'],
            'category': ['Category', 'category', 'Type', 'Usage_Type', 'Residential_Commercial'],
            'address': ['Address', 'address', 'Location']
        }
        
        # Rename columns
        for standard_name, variations in column_mapping.items():
            for col in df.columns:
                if col in variations:
                    df.rename(columns={col: standard_name}, inplace=True)
                    break
        
        logger.info(f"Normalized columns: {list(df.columns)}")
        
        # Check for required columns
        required_cols = ['house_id', 'bill_amount']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            return {
                "error": "Missing required columns",
                "message": f"The file must contain: {', '.join(required_cols)}",
                "found_columns": list(df.columns),
                "missing": missing_cols
            }
        
        # Clean data
        df = df.dropna(subset=['house_id', 'bill_amount'])
        
        # Convert to numeric
        df['bill_amount'] = pd.to_numeric(df['bill_amount'], errors='coerce')
        
        if 'units_consumed' in df.columns:
            df['units_consumed'] = pd.to_numeric(df['units_consumed'], errors='coerce').fillna(0)
        else:
            df['units_consumed'] = 0
        
        # Drop rows with invalid bill amounts
        df = df.dropna(subset=['bill_amount'])
        
        # Detect category if not present (Commercial vs Residential)
        if 'category' not in df.columns:
            # Commercial keywords to look for in house_id or address
            commercial_keywords = ['shop', 'store', 'market', 'stall', 'boutique', 'baker', 'bakery', 
                                  'electronics', 'mobile', 'hardware', 'gift', 'grocery', 'tea', 'fruit',
                                  'corner', 'corp', 'ltd', 'pharmacy', 'medical', 'clinic', 'salon',
                                  'restaurant', 'cafe', 'hotel', 'business', 'office', 'workshop']
            
            def is_commercial(row):
                # Check house_id field first (this is where shop names are in your file)
                house_id_text = str(row.get('house_id', '')).lower()
                if any(keyword in house_id_text for keyword in commercial_keywords):
                    return 'Commercial'
                
                # Check address field
                if 'address' in df.columns:
                    address_text = str(row.get('address', '')).lower()
                    if any(keyword in address_text for keyword in commercial_keywords):
                        return 'Commercial'
                
                # Default to residential
                return 'Residential'
            
            df['category'] = df.apply(is_commercial, axis=1)
        else:
            # Normalize category values
            df['category'] = df['category'].str.strip().str.title()
            df['category'] = df['category'].apply(
                lambda x: 'Residential' if x in ['Residential', 'Res', 'R'] 
                else 'Commercial' if x in ['Commercial', 'Com', 'C'] 
                else 'Residential'
            )
        
        logger.info(f"Category distribution: {df['category'].value_counts().to_dict()}")
        
        # Separate residential and commercial
        residential_df = df[df['category'] == 'Residential'].copy()
        commercial_df = df[df['category'] == 'Commercial'].copy()
        
        # Define thresholds for residential
        RESIDENTIAL_MIN = 500
        RESIDENTIAL_MAX = 5000
        
        # Find anomalies in residential only
        residential_anomalies = []
        
        for _, row in residential_df.iterrows():
            bill_amt = row['bill_amount']
            house_id = row['house_id']
            
            if bill_amt < RESIDENTIAL_MIN:
                residential_anomalies.append({
                    "house_id": str(house_id),
                    "bill_amount": float(bill_amt),
                    "units_consumed": int(row.get('units_consumed', 0)),
                    "month": str(row.get('month', 'N/A')),
                    "address": str(row.get('address', 'N/A')),
                    "reason": f"Bill amount ₹{bill_amt:.2f} is below residential threshold (₹{RESIDENTIAL_MIN})",
                    "severity": "low"
                })
            elif bill_amt > RESIDENTIAL_MAX:
                residential_anomalies.append({
                    "house_id": str(house_id),
                    "bill_amount": float(bill_amt),
                    "units_consumed": int(row.get('units_consumed', 0)),
                    "month": str(row.get('month', 'N/A')),
                    "address": str(row.get('address', 'N/A')),
                    "reason": f"Bill amount ₹{bill_amt:.2f} exceeds residential threshold (₹{RESIDENTIAL_MAX})",
                    "severity": "high"
                })
        
        # Calculate statistics
        residential_stats = {
            "count": len(residential_df),
            "mean": float(residential_df['bill_amount'].mean()) if len(residential_df) > 0 else 0,
            "median": float(residential_df['bill_amount'].median()) if len(residential_df) > 0 else 0,
            "min": float(residential_df['bill_amount'].min()) if len(residential_df) > 0 else 0,
            "max": float(residential_df['bill_amount'].max()) if len(residential_df) > 0 else 0,
            "std": float(residential_df['bill_amount'].std()) if len(residential_df) > 0 else 0
        }
        
        commercial_stats = {
            "count": len(commercial_df),
            "mean": float(commercial_df['bill_amount'].mean()) if len(commercial_df) > 0 else 0,
            "median": float(commercial_df['bill_amount'].median()) if len(commercial_df) > 0 else 0,
            "min": float(commercial_df['bill_amount'].min()) if len(commercial_df) > 0 else 0,
            "max": float(commercial_df['bill_amount'].max()) if len(commercial_df) > 0 else 0,
            "std": float(commercial_df['bill_amount'].std()) if len(commercial_df) > 0 else 0
        }
        
        # Monthly breakdown if month column exists
        monthly_data = []
        if 'month' in df.columns:
            monthly_groups = df.groupby('month').agg({
                'bill_amount': ['count', 'sum', 'mean', 'max'],
                'units_consumed': 'sum'
            }).reset_index()
            
            # Sort months properly
            month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            monthly_groups['month'] = pd.Categorical(monthly_groups['month'], categories=month_order, ordered=True)
            monthly_groups = monthly_groups.sort_values('month')
            
            for _, row in monthly_groups.iterrows():
                monthly_data.append({
                    "month": str(row['month']),
                    "count": int(row['bill_amount']['count']),
                    "total_amount": float(row['bill_amount']['sum']),
                    "average_amount": float(row['bill_amount']['mean']),
                    "max_amount": float(row['bill_amount']['max']),
                    "total_units": int(row['units_consumed']['sum'])
                })
        
        # Prepare summary
        summary = {
            "total_records": len(df),
            "residential": residential_stats,
            "commercial": commercial_stats,
            "anomalies_count": len(residential_anomalies),
            "monthly_data": monthly_data,
            "thresholds": {
                "residential_min": RESIDENTIAL_MIN,
                "residential_max": RESIDENTIAL_MAX
            }
        }
        
        # Prepare data for LLM
        analysis_data = {
            "summary": summary,
            "anomalies": residential_anomalies,
            "all_records": df.to_dict(orient='records')[:100],  # Limit to first 100 for context
            "data_hash": str(hash(str(df.values.tobytes())))  # Simple hash for session tracking
        }
        
        logger.info(f"Analysis prepared: {len(residential_anomalies)} residential anomalies found")
        logger.info(f"Residential: {len(residential_df)}, Commercial: {len(commercial_df)}")
        
        return analysis_data
        
    except Exception as e:
        logger.error(f"File processing error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "error": "File processing failed",
            "details": str(e)
        }