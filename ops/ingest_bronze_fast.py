#!/usr/bin/env python3
"""
===================================================
Fast Ingest - CSV → DataFrame → INSERT DIRECT
===================================================
Mục đích:
  - Đọc CSV → Pandas DataFrame
  - Transform Bronze schema
  - Batch INSERT trực tiếp (không dùng S3)
  - NHANH: 1000-2000 rows/sec

Usage:
  python ops/ingest_bronze_fast.py --all-files
  python ops/ingest_bronze_fast.py --file TT_T01_2022_split_1.csv
===================================================
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
import hashlib
import pandas as pd
import trino

# Trino config
TRINO_HOST = "trino"
TRINO_PORT = 8080
TRINO_USER = "airflow"
TRINO_CATALOG = "iceberg"
TRINO_SCHEMA = "bronze"


def get_trino_connection():
    """Tạo connection tới Trino"""
    conn = trino.dbapi.connect(
        host=TRINO_HOST,
        port=TRINO_PORT,
        user=TRINO_USER,
        catalog=TRINO_CATALOG,
        schema=TRINO_SCHEMA,
        http_scheme="http"
    )
    return conn


def transform_csv_to_bronze(csv_file_path: Path) -> pd.DataFrame:
    """
    Đọc CSV và transform sang Bronze schema
    
    Args:
        csv_file_path: Path to CSV file
    
    Returns:
        DataFrame in Bronze format
    """
    print(f"📖 Reading CSV: {csv_file_path.name}")
    
    # Đọc CSV
    df = pd.read_csv(csv_file_path, encoding='utf-8')
    print(f"✅ Read {len(df):,} rows × {len(df.columns)} columns")
    
    # Transform sang Bronze schema
    now = datetime.now().isoformat(timespec='microseconds')
    
    bronze_rows = []
    for i, (idx, row) in enumerate(df.iterrows(), 1):
        row_dict = row.to_dict()
        row_json = json.dumps(row_dict, default=str)
        row_hash = hashlib.md5(row_json.encode()).hexdigest()
        
        bronze_rows.append({
            'id': i,
            'event_id': f"kaggle_{csv_file_path.stem}_{i}_{row_hash[:8]}",
            'source': 'KAGGLE_VIETNAM_RETAIL',
            'domain': 'sales',
            'org_id': str(row_dict.get('Store_ID', 'UNKNOWN')),
            'updated_at': now,
            'ingested_at': now,
            'hash': row_hash,
            'payload_json': row_json
        })
    
    bronze_df = pd.DataFrame(bronze_rows)
    print(f"✅ Transformed to Bronze schema: {len(bronze_df):,} rows")
    
    return bronze_df


def batch_insert_to_trino(df: pd.DataFrame, batch_size: int = 500):
    """
    Insert DataFrame to Trino in batches (FAST!)
    
    Args:
        df: Bronze DataFrame
        batch_size: Rows per batch
    """
    conn = get_trino_connection()
    cursor = conn.cursor()
    
    try:
        print(f"💾 Inserting {len(df):,} rows (batch_size={batch_size})...")
        
        start_time = datetime.now()
        inserted = 0
        
        for batch_idx in range(0, len(df), batch_size):
            batch = df.iloc[batch_idx:batch_idx+batch_size]
            
            # Build VALUES string for this batch
            values_list = []
            for _, row in batch.iterrows():
                # Escape single quotes in strings
                event_id = row['event_id'].replace("'", "''")
                source = row['source'].replace("'", "''")
                domain = row['domain'].replace("'", "''")
                org_id = row['org_id'].replace("'", "''")
                hash_val = row['hash'].replace("'", "''")
                payload = row['payload_json'].replace("'", "''")
                
                # Trino cần format: YYYY-MM-DD HH:MM:SS.mmm (không có 'T' và chỉ 3 chữ số microseconds)
                updated_ts = row['updated_at'].replace('T', ' ')[:23]
                ingested_ts = row['ingested_at'].replace('T', ' ')[:23]
                
                val = f"({row['id']}, '{event_id}', '{source}', '{domain}', '{org_id}', TIMESTAMP '{updated_ts}', TIMESTAMP '{ingested_ts}', '{hash_val}', '{payload}')"
                values_list.append(val)
            
            # Insert batch
            sql = f"""
            INSERT INTO iceberg.bronze.transactions_raw
            (id, event_id, source, domain, org_id, updated_at, ingested_at, hash, payload_json)
            VALUES {','.join(values_list)}
            """
            
            cursor.execute(sql)
            inserted += len(batch)
            
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = inserted / elapsed if elapsed > 0 else 0
            pct = (inserted / len(df)) * 100
            print(f"  {inserted:,}/{len(df):,} ({pct:.1f}%) - {rate:.0f} rows/sec")
        
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n✅ Inserted {len(df):,} in {elapsed:.1f}s ({len(df)/elapsed:.0f} rows/sec)")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def verify_data():
    """Verify data in Bronze table"""
    conn = get_trino_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT COUNT(*) as total FROM iceberg.bronze.transactions_raw")
        result = cursor.fetchone()
        total = result[0] if result else 0
        
        cursor.execute("SELECT COUNT(*), source FROM iceberg.bronze.transactions_raw GROUP BY source")
        results = cursor.fetchall()
        
        print(f"\n📊 Total rows: {total:,}")
        print(f"📊 Counts by source:")
        for row in results:
            print(f"   {row[1]}: {row[0]:,}")
        
    except Exception as e:
        print(f"⚠️  Could not verify: {e}")
    finally:
        cursor.close()
        conn.close()


def find_sales_csv_files(data_dir: Path) -> list:
    """Find all CSV files"""
    sales_dir = data_dir / "InventoryAndSale_snapshot_data" / "Sales_snapshot_data"
    
    if not sales_dir.exists():
        print(f"❌ Sales directory not found: {sales_dir}")
        return []
    
    csv_files = sorted(sales_dir.glob("*.csv"))
    print(f"📂 Found {len(csv_files)} CSV files")
    
    return csv_files


def main():
    parser = argparse.ArgumentParser(description="Fast ingest CSV to Iceberg Bronze")
    parser.add_argument("--file", help="Specific CSV file")
    parser.add_argument("--all-files", action="store_true", help="All CSV files")
    parser.add_argument("--data-dir", default="data", help="Data directory")
    parser.add_argument("--batch-size", type=int, default=500, help="Batch size (default: 500)")
    
    args = parser.parse_args()
    
    script_dir = Path(__file__).parent.parent
    data_dir = script_dir / args.data_dir
    
    print(f"🚀 Fast Ingest - CSV → DataFrame → Trino (Direct)")
    print(f"📁 Data directory: {data_dir.absolute()}\n")
    
    # Find CSV files
    csv_files = []
    if args.file:
        csv_path = data_dir / "InventoryAndSale_snapshot_data" / "Sales_snapshot_data" / args.file
        csv_files = [csv_path] if csv_path.exists() else []
    elif args.all_files:
        csv_files = find_sales_csv_files(data_dir)
    else:
        print("❌ Use --file <name> or --all-files")
        return
    
    if not csv_files:
        print("❌ No CSV files found")
        return
    
    # Process each CSV
    for csv_file in csv_files:
        print(f"\n{'='*70}")
        print(f"Processing: {csv_file.name}")
        print(f"{'='*70}")
        
        try:
            # Transform CSV → Bronze DataFrame
            df = transform_csv_to_bronze(csv_file)
            
            # Insert to Trino
            batch_insert_to_trino(df, batch_size=args.batch_size)
            
        except Exception as e:
            print(f"❌ Error processing {csv_file.name}: {e}")
            continue
    
    # Verify final data
    verify_data()
    print("\n✅ Ingest completed!")


if __name__ == "__main__":
    main()
