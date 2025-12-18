"""
Batch ingest Sales Snapshot data (19 Excel files) to MinIO
Handles multiple Excel files and combines them into a unified dataset

Usage:
    python ingest_sales_snapshot_batch.py --folder ../data/raw/Sales_snapshot_data --prefix sales_snapshot
"""

import os
import sys
import argparse
import pandas as pd
import boto3
from io import BytesIO
from datetime import datetime
from pathlib import Path
import glob


class BatchIngestionMinIO:
    """Batch ingest multiple Excel files to MinIO"""
    
    def __init__(self):
        """Initialize MinIO connection"""
        self.endpoint = os.getenv('MINIO_ENDPOINT', 'http://sme-minio:9000')
        self.access_key = os.getenv('MINIO_ACCESS_KEY', 'minio')
        self.secret_key = os.getenv('MINIO_SECRET_KEY', 'minio123')
        self.bronze_bucket = os.getenv('BRONZE_BUCKET', 'sme-pulse')

        self.s3_client = None
    
    def connect(self):
        """Establish MinIO connection"""
        try:
            self.s3_client = boto3.client(
                's3',
                endpoint_url=self.endpoint,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name='us-east-1'
            )
            self.s3_client.list_buckets()
            print(f"✅ Connected to MinIO: {self.endpoint}")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to MinIO: {e}")
            return False
    
    def create_bucket(self, bucket_name):
        """Create bucket if not exists"""
        try:
            self.s3_client.head_bucket(Bucket=bucket_name)
            print(f"✅ Bucket '{bucket_name}' exists")
        except:
            try:
                self.s3_client.create_bucket(Bucket=bucket_name)
                print(f"✅ Created bucket: {bucket_name}")
            except Exception as e:
                print(f"❌ Failed to create bucket: {e}")
                return False
        return True
    
    def ingest_batch(self, folder_path, prefix='sales_snapshot', combine=True, upload_originals=False):
        """
        Batch ingest all Excel files from a folder
        
        Args:
            folder_path (str): Path to folder containing Excel files
            prefix (str): S3 prefix for organized storage
            combine (bool): If True, combine all files into one Parquet. If False, upload separately.
            upload_originals (bool): If True, upload original Excel files to Bronze
        
        Returns:
            bool: Success status
        """
        print(f"\n{'='*70}")
        print(f"🚀 BATCH INGESTION TO MINIO")
        print(f"{'='*70}")
        print(f"📂 Source Folder: {folder_path}")
        print(f"🎯 Target Bucket: s3://{self.bronze_bucket}/bronze/raw/{prefix}/")
        print(f"🔀 Mode: {'COMBINED (Single Parquet)' if combine else 'INDIVIDUAL (Separate files)'}")
        print(f"{'='*70}\n")
        
        # Find all Excel files
        excel_patterns = [
            os.path.join(folder_path, '*.xlsx'),
            os.path.join(folder_path, '*.xls')
        ]
        
        excel_files = []
        for pattern in excel_patterns:
            excel_files.extend(glob.glob(pattern))
        
        if not excel_files:
            print(f"❌ No Excel files found in: {folder_path}")
            return False
        
        print(f"📊 Found {len(excel_files)} Excel files:")
        for i, file in enumerate(excel_files, 1):
            size_mb = os.path.getsize(file) / (1024 * 1024)
            print(f"   {i}. {os.path.basename(file)} ({size_mb:.2f} MB)")
        
        # Create bucket if needed
        if not self.create_bucket(self.bronze_bucket):
            return False
        
        try:
            self.upload_originals = upload_originals
            if combine:
                return self._ingest_combined(excel_files, prefix)
            else:
                result = self._ingest_individual(excel_files, prefix)
                # Upload originals after parquet if flag is set
                if getattr(self, "upload_originals", False):
                    self._upload_originals(excel_files, prefix)
                return result
        except Exception as e:
            print(f"\n❌ Batch ingestion failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _upload_originals(self, excel_files, prefix):
        """Upload original Excel files to source zone"""
        print(f"\n📦 Uploading original Excel files to /source/{prefix}/ ...")
        for i, file_path in enumerate(excel_files, 1):
            filename = os.path.basename(file_path)
            key = f"bronze/source/{prefix}/{filename}"
            try:
                with open(file_path, "rb") as f:
                    self.s3_client.put_object(
                        Bucket=self.bronze_bucket,
                        Key=key,
                        Body=f,
                        ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                print(f"   ✅ [{i}] Uploaded: {key}")
            except Exception as e:
                print(f"   ⚠️ Failed: {filename} → {e}")
    
    def _ingest_combined(self, excel_files, prefix):
        """Combine all Excel files into one Parquet"""
        print(f"\n{'='*70}")
        print("📖 READING AND COMBINING FILES...")
        print(f"{'='*70}\n")
        
        all_dataframes = []
        total_rows = 0
        
        for i, file_path in enumerate(excel_files, 1):
            print(f"📄 [{i}/{len(excel_files)}] Reading: {os.path.basename(file_path)}")
            
            try:
                df = pd.read_excel(file_path, engine='openpyxl')
                rows = len(df)
                total_rows += rows
                print(f"   ✅ {rows:,} rows × {len(df.columns)} columns")
                all_dataframes.append(df)
            except Exception as e:
                print(f"   ⚠️  Failed to read: {e}")
                continue
        
        if not all_dataframes:
            print("\n❌ No data to ingest!")
            return False
        
        # Combine all dataframes
        print(f"\n🔗 Combining {len(all_dataframes)} dataframes...")
        combined_df = pd.concat(all_dataframes, ignore_index=True)
        print(f"   ✅ Combined: {len(combined_df):,} total rows × {len(combined_df.columns)} columns")
        # Convert to Parquet
        print(f"\n🔄 Converting to Parquet (Snappy compression)...")
        buffer = BytesIO()
        combined_df.to_parquet(
            buffer,
            engine='pyarrow',
            compression='snappy',
            index=False
        )
        buffer.seek(0)
        parquet_size_mb = len(buffer.getvalue()) / (1024 * 1024)
        print(f"   ✅ Parquet size: {parquet_size_mb:.2f} MB")
        # Generate S3 key (Bronze/raw/..)
        date_partition = datetime.now().strftime('%Y-%m-%d')
        timestamp = datetime.now().strftime('%H%M%S')
        s3_key = f"bronze/raw/{prefix}/batch_{timestamp}.parquet"
        print(f"\n💾 Uploading to MinIO...")
        print(f"   🔑 Key: {s3_key}")
        # Upload
        self.s3_client.put_object(
            Bucket=self.bronze_bucket,
            Key=s3_key,
            Body=buffer.getvalue(),
            ContentType='application/x-parquet',
            Metadata={
                'source_files_count': str(len(excel_files)),
                'ingested_at': datetime.utcnow().isoformat(),
                'total_rows': str(len(combined_df)),
                'total_columns': str(len(combined_df.columns))
            }
        )
        print(f"   ✅ Upload complete!")
        # Verify
        print(f"\n🔍 Verifying upload...")
        obj = self.s3_client.head_object(Bucket=self.bronze_bucket, Key=s3_key)
        verified_size_mb = obj['ContentLength'] / (1024 * 1024)
        print(f"   ✅ Verified: {verified_size_mb:.2f} MB in MinIO")
        print(f"\n{'='*70}")
        print("✅ BATCH INGESTION COMPLETE!")
        print(f"{'='*70}")
        print(f"📊 Summary:")
        print(f"   - Source Files: {len(excel_files)}")
        print(f"   - Total Rows: {len(combined_df):,}")
        print(f"   - Total Columns: {len(combined_df.columns)}")
        print(f"   - Parquet Size: {parquet_size_mb:.2f} MB")
        print(f"   - Location: s3://{self.bronze_bucket}/{s3_key}")
        print(f"{'='*70}\n")
        print(f"🔗 Next steps:")
        print(f"   1. Check MinIO Console: http://localhost:9001")
        print(f"   2. Query with Trino:")
        print(f"      SELECT * FROM minio.default.{prefix.replace('/', '_')} LIMIT 10;")
        print(f"   3. Create dbt staging model for transformation\n")
        # Upload originals after parquet if flag is set
        if getattr(self, "upload_originals", False):
            self._upload_originals(excel_files, prefix)
        return True
    
    def _ingest_individual(self, excel_files, prefix):
        """Upload each Excel file separately as Parquet"""
        print(f"\n{'='*70}")
        print("📤 UPLOADING FILES INDIVIDUALLY...")
        print(f"{'='*70}\n")
        
        success_count = 0
        failed_files = []
        
        for i, file_path in enumerate(excel_files, 1):
            filename = os.path.basename(file_path)
            print(f"\n[{i}/{len(excel_files)}] Processing: {filename}")
            
            try:
                # Read Excel
                df = pd.read_excel(file_path, engine='openpyxl')
                print(f"   ✅ Loaded: {len(df):,} rows × {len(df.columns)} columns")
                # Convert to Parquet
                buffer = BytesIO()
                df.to_parquet(buffer, engine='pyarrow', compression='snappy', index=False)
                buffer.seek(0)
                size_mb = len(buffer.getvalue()) / (1024 * 1024)
                # Generate S3 key (Bronze/raw/..)
                date_partition = datetime.now().strftime('%Y-%m-%d')
                file_base = os.path.splitext(filename)[0]
                s3_key = f"bronze/raw/{prefix}/date={date_partition}/{file_base}.parquet"
                # Upload
                self.s3_client.put_object(
                    Bucket=self.bronze_bucket,
                    Key=s3_key,
                    Body=buffer.getvalue(),
                    ContentType='application/x-parquet',
                    Metadata={
                        'source_file': filename,
                        'ingested_at': datetime.utcnow().isoformat(),
                        'rows': str(len(df)),
                        'columns': str(len(df.columns))
                    }
                )
                print(f"   ✅ Uploaded: {size_mb:.2f} MB → {s3_key}")
                success_count += 1
            except Exception as e:
                print(f"   ❌ Failed: {e}")
                failed_files.append(filename)
                continue
        
        print(f"\n{'='*70}")
        print(f"✅ BATCH UPLOAD COMPLETE!")
        print(f"{'='*70}")
        print(f"📊 Summary:")
        print(f"   - Total Files: {len(excel_files)}")
        print(f"   - Successful: {success_count}")
        print(f"   - Failed: {len(failed_files)}")
        if failed_files:
            print(f"   - Failed files: {', '.join(failed_files)}")
        print(f"{'='*70}\n")
        
        return success_count > 0


def main(folder=None, prefix='sales_snapshot', combine=True, upload_originals=False, **kwargs):
    """
    Main execution for both CLI and Python import.
    Args can be passed as function arguments (for Airflow) or via CLI (argparse).
    """
    # Cho phép truyền folder, prefix, combine, upload_originals từ cả Airflow (kwargs) lẫn CLI
    if folder is None and len(sys.argv) > 1:
        parser = argparse.ArgumentParser(
            description='Batch ingest Sales Snapshot Excel files to MinIO',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Combine all files into one Parquet (RECOMMENDED for analytics)
  python ingest_sales_snapshot_batch.py --folder ../data/raw/Sales_snapshot_data --prefix sales_snapshot
  
  # Upload each file separately
  python ingest_sales_snapshot_batch.py --folder ../data/raw/Sales_snapshot_data --prefix sales_snapshot --individual
  
Environment Variables:
    MINIO_ENDPOINT      MinIO endpoint (default: http://minio:9000)
  MINIO_ACCESS_KEY    Access key (default: minioadmin)
  MINIO_SECRET_KEY    Secret key (default: minioadmin123)
  BRONZE_BUCKET       Bronze bucket name (default: bronze)
            """
        )
        parser.add_argument('--folder', default='/opt/data/Sales_snapshot_data', help='Path to folder containing Excel files')
        parser.add_argument('--prefix', default='sales_snapshot', help='S3 prefix/folder name (default: sales_snapshot)')
        parser.add_argument('--individual', action='store_true', help='Upload files individually instead of combining (default: combine into one Parquet)')
        parser.add_argument('--upload-originals', action='store_true', help='Also upload original Excel files to Bronze/raw/')
        args = parser.parse_args()
        folder = args.folder
        prefix = args.prefix
        combine = not args.individual
        upload_originals = args.upload_originals
    elif folder is None:
        raise ValueError("Missing required argument: folder")
    # Nếu Airflow truyền combine hoặc upload_originals qua kwargs, ưu tiên kwargs
    if 'combine' in kwargs:
        combine = kwargs['combine']
    if 'upload_originals' in kwargs:
        upload_originals = kwargs['upload_originals']

    # Print banner
    print("""
    ╔═══════════════════════════════════════════════════════╗
    ║     SALES SNAPSHOT BATCH INGESTION                   ║
    ║     SME Pulse Lakehouse (Bronze Layer)               ║
    ╚═══════════════════════════════════════════════════════╝
    """)

    # Initialize ingestion
    ingestion = BatchIngestionMinIO()
    ingestion.upload_originals = upload_originals
    # Connect to MinIO
    if not ingestion.connect():
        if __name__ == "__main__":
            sys.exit(1)
        return False
    # Batch ingest
    success = ingestion.ingest_batch(
        folder_path=folder,
        prefix=prefix,
        combine=combine,
        upload_originals=upload_originals
    )
    if __name__ == "__main__":
        sys.exit(0 if success else 1)
    return success


if __name__ == "__main__":
    main()
