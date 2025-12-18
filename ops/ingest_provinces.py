"""
Ingest Vietnam provinces data vào MinIO bronze layer
Schedule: One-time or when province structure changes (rare)
"""
import requests
import pandas as pd
from datetime import datetime
from minio import Minio
import io
import os

def ingest_provinces_data(
    depth: int = 2,
    bucket: str = 'sme-pulse',
    prefix: str = 'bronze/raw/vietnam_provinces'
):
    """
    Thu thập dữ liệu tỉnh/quận/phường từ provinces.open-api.vn
    
    Args:
        depth: 1 (tỉnh), 2 (tỉnh+quận), 3 (tỉnh+quận+phường)
        bucket: MinIO bucket name
        prefix: Prefix path trong bucket
    """
    # Kết nối MinIO
    # Sử dụng minio:9000 khi chạy trong Docker, localhost:9000 khi chạy local
    endpoint = os.getenv('MINIO_ENDPOINT', 'sme-minio:9000')
    client = Minio(
        endpoint=endpoint,
        access_key=os.getenv('MINIO_ACCESS_KEY', 'minio'),
        secret_key=os.getenv('MINIO_SECRET_KEY', 'minio123'),
        secure=False
    )
    
    print(f"🔗 Connecting to MinIO at {endpoint}...")
    
    print(f"\n{'='*60}")
    print(f"  VIETNAM PROVINCES DATA INGESTION")
    print(f"  Depth: {depth}")
    print(f"{'='*60}\n")
    
    # Gọi API
    url = f'https://provinces.open-api.vn/api/v1/?depth={depth}'
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; SME-Pulse/1.0)'}
    
    print(f"📥 Fetching provinces data (depth={depth})...")
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    provinces_data = response.json()
    
    print(f"✅ Fetched {len(provinces_data)} provinces\n")
    
    # Parse provinces
    provinces = []
    for p in provinces_data:
        provinces.append({
            'province_code': str(p['code']),
            'province_name': p['name'],
            'phone_code': p.get('phone_code', ''),
            'division_type': p.get('division_type', ''),
            'codename': p.get('codename', ''),
            'ingested_at': datetime.now().isoformat()
        })
    
    df_provinces = pd.DataFrame(provinces)
    
    # Ghi provinces vào MinIO
    parquet_buffer = io.BytesIO()
    df_provinces.to_parquet(parquet_buffer, index=False, engine='pyarrow')
    parquet_buffer.seek(0)
    
    object_name = f'{prefix}/provinces/{datetime.now().strftime("%Y%m%d")}.parquet'
    client.put_object(
        bucket_name=bucket,
        object_name=object_name,
        data=parquet_buffer,
        length=parquet_buffer.getbuffer().nbytes,
        content_type='application/octet-stream'
    )
    
    print(f"💾 Provinces uploaded to s3://{bucket}/{object_name}")
    
    # Parse districts nếu depth >= 2
    if depth >= 2:
        districts = []
        for p in provinces_data:
            for d in p.get('districts', []):
                districts.append({
                    'district_code': str(d['code']),
                    'district_name': d['name'],
                    'province_code': str(p['code']),
                    'division_type': d.get('division_type', ''),
                    'codename': d.get('codename', ''),
                    'ingested_at': datetime.now().isoformat()
                })
        
        df_districts = pd.DataFrame(districts)
        print(f"✅ Parsed {len(df_districts)} districts\n")
        
        parquet_buffer = io.BytesIO()
        df_districts.to_parquet(parquet_buffer, index=False, engine='pyarrow')
        parquet_buffer.seek(0)
        
        object_name = f'{prefix}/districts/{datetime.now().strftime("%Y%m%d")}.parquet'
        client.put_object(
            bucket_name=bucket,
            object_name=object_name,
            data=parquet_buffer,
            length=parquet_buffer.getbuffer().nbytes,
            content_type='application/octet-stream'
        )
        
        print(f"💾 Districts uploaded to s3://{bucket}/{object_name}")
    
    print(f"\n{'='*60}")
    print(f"  INGESTION COMPLETED")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    # Test thủ công
    ingest_provinces_data(depth=2)
