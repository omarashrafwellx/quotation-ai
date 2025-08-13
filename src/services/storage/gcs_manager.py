"""
Google Cloud Storage operations manager.
"""

import os
import asyncio
from datetime import timedelta
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from google.cloud import storage
from google.oauth2 import service_account
from src.core.config import settings
from src.core.exceptions import StorageError

class GCSManager:
    """Manages Google Cloud Storage operations."""
    
    def __init__(self):
        self.bucket_name = settings.GCS_BUCKET_NAME
        self.service_account_key_path = settings.GCS_AUTH_JSON_FILE
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        # Initialize GCP credentials
        try:
            self.credentials = service_account.Credentials.from_service_account_file(
                self.service_account_key_path
            )
            self.storage_client = storage.Client(credentials=self.credentials)
            self.bucket = self.storage_client.bucket(self.bucket_name)
        except Exception as e:
            raise StorageError(f"Failed to initialize GCS client: {e}")
    
    def _upload_file_sync(self, file_path: str, destination_blob_name: str) -> str:
        """Synchronous file upload to GCS."""
        try:
            blob = self.bucket.blob(destination_blob_name)
            blob.upload_from_filename(file_path)
            
            # Generate signed URL for temporary access
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=30),
                method="GET"
            )
            return url
        except Exception as e:
            raise StorageError(f"Error uploading to GCS: {e}")
    
    def _download_file_sync(self, gcs_path: str, local_path: str) -> bool:
        """Synchronous file download from GCS."""
        try:
            blob = self.bucket.blob(gcs_path)
            blob.download_to_filename(local_path)
            return True
        except Exception as e:
            print(f"Error downloading from GCS: {e}")
            return False
    
    async def upload_file(self, file_path: str, destination_blob_name: str) -> Optional[str]:
        """Upload file to GCS asynchronously."""
        if not os.path.exists(file_path):
            raise StorageError(f"File not found: {file_path}")
        
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(
                self.executor, 
                self._upload_file_sync, 
                file_path, 
                destination_blob_name
            )
        except Exception as e:
            print(f"Error uploading {file_path} to GCS: {e}")
            return None
    
    async def download_file(self, gcs_path: str, local_path: str) -> bool:
        """Download file from GCS asynchronously."""
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(
                self.executor,
                self._download_file_sync,
                gcs_path,
                local_path
            )
        except Exception as e:
            print(f"Error downloading {gcs_path} from GCS: {e}")
            return False
    
    def generate_signed_url(self, blob_name: str, expiration_minutes: int = 30) -> Optional[str]:
        """Generate a signed URL for a blob."""
        try:
            blob = self.bucket.blob(blob_name)
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=expiration_minutes),
                method="GET"
            )
            return url
        except Exception as e:
            print(f"Error generating signed URL for {blob_name}: {e}")
            return None
    
    def delete_file(self, blob_name: str) -> bool:
        """Delete a file from GCS."""
        try:
            blob = self.bucket.blob(blob_name)
            blob.delete()
            return True
        except Exception as e:
            print(f"Error deleting {blob_name} from GCS: {e}")
            return False
    
    def list_files(self, prefix: str = "") -> list:
        """List files in GCS bucket with optional prefix."""
        try:
            blobs = self.storage_client.list_blobs(self.bucket_name, prefix=prefix)
            return [blob.name for blob in blobs]
        except Exception as e:
            print(f"Error listing files in GCS: {e}")
            return []

# Global GCS manager instance
gcs_manager = GCSManager()