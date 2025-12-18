"""MinIO client for file storage operations"""

import os
import boto3
from datetime import timedelta
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class MinIOClient:
    """Client for MinIO S3-compatible storage"""
    
    def __init__(self):
        """Initialize MinIO client"""
        self.internal_endpoint = settings.MINIO_ENDPOINT  # e.g., minio:9000
        self.external_endpoint = os.getenv("MINIO_EXTERNAL_ENDPOINT", "localhost:9000")  # For browser access
        
        self.client = boto3.client(
            "s3",
            endpoint_url=f"http://{self.internal_endpoint}",
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
            use_ssl=settings.MINIO_SECURE,
            region_name="us-east-1",
        )
        self.bucket = settings.MINIO_BUCKET_NAME
    
    def _make_external_url(self, internal_url: str) -> str:
        """
        Convert internal Docker URL to external browser-accessible URL
        
        Args:
            internal_url: URL with internal hostname (minio:9000)
            
        Returns:
            URL with external hostname (localhost:9000)
        """
        return internal_url.replace(
            f"http://{self.internal_endpoint}",
            f"http://{self.external_endpoint}"
        )
    
    def upload_file(self, file_path: str, object_name: str) -> dict:
        """
        Upload file to MinIO
        
        Args:
            file_path: Local file path
            object_name: S3 object name (key)
            
        Returns:
            dict with file_url and presigned_url
        """
        try:
            # Upload file
            self.client.upload_file(file_path, self.bucket, object_name)
            logger.info(f"✅ Uploaded {object_name} to MinIO")
            
            # Generate presigned URL (48 hours validity)
            presigned_url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": object_name},
                ExpiresIn=48 * 3600,  # 48 hours
            )
            
            # Convert to external URL for browser access
            external_url = self._make_external_url(presigned_url)
            
            return {
                "file_url": external_url,
                "object_name": object_name,
                "bucket": self.bucket,
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to upload {object_name}: {e}")
            raise
    
    def delete_file(self, object_name: str) -> bool:
        """
        Delete file from MinIO
        
        Args:
            object_name: S3 object name (key)
            
        Returns:
            True if successful
        """
        try:
            self.client.delete_object(Bucket=self.bucket, Key=object_name)
            logger.info(f"✅ Deleted {object_name} from MinIO")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to delete {object_name}: {e}")
            return False
    
    def get_presigned_url(self, object_name: str, expires_in: int = 48 * 3600) -> str:
        """
        Get presigned URL for an object
        
        Args:
            object_name: S3 object name (key)
            expires_in: Expiration time in seconds (default 48 hours)
            
        Returns:
            Presigned URL
        """
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": object_name},
                ExpiresIn=expires_in,
            )
            # Convert to external URL for browser access
            return self._make_external_url(url)
        except Exception as e:
            logger.error(f"❌ Failed to get presigned URL for {object_name}: {e}")
            raise


# Singleton instance
minio_client = MinIOClient()
