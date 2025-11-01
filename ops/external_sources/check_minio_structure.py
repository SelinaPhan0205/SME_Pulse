"""
Script kiểm tra cấu trúc folder World Bank trên MinIO
"""
from minio import Minio
import os

client = Minio(
    endpoint=os.getenv('MINIO_ENDPOINT', 'localhost:9000'),
    access_key=os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
    secret_key=os.getenv('MINIO_SECRET_KEY', 'minioadmin123'),
    secure=False
)

bucket = 'sme-lake'
prefix = 'bronze/raw/world_bank/indicators/'

print(f"\n📂 Listing objects in s3://{bucket}/{prefix}\n")
print(f"{'Path':<80} {'Size':>10}")
print("="*92)

objects = client.list_objects(bucket, prefix=prefix, recursive=True)
count = 0
for obj in objects:
    print(f"{obj.object_name:<80} {obj.size:>10}")
    count += 1

print("="*92)
print(f"Total: {count} objects\n")
