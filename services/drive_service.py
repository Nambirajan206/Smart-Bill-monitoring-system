import io
import logging
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
from google.oauth2 import service_account


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
SERVICE_ACCOUNT_FILE = 'credentials.json'


def get_gdrive_service():
    
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        logger.error(f"Failed to create Drive service: {str(e)}")
        raise


def download_excel_files(folder_id):
    
    try:
        service = get_gdrive_service()
        
       
        query = (
            f"'{folder_id}' in parents and "
            f"(mimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' or "
            f"mimeType = 'application/vnd.ms-excel') and "
            f"trashed = false"
        )
        
        logger.info(f"Searching for Excel files in folder: {folder_id}")
        
       
        results = service.files().list(
            q=query,
            fields="files(id, name, size, modifiedTime)",
            pageSize=1000  
        ).execute()
        
        files = results.get('files', [])
        
        if not files:
            logger.warning(f"No Excel files found in folder: {folder_id}")
            return []
        
        logger.info(f"Found {len(files)} Excel file(s) to download")
        
        file_data_list = []
        
        for idx, file in enumerate(files, 1):
            try:
                file_id = file['id']
                file_name = file['name']
                file_size = file.get('size', 'Unknown')
                
                logger.info(f"Downloading file {idx}/{len(files)}: {file_name} (Size: {file_size} bytes)")
                
                request = service.files().get_media(fileId=file_id)
                file_stream = io.BytesIO()
                downloader = MediaIoBaseDownload(file_stream, request)
                
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    if status:
                        logger.debug(f"Download progress: {int(status.progress() * 100)}%")
                
                file_content = file_stream.getvalue()
                file_data_list.append({
                    'name': file_name,
                    'content': file_content,
                    'size': len(file_content)
                })
                
                logger.info(f"Successfully downloaded: {file_name}")
                
            except HttpError as e:
                logger.error(f"HTTP error downloading {file.get('name', 'unknown')}: {str(e)}")
                continue
            except Exception as e:
                logger.error(f"Error downloading {file.get('name', 'unknown')}: {str(e)}")
                continue
        
        logger.info(f"Successfully downloaded {len(file_data_list)} out of {len(files)} files")
        
        return file_data_list
        
    except HttpError as e:
        logger.error(f"Google Drive API error: {str(e)}")
        raise Exception(f"Failed to access Google Drive: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in download_excel_files: {str(e)}")
        raise


def list_files_in_folder(folder_id, mime_type=None):
   
    try:
        service = get_gdrive_service()
        
        query = f"'{folder_id}' in parents and trashed = false"
        if mime_type:
            query += f" and mimeType = '{mime_type}'"
        
        results = service.files().list(
            q=query,
            fields="files(id, name, mimeType, size, modifiedTime)",
            pageSize=1000
        ).execute()
        
        return results.get('files', [])
        
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
        raise