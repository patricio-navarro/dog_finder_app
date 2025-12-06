"""
Storage service for handling image uploads to Google Cloud Storage.
"""
import uuid
import logging
from typing import Optional

from ..exceptions import StorageError, ServiceUnavailableError
from .. import gcp_clients

logger = logging.getLogger(__name__)


class StorageService:
    """Service for managing image uploads to GCS."""
    
    def __init__(self, storage_client=None, bucket_name: str = ""):
        """
        Initialize storage service.
        
        Args:
            storage_client: GCS storage client (or None to use global client)
            bucket_name: Name of the GCS bucket
        """
        self.storage_client = storage_client or gcp_clients.storage_client
        self.bucket_name = bucket_name or gcp_clients.BUCKET_NAME
    
    def upload_image(self, image_file, filename: Optional[str] = None) -> str:
        """
        Upload image file to GCS.
        
        Args:
            image_file: File object to upload
            filename: Optional custom filename (generates UUID if not provided)
            
        Returns:
            str: GCS URL of uploaded image (gs://bucket/filename format)
            
        Raises:
            ServiceUnavailableError: If storage client is not initialized
            StorageError: If upload fails
        """
        if not self.storage_client:
            raise ServiceUnavailableError("Storage")
        
        if not filename:
            # Generate unique filename
            original_ext = image_file.filename.rsplit('.', 1)[-1] if '.' in image_file.filename else 'jpg'
            filename = f"{uuid.uuid4()}.{original_ext}"
        
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(filename)
            blob.upload_from_file(image_file, content_type=image_file.content_type)
            
            image_url = f"gs://{self.bucket_name}/{filename}"
            logger.info(f"Successfully uploaded image to {image_url}")
            return image_url
            
        except Exception as e:
            logger.error(f"Failed to upload image to GCS: {e}")
            raise StorageError(f"Failed to upload image: {str(e)}")
    
    def delete_image(self, image_url: str) -> bool:
        """
        Delete image from GCS.
        
        Args:
            image_url: GCS URL of image to delete (gs://bucket/filename format)
            
        Returns:
            bool: True if deleted successfully, False otherwise
            
        Raises:
            ServiceUnavailableError: If storage client is not initialized
        """
        if not self.storage_client:
            raise ServiceUnavailableError("Storage")
        
        if not image_url.startswith("gs://"):
            logger.warning(f"Invalid GCS URL format: {image_url}")
            return False
        
        try:
            # Extract bucket and blob name from URL
            path = image_url.replace("gs://", "")
            parts = path.split("/", 1)
            if len(parts) != 2:
                logger.warning(f"Could not parse GCS URL: {image_url}")
                return False
            
            bucket_name, blob_name = parts
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            blob.delete()
            
            logger.info(f"Successfully deleted image: {image_url}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete image {image_url}: {e}")
            return False
