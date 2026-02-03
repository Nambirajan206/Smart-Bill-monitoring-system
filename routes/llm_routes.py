from flask import jsonify, request
from werkzeug.utils import secure_filename
import pandas as pd
import io
import logging

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def register_llm_routes(app):
    
    @app.route('/api/llm/analyze', methods=['POST'])
    def analyze_with_llm():
        """Analyze uploaded file using Gemini AI to detect spikes"""
        try:
            if 'file' not in request.files:
                return jsonify({"error": "No file uploaded"}), 400
            
            file = request.files['file']
            
            if file.filename == '':
                return jsonify({"error": "No file selected"}), 400
            
            if not allowed_file(file.filename):
                return jsonify({"error": "Invalid file type"}), 400
            
            filename = secure_filename(file.filename)
            logger.info(f"Processing file: {filename}")
            
            file_content = file.read()
            result = process_file_with_ai(file_content, filename)
            
            if "error" in result:
                return jsonify(result), 400
            
            return jsonify({
                "status": "success",
                "filename": filename,
                "summary": result["summary"],
                "analysis": result["analysis"],
                "spikes": result["spikes"],
                "raw_data": result.get("raw_data", [])  # Include raw data for chat
            }), 200
            
        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": "Analysis failed", "details": str(e)}), 500
    
    @app.route('/api/llm/chat', methods=['POST'])
    def chat_with_llm():
        """Chat endpoint for questions about the analysis"""
        try:
            data = request.json
            
            if not data or 'question' not in data:
                return jsonify({"error": "Missing question"}), 400
            
            question = data.get('question', '').strip()
            context = data.get('context', {})
            
            if not question:
                return jsonify({"error": "Question cannot be empty"}), 400
            
            logger.info(f"Chat question: {question}")
            
            from services.llm_service import answer_chat_question
            answer = answer_chat_question(question, context)
            
            return jsonify({
                "status": "success",
                "question": question,
                "answer": answer
            }), 200
            
        except Exception as e:
            logger.error(f"Chat failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({
                "error": "Failed to process question",
                "details": str(e)
            }), 500

def process_file_with_ai(file_content, filename):
    """Process file and use AI to analyze each consumer"""
    try:
        file_ext = filename.rsplit('.', 1)[1].lower()
        
        if file_ext == 'csv':
            df = pd.read_csv(io.BytesIO(file_content))
        else:
            df = pd.read_excel(io.BytesIO(file_content))
        
        logger.info(f"Loaded {len(df)} rows, {len(df.columns)} columns")
        
        df.columns = df.columns.str.strip()
        
        if 'Consumer_ID' not in df.columns:
            id_cols = [col for col in df.columns if 'id' in col.lower()]
            if id_cols:
                df.rename(columns={id_cols[0]: 'Consumer_ID'}, inplace=True)
            else:
                df['Consumer_ID'] = [f'C{str(i+1).zfill(3)}' for i in range(len(df))]
        
        if 'Consumer_Type' not in df.columns:
            type_cols = [col for col in df.columns if 'type' in col.lower()]
            if type_cols:
                df.rename(columns={type_cols[0]: 'Consumer_Type'}, inplace=True)
            else:
                df['Consumer_Type'] = 'Residential'
        
        df['Consumer_Type'] = df['Consumer_Type'].str.strip().str.title()
        df['Consumer_Type'] = df['Consumer_Type'].apply(
            lambda x: 'Commercial' if x in ['Commercial', 'Com', 'C'] else 'Residential'
        )
        
        month_columns = ['January', 'February', 'March', 'April', 'May', 'June',
                        'July', 'August', 'September', 'October', 'November', 'December']
        available_months = [col for col in month_columns if col in df.columns]
        
        if len(available_months) < 2:
            return {
                "error": "Insufficient data",
                "details": "File must contain at least 2 months of billing data"
            }
        
        logger.info(f"Found {len(available_months)} months of data")
        
        from services.llm_service import analyze_consumer_with_ai, generate_overall_insights
        
        all_results = []
        all_spikes = []
        raw_data = []  # Store all consumer data for chat
        
        logger.info(f"Starting AI analysis for {len(df)} consumers...")
        
        for idx, row in df.iterrows():
            consumer_id = str(row['Consumer_ID'])
            consumer_type = str(row['Consumer_Type'])
            
            monthly_bills = []
            monthly_dict = {}
            for month in available_months:
                bill = row.get(month)
                if pd.notna(bill) and bill > 0:
                    monthly_bills.append({
                        'month': month,
                        'amount': float(bill)
                    })
                    monthly_dict[month] = float(bill)
            
            if len(monthly_bills) < 2:
                logger.warning(f"Skipping {consumer_id} - insufficient data")
                continue
            
            # Store raw data for chat context
            raw_data.append({
                'consumer_id': consumer_id,
                'consumer_type': consumer_type,
                'monthly_bills': monthly_dict
            })
            
            logger.info(f"Analyzing consumer {consumer_id} ({idx+1}/{len(df)})...")
            result = analyze_consumer_with_ai(consumer_id, consumer_type, monthly_bills)
            
            all_results.append(result)
            
            if result.get('has_spikes'):
                all_spikes.extend(result['spikes'])
        
        logger.info(f"AI analysis complete. Found {len(all_spikes)} total spikes")
        
        residential_count = len(df[df['Consumer_Type'] == 'Residential'])
        commercial_count = len(df[df['Consumer_Type'] == 'Commercial'])
        
        summary = {
            "total_consumers": len(df),
            "residential_count": residential_count,
            "commercial_count": commercial_count,
            "spike_count": len(all_spikes),
            "consumers_with_spikes": sum(1 for r in all_results if r.get('has_spikes'))
        }
        
        logger.info("Generating overall insights...")
        overall_analysis = generate_overall_insights(all_results, summary)
        
        return {
            "summary": summary,
            "spikes": all_spikes,
            "analysis": overall_analysis,
            "raw_data": raw_data  # Include for chat
        }
        
    except Exception as e:
        logger.error(f"Processing failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "error": "File processing failed",
            "details": str(e)
        }
