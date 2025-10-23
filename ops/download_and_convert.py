"""
Download Kaggle dataset và convert Excel sang CSV automatically
"""
from pathlib import Path
import sys
import zipfile

def download_and_convert():
    """
    Download full dataset từ Kaggle và convert tất cả Excel files sang CSV
    """
    
    # Check pandas + openpyxl
    try:
        import pandas as pd
        print("✅ pandas installed")
    except ImportError:
        print("❌ pandas not installed. Installing...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas", "openpyxl"])
        import pandas as pd
    
    # Setup paths
    script_dir = Path(__file__).parent.parent
    data_dir = script_dir / "data"
    data_dir.mkdir(exist_ok=True)
    
    print("=" * 70)
    print("📥 KAGGLE DATASET DOWNLOAD & CONVERT")
    print("=" * 70)
    
    # Try Kaggle API first
    try:
        import kaggle
        
        dataset_name = "tienanh2003/sales-and-inventory-snapshot-data"
        print(f"\n🔄 Downloading from Kaggle API: {dataset_name}")
        print(f"📦 Size: 196 MB")
        print(f"⏳ Please wait 2-5 minutes...\n")
        
        kaggle.api.dataset_download_files(
            dataset_name,
            path=str(data_dir),
            unzip=True
        )
        
        print("\n✅ Download completed!")
        
    except ImportError:
        print("\n⚠️  Kaggle API not installed - skipping auto download")
        print("   Checking if files already downloaded...")
    
    except Exception as e:
        print(f"\n⚠️  Kaggle API error: {e}")
        print("   Continuing with conversion if files exist...")
    
    # Convert Excel to CSV
    print("\n" + "=" * 70)
    print("🔄 CONVERTING EXCEL FILES TO CSV")
    print("=" * 70)
    
    sales_dir = data_dir / "InventoryAndSale_snapshot_data" / "Sales_snapshot_data"
    
    if not sales_dir.exists():
        print(f"❌ Sales directory not found: {sales_dir}")
        print("   Please check extraction path")
        return
    
    # Find all Excel files
    excel_files = sorted(list(sales_dir.glob("*.xlsx")) + list(sales_dir.glob("*.xls")))
    
    if not excel_files:
        print("ℹ️  No Excel files found (maybe already converted?)")
        csv_files = list(sales_dir.glob("*.csv"))
        if csv_files:
            print(f"✅ Found {len(csv_files)} CSV files already")
        return
    
    print(f"\n📊 Found {len(excel_files)} Excel files")
    
    converted = 0
    errors = []
    
    for idx, excel_file in enumerate(excel_files, 1):
        print(f"\n[{idx}/{len(excel_files)}] Processing: {excel_file.name}")
        
        try:
            # Read Excel
            df = pd.read_excel(excel_file, engine='openpyxl')
            print(f"   ✓ Read {len(df):,} rows × {len(df.columns)} columns")
            
            # Generate clean CSV filename
            # TT T01-2022_split_1.xlsx → TT_T01_2022_split_1.csv
            csv_name = excel_file.stem.replace(" ", "_").replace("-", "_") + ".csv"
            csv_path = sales_dir / csv_name
            
            # Save as CSV
            df.to_csv(csv_path, index=False, encoding='utf-8')
            size_mb = csv_path.stat().st_size / (1024 * 1024)
            print(f"   ✓ Saved: {csv_name} ({size_mb:.2f} MB)")
            
            # Delete Excel file to save space
            excel_file.unlink()
            print(f"   ✓ Deleted Excel file")
            
            converted += 1
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            errors.append((excel_file.name, str(e)))
    
    # Summary
    print("\n" + "=" * 70)
    print("✅ CONVERSION COMPLETE")
    print("=" * 70)
    print(f"Converted: {converted}/{len(excel_files)} files")
    
    if errors:
        print(f"\n⚠️  Errors: {len(errors)}")
        for filename, error in errors:
            print(f"   - {filename}: {error}")
    
    # List final CSV files
    csv_files = sorted(list(sales_dir.glob("*.csv")))
    if csv_files:
        print(f"\n📂 CSV files ready: {len(csv_files)}")
        total_size = sum(f.stat().st_size for f in csv_files) / (1024 * 1024)
        print(f"   Total size: {total_size:.2f} MB")
        
        print("\n🚀 Next step:")
        print("   docker exec sme-airflow python /opt/ops/check_dataset.py")
        print("   docker exec sme-airflow python /opt/ops/ingest_bronze.py --all-files")

if __name__ == "__main__":
    download_and_convert()
