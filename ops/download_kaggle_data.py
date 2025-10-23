"""
Download Vietnam Retail Dataset from Kaggle
https://www.kaggle.com/datasets/tienanh2003/sales-and-inventory-snapshot-data

⚠️  NOTE: Kaggle only allows downloading the ENTIRE dataset (196 MB)
   You cannot download individual files via API.
   
   OPTIONS:
   1. Manual: Download 1 sample CSV for testing from Kaggle website
   2. API: Download full dataset (all 38 files) using this script
"""
import os
import sys
import zipfile
from pathlib import Path

def download_dataset():
    """
    Download FULL dataset using Kaggle API (196 MB - all 38 files)
    
    Prerequisites:
    - pip install kaggle
    - Setup ~/.kaggle/kaggle.json with API credentials
      Get token from: https://www.kaggle.com/settings → API → Create New Token
    """
    try:
        import kaggle
        
        dataset_name = "tienanh2003/sales-and-inventory-snapshot-data"
        download_path = Path(__file__).parent.parent / "data"
        download_path.mkdir(exist_ok=True)
        
        print(f"📥 Downloading FULL dataset: {dataset_name}")
        print(f"📦 Size: 196 MB (38 files)")
        print(f"📁 Destination: {download_path.absolute()}")
        print(f"⏳ This will take 2-5 minutes depending on internet speed...\n")
        
        kaggle.api.dataset_download_files(
            dataset_name,
            path=str(download_path),
            unzip=True
        )
        
        print("\n✅ Download completed!")
        print(f"📁 Data location: {download_path.absolute()}")
        
        # List downloaded files
        sales_dir = download_path / "InventoryAndSale_snapshot_data" / "Sales_snapshot_data"
        if sales_dir.exists():
            csv_files = list(sales_dir.glob("*.csv"))
            print(f"\n📂 Sales CSV files found: {len(csv_files)}")
            for csv_file in sorted(csv_files)[:5]:  # Show first 5
                size_mb = csv_file.stat().st_size / (1024 * 1024)
                print(f"  ✓ {csv_file.name} ({size_mb:.2f} MB)")
            if len(csv_files) > 5:
                print(f"  ... and {len(csv_files) - 5} more files")
        
        print("\n🚀 Next step: Run ingest script")
        print("   docker exec sme-airflow python /opt/ops/ingest_bronze.py --all-files")
        
    except ImportError:
        print("❌ Error: 'kaggle' module not installed\n")
        print("=" * 70)
        print("📝 MANUAL DOWNLOAD STEPS (Recommended for testing):")
        print("=" * 70)
        print("1. Visit: https://www.kaggle.com/datasets/tienanh2003/sales-and-inventory-snapshot-data")
        print("2. Click 'Download' button (196 MB) - downloads ALL files")
        print("3. Extract ZIP to: D:\\Project\\SME_PULSE\\SME_Pulse\\data\\")
        print("")
        print("OR download 1 sample file for testing:")
        print("   a) Click 'Data Explorer' on Kaggle page")
        print("   b) Navigate to: InventoryAndSale_snapshot_data/Sales_snapshot_data/")
        print("   c) Click any CSV file (e.g., Sales_01_2022.csv)")
        print("   d) Save to: data/InventoryAndSale_snapshot_data/Sales_snapshot_data/")
        print("")
        print("=" * 70)
        print("📝 OR INSTALL KAGGLE API:")
        print("=" * 70)
        print("  pip install kaggle")
        print("  # Get API token from: https://www.kaggle.com/settings")
        print("  # Save kaggle.json to: ~/.kaggle/kaggle.json (Linux/Mac)")
        print("  #                  or: C:\\Users\\<username>\\.kaggle\\kaggle.json (Windows)")
        print("  python ops/download_kaggle_data.py")
        sys.exit(1)
    
    except Exception as e:
        print(f"❌ Error downloading: {e}\n")
        print("=" * 70)
        print("📝 MANUAL DOWNLOAD ALTERNATIVE:")
        print("=" * 70)
        print("1. Visit: https://www.kaggle.com/datasets/tienanh2003/sales-and-inventory-snapshot-data")
        print("2. Download manually (196 MB)")
        print("3. Extract to: D:\\Project\\SME_PULSE\\SME_Pulse\\data\\")
        print("")
        print("Expected structure:")
        print("  data/")
        print("  └── InventoryAndSale_snapshot_data/")
        print("      ├── Sales_snapshot_data/        (19 CSV files)")
        print("      ├── Inventory_snapshot_data/    (12 CSV files)")
        print("      └── MasterData/                 (7 CSV files)")
        sys.exit(1)

if __name__ == "__main__":
    download_dataset()
