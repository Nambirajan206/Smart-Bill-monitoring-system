import pandas as pd
import io
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Threshold for high bills
HIGH_BILL_THRESHOLD = 5000


def process_excel_content(file_content, file_name="unknown"):
    """
    Process a single Excel file and return high-bill records
    
    Args:
        file_content (bytes): Excel file binary content
        file_name (str): Name of the file being processed
        
    Returns:
        list: List of dictionaries containing high-bill records
    """
    try:
        # Load Excel file into Pandas DataFrame
        df = pd.read_excel(io.BytesIO(file_content))
        
        logger.info(f"Processing {file_name}: {len(df)} total records")
        
        # Clean column names (remove leading/trailing whitespace)
        df.columns = df.columns.str.strip()
        
        # Validate required columns exist
        required_columns = ['House_ID', 'Bill_Amount', 'Month']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            logger.error(f"Missing required columns in {file_name}: {missing_columns}")
            logger.error(f"Available columns: {list(df.columns)}")
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Remove rows with missing critical data
        df = df.dropna(subset=['House_ID', 'Bill_Amount', 'Month'])
        
        # Convert data types
        df['Bill_Amount'] = pd.to_numeric(df['Bill_Amount'], errors='coerce')
        df['Units_Consumed'] = pd.to_numeric(df.get('Units_Consumed', 0), errors='coerce').fillna(0)
        
        # Remove rows where conversion failed
        df = df.dropna(subset=['Bill_Amount'])
        
        # Filter high bills (> threshold)
        high_bills_df = df[df['Bill_Amount'] > HIGH_BILL_THRESHOLD]
        
        logger.info(f"Found {len(high_bills_df)} high-bill records (>{HIGH_BILL_THRESHOLD}) in {file_name}")
        
        # Convert to list of dictionaries
        records = high_bills_df.to_dict(orient='records')
        
        return records
        
    except Exception as e:
        logger.error(f"Error processing {file_name}: {str(e)}")
        raise


def process_excel_files(excel_files):
    """
    Process ALL Excel files, combine data, and filter high bills
    
    Args:
        excel_files (list): List of dictionaries with 'name' and 'content' keys
        
    Returns:
        list: Combined list of all high-bill records from all files
    """
    all_high_bills = []
    processed_count = 0
    error_count = 0
    
    logger.info(f"Starting to process {len(excel_files)} Excel file(s)")
    
    for idx, file_data in enumerate(excel_files, 1):
        file_name = file_data.get('name', f'file_{idx}')
        file_content = file_data.get('content')
        
        try:
            # Process individual file
            high_bills = process_excel_content(file_content, file_name)
            
            # Add to combined list
            all_high_bills.extend(high_bills)
            processed_count += 1
            
            logger.info(f"Progress: {idx}/{len(excel_files)} files processed")
            
        except Exception as e:
            error_count += 1
            logger.error(f"Failed to process {file_name}: {str(e)}")
            # Continue processing other files even if one fails
            continue
    
    logger.info(f"Processing complete: {processed_count} files successful, {error_count} files failed")
    logger.info(f"Total high-bill records found: {len(all_high_bills)}")
    
    # Remove duplicates based on House_ID and Month (keep first occurrence)
    if all_high_bills:
        df_combined = pd.DataFrame(all_high_bills)
        df_combined = df_combined.drop_duplicates(subset=['House_ID', 'Month'], keep='first')
        all_high_bills = df_combined.to_dict(orient='records')
        logger.info(f"After removing duplicates: {len(all_high_bills)} unique records")
    
    return all_high_bills


def get_excel_summary(file_content, file_name="unknown"):
    """
    Get summary statistics from an Excel file without filtering
    
    Args:
        file_content (bytes): Excel file binary content
        file_name (str): Name of the file
        
    Returns:
        dict: Summary statistics
    """
    try:
        df = pd.read_excel(io.BytesIO(file_content))
        df.columns = df.columns.str.strip()
        
        summary = {
            "file_name": file_name,
            "total_records": len(df),
            "columns": list(df.columns),
            "bill_stats": {}
        }
        
        if 'Bill_Amount' in df.columns:
            df['Bill_Amount'] = pd.to_numeric(df['Bill_Amount'], errors='coerce')
            summary["bill_stats"] = {
                "min": float(df['Bill_Amount'].min()),
                "max": float(df['Bill_Amount'].max()),
                "mean": float(df['Bill_Amount'].mean()),
                "median": float(df['Bill_Amount'].median()),
                "high_bills_count": int((df['Bill_Amount'] > HIGH_BILL_THRESHOLD).sum())
            }
        
        return summary
        
    except Exception as e:
        logger.error(f"Error getting summary for {file_name}: {str(e)}")
        return {"file_name": file_name, "error": str(e)}
