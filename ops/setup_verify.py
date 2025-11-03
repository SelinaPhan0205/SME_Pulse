#!/usr/bin/env python3
"""
Setup Verification Script: Kiểm tra environment ready trước khi ingest
- Python packages
- MinIO connection
- Source files
- Disk space
"""

import sys
import subprocess
import os
from pathlib import Path
from datetime import datetime

def print_header(text):
    print(f"\n{'=' * 70}")
    print(f"  {text}")
    print(f"{'=' * 70}\n")

def print_check(status, message):
    symbol = "✅" if status else "❌"
    print(f"  {symbol} {message}")
    return status

def main():
    print_header("🔍 SME PULSE – INGEST SETUP VERIFICATION")
    
    all_passed = True
    
    # 1. Python version
    print("1️⃣  Python Environment")
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    all_passed &= print_check(
        sys.version_info >= (3, 8),
        f"Python {python_version} (required >= 3.8)"
    )
    
    # 2. Project structure
    print("\n2️⃣  Project Structure")
    project_root = Path(__file__).parent.parent
    
    required_dirs = [
        ("data/raw", "Source data directory"),
        ("dbt", "dbt project"),
        ("airflow", "Airflow directory"),
    ]
    
    for dir_name, description in required_dirs:
        dir_path = project_root / dir_name
        exists = dir_path.exists()
        all_passed &= print_check(exists, f"{dir_name}/ ({description})")
    
    # 3. Source files
    print("\n3️⃣  Source CSV Files")
    csv_files = [
        ("data/raw/Bank-Transactions.csv", "Bank transactions"),
        ("data/raw/shipments_payments.csv", "Shipments & payments"),
    ]
    
    for csv_file, description in csv_files:
        file_path = project_root / csv_file
        exists = file_path.exists()
        all_passed &= print_check(exists, f"{csv_file} ({description})")
        
        if exists:
            size_mb = file_path.stat().st_size / (1024 * 1024)
            print(f"     Size: {size_mb:.1f} MB")
    
    # 4. Python packages
    print("\n4️⃣  Python Packages")
    required_packages = [
        ("pandas", "Data processing"),
        ("pyarrow", "Parquet support"),
        ("minio", "MinIO client"),
    ]
    
    for package, description in required_packages:
        try:
            __import__(package)
            all_passed &= print_check(True, f"{package} ({description})")
        except ImportError:
            all_passed &= print_check(False, f"{package} ({description})")
    
    # 5. MinIO connection
    print("\n5️⃣  MinIO Connection")
    try:
        from minio import Minio
        
        minio_host = os.getenv("MINIO_HOST", "localhost:9000")
        minio_access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        minio_secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
        
        client = Minio(
            minio_host,
            access_key=minio_access_key,
            secret_key=minio_secret_key,
            secure=False
        )
        
        # Test connection
        buckets = client.list_buckets()
        all_passed &= print_check(True, f"MinIO connected ({minio_host})")
        print(f"     Buckets: {len(buckets)}")
        
        # Check sme-lake bucket
        bucket_exists = client.bucket_exists("sme-lake")
        if bucket_exists:
            all_passed &= print_check(True, "Bucket 'sme-lake' exists")
        else:
            all_passed &= print_check(False, "Bucket 'sme-lake' not found")
            print("     💡 Tip: dbt will create it on first run")
        
    except Exception as e:
        all_passed &= print_check(False, f"MinIO connection failed: {e}")
    
    # 6. Disk space
    print("\n6️⃣  Disk Space")
    try:
        import shutil
        stat = shutil.disk_usage(project_root)
        free_gb = stat.free / (1024**3)
        all_passed &= print_check(
            free_gb > 5,
            f"Disk space: {free_gb:.1f} GB free (required > 5 GB)"
        )
    except Exception as e:
        print(f"     ⚠️  Could not check disk space: {e}")
    
    # Summary
    print_header("📋 SUMMARY")
    
    if all_passed:
        print("  ✅ All checks passed! Ready to ingest.")
        print("\n  Next steps:")
        print("    1. python ops/run_all_ingest.py")
        print("    2. dbt run --select silver.*")
        print("    3. dbt test")
        return 0
    else:
        print("  ❌ Some checks failed. Please fix above issues.")
        print("\n  💡 Tips:")
        print("    - Install packages: pip install -r ops/requirements_ingest.txt")
        print("    - Start MinIO: docker-compose up -d minio")
        print("    - Check source files: ls -la data/raw/")
        return 1

if __name__ == "__main__":
    sys.exit(main())
