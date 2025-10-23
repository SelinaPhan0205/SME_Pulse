"""
Check current dataset status and guide next steps
"""
from pathlib import Path

def check_dataset_status():
    """Check what data files are currently available"""
    
    script_dir = Path(__file__).parent.parent
    data_dir = script_dir / "data"
    sales_dir = data_dir / "InventoryAndSale_snapshot_data" / "Sales_snapshot_data"
    
    print("=" * 70)
    print("📊 KAGGLE DATASET STATUS CHECK")
    print("=" * 70)
    
    # Check data directory
    if not data_dir.exists():
        print(f"❌ Data directory not found: {data_dir.absolute()}")
        print("\n📝 Action needed: Create data/ folder")
        print(f"   mkdir {data_dir.absolute()}")
        return False
    
    print(f"✅ Data directory exists: {data_dir.absolute()}")
    
    # Check sales directory
    if not sales_dir.exists():
        print(f"❌ Sales directory not found: {sales_dir.absolute()}")
        print("\n📝 Action needed:")
        print("   1. Download dataset from Kaggle")
        print("   2. Extract to data/ folder")
        print("   3. Ensure structure: data/InventoryAndSale_snapshot_data/Sales_snapshot_data/")
        return False
    
    print(f"✅ Sales directory exists: {sales_dir.absolute()}")
    
    # Count CSV files
    csv_files = sorted(sales_dir.glob("*.csv"))
    
    if not csv_files:
        print(f"\n❌ No CSV files found in {sales_dir.name}")
        print("\n📝 Action needed: Download at least 1 CSV file for testing")
        return False
    
    print(f"\n📂 Found {len(csv_files)} CSV file(s):")
    print("-" * 70)
    
    total_size_mb = 0
    for idx, csv_file in enumerate(csv_files, 1):
        size_mb = csv_file.stat().st_size / (1024 * 1024)
        total_size_mb += size_mb
        print(f"  {idx:2d}. {csv_file.name:<30s} ({size_mb:6.2f} MB)")
    
    print("-" * 70)
    print(f"Total size: {total_size_mb:.2f} MB")
    
    # Recommendations
    print("\n" + "=" * 70)
    print("🚀 NEXT STEPS:")
    print("=" * 70)
    
    if len(csv_files) == 1:
        print(f"✅ You have 1 CSV file - perfect for testing!")
        print(f"\n📝 Test ingest with this file:")
        print(f"   docker exec sme-airflow python /opt/ops/ingest_bronze.py --file {csv_files[0].name}")
        print(f"\n📝 If test successful, download remaining 18 files:")
        print(f"   Option 1: Download full dataset (196 MB) from Kaggle")
        print(f"   Option 2: Use Kaggle API - python ops/download_kaggle_data.py")
        
    elif len(csv_files) < 19:
        print(f"⚠️  You have {len(csv_files)} files out of 19 total")
        print(f"\n📝 Test with current files:")
        print(f"   docker exec sme-airflow python /opt/ops/ingest_bronze.py --all-files")
        print(f"\n📝 To get all 19 files:")
        print(f"   Download full dataset from Kaggle (196 MB)")
        
    else:
        print(f"✅ You have all 19 CSV files!")
        print(f"\n📝 Recommended: Test with 1 file first:")
        print(f"   docker exec sme-airflow python /opt/ops/ingest_bronze.py --file {csv_files[0].name}")
        print(f"\n📝 Then process all files:")
        print(f"   docker exec sme-airflow python /opt/ops/ingest_bronze.py --all-files --batch-size 200")
    
    print("\n" + "=" * 70)
    
    return True

if __name__ == "__main__":
    check_dataset_status()
