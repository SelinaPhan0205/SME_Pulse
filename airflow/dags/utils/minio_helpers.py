"""
Utility functions for MinIO operations
Các hàm tiện ích cho thao tác với MinIO
"""
from minio import Minio
from minio.error import S3Error
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def get_minio_client(config: Dict[str, Any]) -> Minio:
    """
    Tạo MinIO client từ config
    
    Args:
        config: Dict chứa minio configuration
    
    Returns:
        Minio client instance
    """
    return Minio(
        endpoint=config['endpoint'],
        access_key=config['access_key'],
        secret_key=config['secret_key'],
        secure=config.get('secure', False)
    )


def check_minio_health(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Kiểm tra sức khỏe MinIO service
    
    Returns:
        Dict với status và message
    """
    try:
        client = get_minio_client(config)
        
        # Kiểm tra bucket tồn tại
        bucket_name = config['bucket']
        if not client.bucket_exists(bucket_name):
            return {
                'status': 'unhealthy',
                'message': f"Bucket '{bucket_name}' không tồn tại"
            }
        
        # Thử list objects để verify permissions (limit with prefix)
        objects = client.list_objects(bucket_name, prefix='', recursive=False)
        # Just get first object to test access
        try:
            next(iter(objects), None)
        except StopIteration:
            pass  # Empty bucket is OK
        
        return {
            'status': 'healthy',
            'message': f"MinIO OK - Bucket '{bucket_name}' accessible"
        }
    
    except S3Error as e:
        logger.error(f"MinIO S3 Error: {e}")
        return {
            'status': 'unhealthy',
            'message': f"MinIO S3 Error: {str(e)}"
        }
    except Exception as e:
        logger.error(f"MinIO connection error: {e}")
        return {
            'status': 'unhealthy',
            'message': f"Connection error: {str(e)}"
        }


def get_object_info(config: Dict[str, Any], object_path: str) -> Dict[str, Any]:
    """
    Lấy thông tin về object trong MinIO
    
    Args:
        config: MinIO config
        object_path: Path đến object (vd: bronze/raw/bank_txn_raw.parquet)
    
    Returns:
        Dict chứa size, last_modified, etc.
    """
    try:
        client = get_minio_client(config)
        bucket_name = config['bucket']
        
        stat = client.stat_object(bucket_name, object_path)
        
        return {
            'exists': True,
            'size_bytes': stat.size,
            'size_mb': round(stat.size / (1024 * 1024), 2),
            'last_modified': stat.last_modified,
            'etag': stat.etag
        }
    
    except S3Error as e:
        if e.code == 'NoSuchKey':
            return {
                'exists': False,
                'message': f"Object không tồn tại: {object_path}"
            }
        raise
    except Exception as e:
        logger.error(f"Error getting object info: {e}")
        raise


def validate_bronze_files(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Kiểm tra các file Bronze đã được ingest chưa
    
    Returns:
        Dict với status của từng file
    """
    bronze_paths = config['bronze_paths']
    results = {}
    
    for source_name, path in bronze_paths.items():
        # Giả sử file parquet có tên như path + filename
        file_path = f"{path}{source_name}_raw.parquet"
        
        try:
            info = get_object_info(config, file_path)
            results[source_name] = {
                'status': 'ok' if info['exists'] else 'missing',
                'info': info
            }
        except Exception as e:
            results[source_name] = {
                'status': 'error',
                'error': str(e)
            }
    
    return results
