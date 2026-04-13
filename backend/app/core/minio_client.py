"""Khách hàng MinIO cho các hoạt động lưu trữ tệp"""

import os
import boto3
from datetime import timedelta
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class MinIOClient:
    """Khách hàng cho lưu trữ tương thích S3 của MinIO"""
    
    def __init__(self):
        """Khởi tạo khách hàng MinIO"""
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
        Chuyển đổi URL Docker nội bộ thành URL có thể truy cập từ trình duyệt bên ngoài
        
        Args:
            internal_url: URL với tên máy chủ nội bộ (minio:9000)
            
        Returns:
            URL với tên máy chủ bên ngoài (localhost:9000)
        """
        return internal_url.replace(
            f"http://{self.internal_endpoint}",
            f"http://{self.external_endpoint}"
        )
    
    def upload_file(self, file_path: str, object_name: str) -> dict:
        """
        Tải tệp lên MinIO
        
        Args:
            file_path: Đường dẫn tệp cục bộ
            object_name: Tên đối tượng S3 (khóa)
            
        Returns:
            dict với file_url và presigned_url
        """
        try:
            # Tải lên tệp
            self.client.upload_file(file_path, self.bucket, object_name)
            logger.info(f"Uploaded {object_name} to MinIO")
            
            # Tạo URL được ký sẵn (48 giờ hiệu lực)
            presigned_url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": object_name},
                ExpiresIn=48 * 3600,  # 48 giờ
            )
            
            # Chuyển đổi thành URL bên ngoài để truy cập từ trình duyệt
            external_url = self._make_external_url(presigned_url)
            
            return {
                "file_url": external_url,
                "object_name": object_name,
                "bucket": self.bucket,
            }
            
        except Exception as e:
            logger.error(f"Failed to upload {object_name}: {e}")
            raise
    
    def delete_file(self, object_name: str) -> bool:
        """
        Xóa tệp từ MinIO
        
        Args:
            object_name: Tên đối tượng S3 (khóa)
            
        Returns:
            True nếu thành công
        """
        try:
            self.client.delete_object(Bucket=self.bucket, Key=object_name)
            logger.info(f"Deleted {object_name} from MinIO")
            return True
        except Exception as e:
            logger.error(f"Failed to delete {object_name}: {e}")
            return False
    
    def get_presigned_url(self, object_name: str, expires_in: int = 48 * 3600) -> str:
        """
        Lấy URL được ký sẵn cho một đối tượng
        
        Args:
            object_name: Tên đối tượng S3 (khóa)
            expires_in: Thời gian hết hạn tính bằng giây (mặc định 48 giờ)
            
        Returns:
            URL được ký sẵn
        """
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": object_name},
                ExpiresIn=expires_in,
            )
            # Chuyển đổi thành URL bên ngoài để truy cập từ trình duyệt
            return self._make_external_url(url)
        except Exception as e:
            logger.error(f"Failed to get presigned URL for {object_name}: {e}")
            raise


# Singleton instance
minio_client = MinIOClient()
