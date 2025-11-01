"""
Ingest World Bank indicators vào MinIO bronze layer
Schedule: Monthly (via Airflow)
"""
import requests
import pandas as pd
from datetime import datetime
from minio import Minio
import io
import os

def ingest_world_bank_data(
    indicators: list,
    country: str = 'VNM',
    bucket: str = 'sme-lake',
    prefix: str = 'bronze/raw/world_bank/indicators'
):
    """
    Thu thập dữ liệu World Bank API và ghi vào MinIO
    
    Args:
        indicators: List mã chỉ số (ví dụ: ['FP.CPI.TOTL.ZG'])
        country: Mã quốc gia (mặc định VNM)
        bucket: MinIO bucket name
        prefix: Prefix path trong bucket
    """
    # Kết nối MinIO
    # Sử dụng localhost:9000 khi chạy local, minio:9000 khi chạy trong Docker
    endpoint = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
    client = Minio(
        endpoint=endpoint,
        access_key=os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
        secret_key=os.getenv('MINIO_SECRET_KEY', 'minioadmin123'),
        secure=False
    )
    
    print(f"🔗 Connecting to MinIO at {endpoint}...")
    
    print(f"\n{'='*60}")
    print(f"  WORLD BANK DATA INGESTION")
    print(f"  Country: {country} | Indicators: {len(indicators)}")
    print(f"{'='*60}\n")
    
    for indicator in indicators:
        try:
            # Gọi World Bank API
            url = f'https://api.worldbank.org/v2/country/{country}/indicator/{indicator}'
            params = {'format': 'json', 'per_page': 1000}
            
            print(f"📥 Fetching {indicator}...")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if len(data) < 2:
                print(f"⚠️  No data returned for {indicator}")
                continue
            
            # Parse dữ liệu
            records = []
            for r in data[1]:
                if r['value'] is not None:
                    records.append({
                        'indicator_code': indicator,
                        'country_code': country,
                        'year': r['date'],
                        'value': r['value'],
                        'ingested_at': datetime.now().isoformat()
                    })
            
            if not records:
                print(f"⚠️  No valid values for {indicator}")
                continue
            
            df = pd.DataFrame(records)
            print(f"✅ Fetched {len(df)} records for {indicator}")
            
            # Ghi vào MinIO dưới dạng Parquet
            parquet_buffer = io.BytesIO()
            df.to_parquet(parquet_buffer, index=False, engine='pyarrow')
            parquet_buffer.seek(0)
            
            # Ghi flat (không tạo subfolder) để Trino đọc được
            object_name = f'{prefix}/{indicator}_{datetime.now().strftime("%Y%m%d")}.parquet'
            client.put_object(
                bucket_name=bucket,
                object_name=object_name,
                data=parquet_buffer,
                length=parquet_buffer.getbuffer().nbytes,
                content_type='application/octet-stream'
            )
            
            print(f"💾 Uploaded to s3://{bucket}/{object_name}\n")
            
        except Exception as e:
            print(f"❌ Error processing {indicator}: {str(e)}\n")
            continue
    
    print(f"{'='*60}")
    print(f"  INGESTION COMPLETED")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    # Test thủ công
    indicators = [
        'FP.CPI.TOTL.ZG',      # Inflation
        'NY.GDP.MKTP.KD.ZG',   # GDP growth
        'SL.UEM.TOTL.ZS'       # Unemployment
    ]
    ingest_world_bank_data(indicators)