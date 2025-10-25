"""
Download Kaggle dataset using kagglehub
Compatible with both CSV and Excel files

Usage:
    python download_kaggle_dataset.py
"""

import kagglehub
from kagglehub import KaggleDatasetAdapter
import os
import shutil
from pathlib import Path

def download_sales_inventory_dataset():
    """Download Sales and Inventory Snapshot dataset"""
    
    print("="*70)
    print("📦 DOWNLOADING KAGGLE DATASET")
    print("="*70)
    print("Dataset: sales-and-inventory-snapshot-data")
    print("Owner: tienanh2003")
    print("="*70)
    
    try:
        # Download dataset using kagglehub (downloads to cache)
        print("\n⬇️  Downloading from Kaggle...")
        path = kagglehub.dataset_download("tienanh2003/sales-and-inventory-snapshot-data")
        
        print(f"✅ Downloaded to: {path}")
        
        # List files in downloaded dataset
        print("\n📂 Files in dataset:")
        files = list(Path(path).glob("*"))
        for file in files:
            size_mb = file.stat().st_size / (1024 * 1024)
            print(f"   - {file.name} ({size_mb:.2f} MB)")
        
        # Copy files to data/raw folder
        project_root = Path(__file__).parent.parent
        raw_data_folder = project_root / "data" / "raw"
        raw_data_folder.mkdir(parents=True, exist_ok=True)
        
        print(f"\n📁 Copying to: {raw_data_folder}")
        
        copied_files = []
        for file in files:
            if file.is_file() and file.suffix in ['.csv', '.xlsx', '.xls']:
                dest = raw_data_folder / file.name
                shutil.copy2(file, dest)
                print(f"   ✅ Copied: {file.name}")
                copied_files.append(dest)
        
        print("\n" + "="*70)
        print("✅ DOWNLOAD COMPLETE!")
        print("="*70)
        
        print("\n📋 Next steps:")
        print("\n1️⃣  Ingest CSV file (Sales Data):")
        print(f'   python ingest_kaggle_to_minio.py --file "{copied_files[0]}" --prefix kaggle_sales')
        
        if len(copied_files) > 1:
            print("\n2️⃣  Ingest Excel file (Inventory EOQ):")
            print(f'   python ingest_kaggle_to_minio.py --file "{copied_files[1]}" --prefix kaggle_inventory')
        
        print("\n3️⃣  Check MinIO Console:")
        print("   http://localhost:9001 (minioadmin / minioadmin123)")
        print("   Navigate to 'bronze' bucket\n")
        
        return copied_files
        
    except Exception as e:
        print(f"\n❌ Error downloading dataset: {e}")
        print("\n💡 Make sure you have:")
        print("   1. Kaggle account")
        print("   2. API credentials in ~/.kaggle/kaggle.json")
        print("   3. Accepted dataset rules on Kaggle website")
        return []


if __name__ == "__main__":
    download_sales_inventory_dataset()