#!/bin/bash
# =====================================================
# Bootstrap Lakehouse Infrastructure
# =====================================================
# Purpose: Khởi tạo lại toàn bộ schemas Iceberg sau khi reset Docker
# Usage: ./tools/bootstrap_lakehouse.sh
# =====================================================

set -e  # Exit on error

echo "=========================================="
echo "🚀 Bootstrap Lakehouse Infrastructure"
echo "=========================================="

# Wait for Trino to be ready
echo "⏳ Waiting for Trino to be healthy..."
until docker exec sme-trino curl -f http://localhost:8080/v1/info > /dev/null 2>&1; do
    echo "   Trino not ready yet, waiting 5s..."
    sleep 5
done
echo "✅ Trino is healthy"

# Step 1: Create schemas (bronze/silver/gold)
echo ""
echo "📁 Step 1: Creating Iceberg schemas..."
docker exec -i sme-trino trino --execute "$(cat sql/00_bootstrap_schemas.sql)"
echo "✅ Schemas created"

# Step 2: Verify
echo ""
echo "🔍 Step 2: Verifying schemas..."
docker exec -i sme-trino trino --execute "SHOW SCHEMAS FROM sme_lake;"
echo ""

echo "=========================================="
echo "✅ Bootstrap completed successfully!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Run ingest scripts to populate bronze layer"
echo "  2. Run dbt to build silver/gold layers"
echo "  3. Trigger Airflow DAG for full pipeline"
