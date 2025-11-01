#!/usr/bin/env python3
"""
Export dim_location table to a properly formatted text file with UTF-8 encoding
"""

import subprocess
import pandas as pd
from io import StringIO
from datetime import datetime

# Query via docker exec (avoid port conflict with Airflow)
print("🔍 Querying dim_location table...")
cmd = [
    'docker', 'compose', 'exec', '-T', 'trino', 
    'trino', '--catalog', 'sme_lake', '--schema', 'gold',
    '--output-format', 'CSV_UNQUOTED',
    '--execute', 
    """
    SELECT 
        province_code,
        province_name,
        district_code,
        district_name,
        region_name,
        phone_code,
        district_division_type,
        urban_rural_classification,
        is_major_city
    FROM dim_location
    ORDER BY province_code, district_code
    """
]

result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
if result.returncode != 0:
    print(f"❌ Error: {result.stderr}")
    exit(1)

# Parse CSV output (CSV_UNQUOTED format doesn't include header)
column_names = [
    'province_code', 'province_name', 'district_code', 'district_name',
    'region_name', 'phone_code', 'district_division_type', 
    'urban_rural_classification', 'is_major_city'
]
df = pd.read_csv(StringIO(result.stdout), names=column_names, header=None)

# Export to text file with proper UTF-8 encoding
output_file = "dim_location_full_data.txt"

with open(output_file, 'w', encoding='utf-8') as f:
    # Write header
    f.write("="*120 + "\n")
    f.write("DIM_LOCATION - DANH SÁCH ĐẦY ĐỦ TẤT CẢ QUẬN/HUYỆN VIỆT NAM\n")
    f.write(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"Total Districts: {len(df)}\n")
    f.write("="*120 + "\n\n")
    
    # Write summary by province
    f.write("TỔNG HỢP THEO TỈNH/THÀNH:\n")
    f.write("-"*120 + "\n")
    province_summary = df.groupby(['province_code', 'province_name', 'region_name']).size().reset_index(name='district_count')
    for _, row in province_summary.iterrows():
        f.write(f"[{row['province_code']:>3}] {row['province_name']:<30} | {row['region_name']:<15} | {row['district_count']:>2} quận/huyện\n")
    
    f.write("\n" + "="*120 + "\n\n")
    
    # Write detailed table
    f.write("CHI TIẾT TẤT CẢ QUẬN/HUYỆN:\n")
    f.write("-"*120 + "\n")
    f.write(f"{'P.Code':<8}{'Province Name':<30}{'D.Code':<8}{'District Name':<35}{'Region':<15}{'Phone':<8}{'Type':<12}{'Urban':<12}{'Major':<6}\n")
    f.write("-"*120 + "\n")
    
    for _, row in df.iterrows():
        f.write(
            f"{row['province_code']:<8}"
            f"{row['province_name']:<30}"
            f"{row['district_code']:<8}"
            f"{row['district_name']:<35}"
            f"{row['region_name']:<15}"
            f"{row['phone_code']:<8}"
            f"{row['district_division_type']:<12}"
            f"{row['urban_rural_classification']:<12}"
            f"{str(row['is_major_city']):<6}\n"
        )
    
    f.write("="*120 + "\n")

print(f"✅ Exported to: {output_file}")
print(f"📊 Total rows: {len(df)}")
print(f"📊 Total provinces: {df['province_code'].nunique()}")
