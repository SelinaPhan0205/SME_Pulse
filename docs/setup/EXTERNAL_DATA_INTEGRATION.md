# External Data Integration - Complete Documentation

## Table of Contents
1. [Overview](#overview)
2. [Phase 1: Data Source Analysis & Ingestion](#phase-1-data-source-analysis--ingestion)
3. [Phase 2: Silver Layer Transformation](#phase-2-silver-layer-transformation)
4. [Phase 3: Gold Layer Dimension Tables](#phase-3-gold-layer-dimension-tables)
5. [Phase 4: Airflow Orchestration](#phase-4-airflow-orchestration)
6. [Lessons Learned](#lessons-learned)
7. [Production Checklist](#production-checklist)

---

## Overview

### Objective
Integrate external macro-economic and geographic data sources into the SME Pulse data platform to enrich sales analytics with contextual insights about Vietnam's economic conditions and location hierarchies.

### Data Sources

#### 1. World Bank Open Data API
- **Purpose**: Provide macro-economic indicators for Vietnam
- **Role**: Enable correlation analysis between SME sales performance and national economic trends
- **Update Frequency**: Annually (World Bank publishes data with 1-2 year lag)
- **Selected Indicators**:
  - `NY.GDP.MKTP.CD` - GDP (current US$)
  - `FP.CPI.TOTL.ZG` - Inflation, consumer prices (annual %)
  - `SL.UEM.TOTL.ZS` - Unemployment rate (% of total labor force)

**Business Value**:
- Understand if sales dips correlate with economic downturns
- Benchmark SME performance against national economic health
- Provide context for executive dashboards and strategic planning

#### 2. Vietnam Provinces API (provinces.open-api.vn)
- **Purpose**: Provide standardized location hierarchy (Province → District → Ward)
- **Role**: Enable geographic analysis and location-based sales aggregation
- **Update Frequency**: Rarely (only when administrative boundaries change)
- **Data Structure**: 
  - 63 provinces/cities
  - 691 districts
  - Hierarchical relationships with standardized codes

**Business Value**:
- Aggregate sales by geographic region
- Identify high-performing locations
- Support territory management and expansion planning
- Enable map visualizations in Metabase

### Architecture Pattern: Bronze → Silver → Gold

```
External APIs
    ↓
[Bronze Layer] - Raw data in Parquet (MinIO)
    ↓
[Silver Layer] - Cleaned, typed, deduplicated (Iceberg via dbt)
    ↓
[Gold Layer] - Business-ready dimension tables (Iceberg via dbt)
    ↓
Analytics (Metabase, SQL queries)
```

---

## Phase 1: Data Source Analysis & Ingestion

### Step 1.1: API Exploration & Testing

**World Bank API**:
- Base URL: `https://api.worldbank.org/v2/country/VN/indicator/{indicator_code}`
- Format: `?format=json&per_page=100&date=2014:2024`
- Response structure: Nested JSON with pagination
- Challenge: Need to extract year-over-year data for multiple indicators

**Vietnam Provinces API**:
- Base URL: `https://provinces.open-api.vn/api/?depth={1|2|3}`
- Depth levels:
  - 1: Provinces only
  - 2: Provinces + Districts (chosen for our use case)
  - 3: Provinces + Districts + Wards
- Response: Single JSON array with nested district objects

### Step 1.2: Ingestion Script Design

**Key Design Decisions**:

1. **Parquet Format**: Chosen for columnar storage efficiency and Trino compatibility
2. **MinIO Bronze Layer**: Store raw data with date-stamped filenames for audit trail
3. **Incremental Approach**: Each ingestion creates new dated file (append-only)
4. **Error Handling**: Retry logic with exponential backoff for API calls

**Implementation Pattern**:
```python
# General structure for both scripts
def ingest_data():
    1. Connect to MinIO (using service name 'minio' for Docker)
    2. Fetch data from external API
    3. Parse and flatten nested JSON structures
    4. Convert to Pandas DataFrame
    5. Write to Parquet with PyArrow engine
    6. Upload to MinIO with dated filename
    7. Log success metrics
```

**World Bank Script** (`ops/external_sources/ingest_world_bank.py`):
- Fetches 3 indicators in parallel
- Flattens nested `[1]` array structure
- Pivots data to have one row per year
- Output: `bronze/raw/world_bank/YYYYMMDD.parquet`

**Provinces Script** (`ops/external_sources/ingest_provinces.py`):
- Fetches provinces with depth=2
- Separates provinces and districts into 2 files
- Maintains parent-child relationships via `province_code`
- Output: 
  - `bronze/raw/vietnam_provinces/provinces/YYYYMMDD.parquet`
  - `bronze/raw/vietnam_provinces/districts/YYYYMMDD.parquet`

### Step 1.3: Manual Testing

```bash
# Test World Bank ingestion
python ops/external_sources/ingest_world_bank.py

# Test Provinces ingestion
python ops/external_sources/ingest_provinces.py

# Verify in MinIO
mc ls local/sme-lake/bronze/raw/world_bank/
mc ls local/sme-lake/bronze/raw/vietnam_provinces/
```

**Validation Checks**:
- ✅ Files created in MinIO with correct paths
- ✅ Parquet files readable by Trino
- ✅ Row counts match API responses (30 rows for WB, 63+691 for provinces)
- ✅ Data types correctly inferred

---

## Phase 2: Silver Layer Transformation

### Step 2.1: dbt Model Design

**Silver Layer Purpose**: 
- Clean and standardize raw data
- Apply consistent typing
- Deduplicate based on business logic
- Make data queryable and testable

#### Model 1: `stg_wb_indicators` (World Bank staging)

**Location**: `dbt/models/silver/external/stg_wb_indicators.sql`

**Materialization**: Incremental
- **Why**: World Bank data grows over time (new years added)
- **Unique Key**: `year || indicator_code`
- **Strategy**: Append new data, avoid reprocessing historical records

**Transformations**:
1. Read from MinIO Parquet files using Iceberg external table pattern
2. Filter out null values and invalid years
3. Cast data types (year as INTEGER, value as DOUBLE)
4. Add metadata columns: `source`, `ingested_at`
5. Deduplicate using ROW_NUMBER() to keep latest value per year-indicator

**Data Quality**:
- Not-null constraint on `year`
- Not-null constraint on `indicator_code`
- Accepted values for `indicator_code` (3 specific codes)

#### Model 2: `stg_vietnam_locations` (Provinces/Districts staging)

**Location**: `dbt/models/silver/external/stg_vietnam_locations.sql`

**Materialization**: Table
- **Why**: Location data is small and changes rarely, full refresh is fast
- **Strategy**: Rebuild entire table on each run

**Transformations**:
1. Union provinces and districts from separate Parquet files
2. Standardize location hierarchy with `location_level` field
3. Create surrogate key: `location_code` (province or district code)
4. Handle parent relationships (`parent_location_code`)
5. Enrich with metadata: `phone_code`, `division_type`, `codename`

**Hierarchy Structure**:
```
Province (level=1)
  ├── District (level=2, parent=province_code)
  ├── District (level=2, parent=province_code)
  └── District (level=2, parent=province_code)
```

**Data Quality**:
- Not-null on `location_code`
- Not-null on `location_name`
- Accepted values for `location_level` (1 or 2)
- Relationship test: `parent_location_code` must exist in same table

### Step 2.2: dbt Execution

```bash
# Run silver models
dbt run --select silver.external

# Run tests
dbt test --select silver.external

# Check results
trino --execute "SELECT * FROM iceberg.silver.stg_wb_indicators LIMIT 10"
trino --execute "SELECT COUNT(*) FROM iceberg.silver.stg_vietnam_locations"
```

**Validation Results**:
- ✅ `stg_wb_indicators`: 30 rows (10 years × 3 indicators)
- ✅ `stg_vietnam_locations`: 754 rows (63 provinces + 691 districts)
- ✅ All dbt tests passed (schema, not-null, relationships)

---

## Phase 3: Gold Layer Dimension Tables

### Step 3.1: Business Requirements

**Gold Layer Purpose**:
- Create analytics-ready dimension tables
- Apply business logic and calculations
- Optimize for query performance
- Support star schema modeling

#### Dimension 1: `dim_macro_indicators` (Time-series fact table)

**Business Requirements**:
- Analysts need to compare current year vs previous year (YoY analysis)
- Need pivot format: one column per indicator for easy querying
- Must include calculated fields: YoY change, growth rate

**Design Decisions**:
1. **Grain**: One row per year
2. **Columns**: Separate columns for GDP, Inflation, Unemployment
3. **Calculated Fields**: 
   - Previous year values using LAG() window function
   - Absolute change (current - previous)
   - Percentage change ((current - previous) / previous * 100)
4. **Time Dimension**: Include year as both INTEGER and DATE for flexibility

**SQL Pattern**:
```sql
-- Pivot indicators to columns
WITH pivoted AS (
  SELECT year,
    MAX(CASE WHEN indicator = 'GDP' THEN value END) as gdp,
    MAX(CASE WHEN indicator = 'Inflation' THEN value END) as inflation,
    MAX(CASE WHEN indicator = 'Unemployment' THEN value END) as unemployment
  FROM stg_wb_indicators
  GROUP BY year
)
-- Add YoY calculations
SELECT 
  year,
  gdp,
  LAG(gdp) OVER (ORDER BY year) as gdp_prev_year,
  gdp - LAG(gdp) OVER (ORDER BY year) as gdp_yoy_change,
  -- ... similar for inflation and unemployment
FROM pivoted
```

**Output**: 10 rows (one per year 2014-2023) with 13+ columns

#### Dimension 2: `dim_location` (SCD Type 2 dimension)

**Business Requirements**:
- Support geographic aggregation (rollup from district to province)
- Handle administrative boundary changes over time (future-proof)
- Enable geographic filtering in BI tools

**Design Decisions**:
1. **Grain**: One row per district (691 rows)
2. **Hierarchy Columns**: 
   - `province_code`, `province_name`
   - `district_code`, `district_name` (NULL for province-level rows)
3. **SCD Type 2 Fields**:
   - `effective_from`: When this version became valid
   - `effective_to`: When this version expired (NULL for current)
   - `is_current`: Boolean flag for active version
4. **Sort Key**: For map visualizations and alphabetical filters

**SQL Pattern**:
```sql
WITH current_locations AS (
  SELECT 
    COALESCE(district_code, province_code) as location_key,
    province_code,
    province_name,
    district_code,
    district_name,
    location_level,
    CURRENT_DATE as effective_from,
    NULL as effective_to,
    TRUE as is_current
  FROM stg_vietnam_locations
)
SELECT * FROM current_locations
ORDER BY province_name, district_name NULLS FIRST
```

**Output**: 691 rows (all districts with parent province info)

### Step 3.2: dbt Execution & Testing

```bash
# Run gold models
dbt run --select gold.external

# Run comprehensive tests
dbt test --select gold.external

# Export for validation
dbt run-operation export_to_csv --args '{model: dim_macro_indicators, output: /tmp/dim_macro.csv}'
```

**Data Quality Tests**:
- ✅ Not-null on all key fields
- ✅ Unique constraint on surrogate keys
- ✅ Referential integrity (child → parent relationships)
- ✅ Custom tests for YoY calculation logic
- ✅ Row count validation (691 districts, 10 years)

---

## Phase 4: Airflow Orchestration

### Step 4.1: Infrastructure Preparation

**Prerequisites Check**:
1. ✅ Airflow 2.9.3 running with LocalExecutor
2. ✅ Services: postgres (metadata), redis (celery), minio, trino, hive-metastore
3. ✅ Volumes mounted: `./airflow/dags`, `./ops`, `./dbt`
4. ✅ Airflow user has access to dbt container

**Package Requirements**:
- `minio` - For MinIO connectivity checks
- `requests` - For API calls to external sources
- `pandas` - For DataFrame operations in scripts
- `pyarrow` - For Parquet file handling
- `dbt-core`, `dbt-trino` - Already installed

**Dockerfile Update**:
```dockerfile
# Added to airflow/Dockerfile
RUN pip install --no-cache-dir \
    dbt-core \
    dbt-trino \
    boto3 \
    openpyxl \
    pyarrow \
    minio \
    requests \
    pandas
```

**Image Rebuild**:
```bash
docker compose build airflow-scheduler airflow-webserver
docker compose up -d
```

### Step 4.2: DAG Design

**DAG Name**: `sme_pulse_external_data_sync`

**Schedule**: Monthly on 1st day at 00:00 UTC
- **Rationale**: World Bank data updates annually, provinces rarely change
- **Cron**: `"0 0 1 * *"`

**DAG Configuration**:
```python
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': True,  # Production setting
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5)
}
```

**Task Flow Architecture**:

```
verify_external_sources (PythonOperator)
    ↓
check_data_freshness (PythonOperator)
    ↓
[ingest_external_data] TaskGroup
    ├─ ingest_world_bank (PythonOperator)
    └─ ingest_provinces (PythonOperator)
    ↓
[dbt_silver_external] TaskGroup
    ├─ dbt_run_silver_external (BashOperator)
    └─ dbt_test_silver_external (BashOperator)
    ↓
[dbt_gold_external] TaskGroup
    ├─ dbt_run_gold_external (BashOperator)
    └─ dbt_test_gold_external (BashOperator)
    ↓
log_summary (PythonOperator)
```

### Step 4.3: Task Implementation Details

#### Task 1: `verify_external_sources`
**Purpose**: Smoke test to verify all external dependencies before starting
**Logic**:
1. Test World Bank API reachability (simple GET request)
2. Test Vietnam Provinces API reachability
3. Test MinIO connectivity (list buckets)
4. Verify bucket `sme-lake` exists
5. Raise exception if any check fails

**Why Important**: Fail fast if external services are down, don't waste resources

#### Task 2: `check_data_freshness`
**Purpose**: Skip ingestion if data was recently updated
**Logic**:
1. List objects in MinIO bronze paths
2. Check last modified timestamp
3. If latest file < 30 days old, log skip message and continue
4. If > 30 days or no file exists, proceed to ingestion

**Why Important**: Avoid unnecessary API calls and reduce costs

#### Task 3-4: `ingest_world_bank` and `ingest_provinces`
**Purpose**: Execute ingestion scripts dynamically
**Implementation Pattern**:
```python
def _run_python_script(script_path, script_name):
    """
    Execute Python script either via importlib (preferred) or subprocess
    """
    try:
        # Try importlib first (cleaner, better error messages)
        spec = importlib.util.spec_from_file_location(script_name, script_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as e:
        # Fallback to subprocess if importlib fails
        result = subprocess.run(
            ['python', script_path],
            capture_output=True,
            text=True,
            check=True
        )
        print(result.stdout)
```

**Parallelism**: These tasks run in parallel using TaskGroup
- World Bank ingestion: ~27 seconds
- Provinces ingestion: ~14 seconds
- Total time saved: ~15 seconds per run

#### Task 5-6: `dbt_run_silver_external` and `dbt_test_silver_external`
**Purpose**: Run dbt models and tests in dbt container
**Implementation**:
```bash
docker compose exec -T dbt bash -c "cd /opt/dbt && dbt run --select silver.external"
docker compose exec -T dbt bash -c "cd /opt/dbt && dbt test --select silver.external"
```

**Key Points**:
- `-T` flag: Required for non-interactive execution in Airflow
- `cd /opt/dbt`: Ensure correct working directory for dbt
- `--select`: Run only external data models (not sales models)

**Expected Output**:
- 2 models built successfully
- 8+ tests passed
- Total duration: ~13 seconds

#### Task 7-8: `dbt_run_gold_external` and `dbt_test_gold_external`
**Purpose**: Build gold dimension tables and validate
**Same pattern as silver tasks**

**Expected Output**:
- 2 models built successfully
- 10+ tests passed
- Total duration: ~9 seconds

#### Task 9: `log_summary`
**Purpose**: Log final metrics and success message
**Logic**:
1. Query row counts from Trino
2. Log summary: "Successfully synced X indicators, Y locations"
3. Can be extended to send notifications (Slack, email)

### Step 4.4: DAG File Structure

**Location**: `airflow/dags/sme_pulse_external_data_sync.py`

**Key Components**:
1. **Imports**: Standard Airflow operators + custom logic
2. **Constants**: API URLs, script paths, MinIO config
3. **Helper Functions**: `_run_python_script`, `_verify_external_sources`, etc.
4. **DAG Definition**: Using `@dag` decorator or traditional DAG() constructor
5. **Task Definitions**: Using context managers for TaskGroups
6. **Task Dependencies**: Using `>>` operator for clear flow

**DAG Validation**:
```bash
# Syntax check
python -m py_compile airflow/dags/sme_pulse_external_data_sync.py

# Import check
docker compose exec airflow-webserver airflow dags list-import-errors

# DAG structure visualization
docker compose exec airflow-webserver airflow dags show sme_pulse_external_data_sync
```

### Step 4.5: Testing & Deployment

**Manual Trigger Test**:
```bash
# Unpause DAG
docker compose exec airflow-webserver airflow dags unpause sme_pulse_external_data_sync

# Trigger manual run
docker compose exec airflow-webserver airflow dags trigger sme_pulse_external_data_sync

# Monitor via Web UI
# http://localhost:8080 → DAGs → sme_pulse_external_data_sync → Graph View
```

**Monitoring Execution**:
1. Web UI: Real-time task status with color coding
2. Logs: Click on task → View Logs for detailed output
3. CLI: `airflow tasks states-for-dag-run` command

**Success Criteria**:
- ✅ All tasks green in Graph View
- ✅ DAG run state = "success"
- ✅ End-to-end duration < 2 minutes
- ✅ No errors in any task logs
- ✅ Data visible in Trino: `SELECT * FROM iceberg.gold.dim_macro_indicators`

---

## Lessons Learned

### Issue 1: MinIO Package Not Installed

**Problem**: 
```
ModuleNotFoundError: No module named 'minio'
```
DAG failed immediately on `verify_external_sources` task.

**Root Cause**: 
Airflow Dockerfile didn't include `minio` package, only had `boto3`.

**Solution**:
1. Updated `airflow/Dockerfile` to add `minio requests pandas` to pip install
2. Rebuilt Docker images: `docker compose build`
3. Restarted services: `docker compose up -d`

**Lesson**: Always test package imports in Airflow container before deploying DAG. Use `docker compose exec airflow-scheduler pip list` to verify.

**Prevention**: Maintain a `requirements.txt` for Airflow and include in Dockerfile.

---

### Issue 2: Permission Denied on dbt/target Folder

**Problem**:
```
PermissionError: [Errno 13] Permission denied: '/opt/dbt/target/compiled/sme_pulse/models/silver/external'
```

**Root Cause**: 
Airflow user trying to write to dbt container's file system. Volume mount permissions didn't allow cross-container writes.

**Solution**:
Removed the problematic compiled folders that were causing conflicts:
```powershell
Remove-Item -Recurse -Force "dbt/target/compiled/sme_pulse/models/*/external"
```

**Lesson**: dbt should run in its own container, not from Airflow. Use `docker compose exec dbt` pattern instead of trying to run dbt directly in Airflow container.

**Prevention**: Keep dbt execution isolated in dbt container. Only use Airflow to orchestrate via Docker commands.

---

### Issue 3: Wrong API URL for Vietnam Provinces

**Problem**:
```
HTTPError: 404 Client Error: Not Found for url: https://vnappmob.com/api/province
```

**Root Cause**: 
Used outdated API endpoint from old documentation.

**Solution**:
Updated to official Open API endpoint:
```python
PROVINCES_API_URL = "https://provinces.open-api.vn/api/?depth=2"
```

**Lesson**: Always verify API endpoints are current before production deployment. Check official documentation or GitHub repos for latest URLs.

**Prevention**: 
- Add API health checks in `verify_external_sources` task
- Document API sources with links in code comments
- Set up monitoring to detect API endpoint changes

---

### Issue 4: Task Group Chaining Error

**Problem**:
```
TypeError: unsupported operand type(s) for >>: 'list' and 'list'
```
When trying: `ingest_group >> silver_group >> gold_group`

**Root Cause**: 
TaskGroups don't automatically return a single exit task. When you reference a TaskGroup in dependencies, you need to be explicit.

**Original Code** (wrong):
```python
with TaskGroup('ingest_external_data') as ingest_group:
    ingest_wb = PythonOperator(...)
    ingest_prov = PythonOperator(...)
    # Implicitly returns [ingest_wb, ingest_prov]

ingest_group >> silver_group  # Tries to chain list >> list
```

**Solution**:
```python
with TaskGroup('ingest_external_data') as ingest_group:
    ingest_wb = PythonOperator(...)
    ingest_prov = PythonOperator(...)

# Explicitly chain from check_freshness to BOTH ingest tasks
check_freshness >> [ingest_wb, ingest_prov] >> dbt_silver.dbt_run_task
```

**Lesson**: Be explicit about task dependencies with TaskGroups. Use list syntax `[task1, task2] >> task3` when you want both to complete before next task.

**Prevention**: Draw out task flow diagram before coding. Use `airflow dags show --tree` to verify dependencies.

---

### Issue 5: Scheduler Hostname Mismatch

**Problem**:
```
AirflowException: Hostname of job runner does not match
```
Tasks stuck in queued state, scheduler not picking up.

**Root Cause**: 
Scheduler crashed during development, left stale state in metadata database. New scheduler had different hostname.

**Solution**:
```bash
docker compose restart airflow-scheduler
```
Restart clears stale jobs and reinitializes scheduler with correct hostname.

**Lesson**: LocalExecutor is sensitive to scheduler restarts. Always restart scheduler after significant config changes.

**Prevention**: 
- Use CeleryExecutor in production for better resilience
- Monitor scheduler health with `airflow jobs check`
- Set up auto-restart policies in Docker Compose

---

### Issue 6: Stuck DAG Runs from Testing

**Problem**:
Manual trigger from UI resulted in DAG staying in "queued" state. Tasks never scheduled.

**Root Cause**: 
Old failed DAG runs from testing phase left task instances in database. Airflow scheduler trying to adopt orphaned tasks.

**Solution**:
```bash
# Delete all runs for the DAG
docker compose exec airflow-webserver airflow dags delete sme_pulse_external_data_sync -y

# Restart both scheduler and webserver
docker compose restart airflow-scheduler airflow-webserver
```

**Lesson**: Clean up test runs before production deployment. Use `airflow dags delete` to clear DAG history and start fresh.

**Prevention**: 
- Use separate Airflow environments for dev and prod
- Regularly clean up old DAG runs: `airflow db clean --clean-before-timestamp`
- Set DAG-level `max_active_runs=1` to prevent concurrent run issues

---

### Issue 7: Webserver Stale PID File

**Problem**:
Web UI inaccessible with `ERR_EMPTY_RESPONSE`. Webserver logs showed:
```
Error: Already running on PID 14 (or pid file '/opt/airflow/airflow-webserver.pid' is stale)
```

**Root Cause**: 
Webserver crashed or was killed ungracefully, leaving PID file. Gunicorn refused to start because it detected "existing" process.

**Solution**:
```bash
# Remove stale PID file
docker compose exec airflow-webserver rm -f /opt/airflow/airflow-webserver.pid

# Restart webserver
docker compose restart airflow-webserver
```

**Lesson**: PID files can become stale after ungraceful shutdowns. Always check for and remove stale PIDs before restart.

**Prevention**: 
- Use proper shutdown procedures: `docker compose stop` (not `kill`)
- Add health checks in docker-compose.yml
- Set up monitoring to detect webserver down status

---

### Issue 8: MinIO Endpoint Configuration

**Problem**:
```
ConnectionRefusedError: [Errno 111] Connection refused (localhost:9000)
```
Script failed when executed from Airflow container.

**Root Cause**: 
`ingest_provinces.py` defaulted to `localhost:9000`, but in Docker network, MinIO service is at `minio:9000`.

**Original Code**:
```python
endpoint = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
```

**Solution**:
```python
endpoint = os.getenv('MINIO_ENDPOINT', 'minio:9000')
```

**Lesson**: Service names in Docker Compose are DNS names within the Docker network. Never hardcode `localhost` for inter-container communication.

**Better Solution**: Always set environment variables in docker-compose.yml:
```yaml
services:
  airflow-scheduler:
    environment:
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin123
```

**Prevention**: 
- Document all required environment variables
- Use `.env` file for configuration
- Add connectivity tests before running main logic

---

### Issue 9: Task Retry Delay Too Long

**Problem**:
Task `ingest_provinces` failed, but retry took 5 minutes. During development, this slowed down iteration.

**Solution for Development**:
```python
default_args = {
    'retries': 3,
    'retry_delay': timedelta(seconds=30)  # Shorter for dev
}
```

**Solution for Production**:
```python
default_args = {
    'retries': 3,
    'retry_delay': timedelta(minutes=5),  # Longer for prod to avoid API rate limits
    'retry_exponential_backoff': True,
    'max_retry_delay': timedelta(minutes=30)
}
```

**Lesson**: Use different retry configurations for dev vs prod. Dev needs fast iteration, prod needs resilience.

---

## Key Takeaways & Best Practices

### 1. **Containerization is Critical**
- Each service (Airflow, dbt, Trino, MinIO) runs in its own container
- Use service names for inter-container communication
- Mount volumes for code sharing, not for execution

### 2. **Separation of Concerns**
- **Ingestion Layer**: Python scripts handle API calls and MinIO writes
- **Transformation Layer**: dbt handles SQL transformations and tests
- **Orchestration Layer**: Airflow handles scheduling and dependencies
- Don't mix these responsibilities

### 3. **Idempotency is Essential**
- Every task should be safe to re-run
- Use date-stamped filenames for audit trail
- Use incremental models with unique keys
- Design for eventual consistency

### 4. **Testing at Every Layer**
- **API Testing**: Verify endpoints before production
- **Script Testing**: Run scripts manually before DAG
- **dbt Testing**: Use schema tests, not-null, relationships
- **DAG Testing**: Trigger manual runs before scheduling

### 5. **Error Handling Strategy**
- **Fail Fast**: Verify dependencies first (verify_external_sources)
- **Retry with Backoff**: Use exponential backoff for API calls
- **Log Everything**: Detailed logging helps debugging
- **Graceful Degradation**: Skip if data fresh, don't fail

### 6. **Environment Variables for Configuration**
- Never hardcode endpoints, credentials, or paths
- Use `os.getenv()` with sensible defaults
- Document all required env vars in README
- Use different configs for dev/staging/prod

### 7. **Monitoring & Alerting**
- Set up email alerts for DAG failures
- Monitor data freshness in gold tables
- Track API response times and error rates
- Create summary dashboard in Metabase

---

## Production Checklist

### Pre-Deployment
- [ ] All packages installed in Airflow image
- [ ] Environment variables configured in docker-compose.yml
- [ ] API endpoints verified and documented
- [ ] MinIO buckets and paths exist
- [ ] dbt models tested and documented
- [ ] DAG syntax validated with py_compile
- [ ] Manual DAG run successful end-to-end

### Deployment
- [ ] DAG file copied to airflow/dags folder
- [ ] Ingestion scripts in ops/external_sources folder
- [ ] Docker images rebuilt and restarted
- [ ] DAG visible in Airflow UI without import errors
- [ ] DAG unpaused and ready for scheduling

### Post-Deployment Monitoring (First 30 Days)
- [ ] Monitor first scheduled run (1st of month)
- [ ] Verify data appears in gold tables
- [ ] Check Metabase dashboards refresh correctly
- [ ] Review Airflow logs for warnings
- [ ] Validate data quality (row counts, null checks)
- [ ] Test downstream analytics queries

### Ongoing Operations
- [ ] Monthly review of DAG run history
- [ ] Quarterly API endpoint health check
- [ ] Bi-annual review of data quality tests
- [ ] Annual review of data retention policy
- [ ] Update documentation as APIs change

---

## Performance Metrics

### Successful DAG Run Timings (Phase 4 Final)
```
Total Duration: ~49 seconds

Task Breakdown:
- verify_external_sources:     1.5s
- check_data_freshness:        4.2s
- ingest_world_bank:          27.2s
- ingest_provinces:           14.1s  (parallel with world_bank)
- dbt_run_silver_external:    13.6s
- dbt_test_silver_external:    0.8s
- dbt_run_gold_external:       9.2s
- dbt_test_gold_external:      0.9s
- log_summary:                 0.3s
```

### Data Volumes
- **World Bank**: 30 rows (10 years × 3 indicators)
- **Provinces**: 63 provinces
- **Districts**: 691 districts
- **Total Gold Records**: ~700 location records + 10 time records

### Resource Usage
- **MinIO Storage**: ~50 KB for all Parquet files
- **Iceberg Tables**: ~200 KB for silver + gold combined
- **Airflow Metadata**: ~5 KB per DAG run

---

## Future Enhancements

### Short-term (Next Sprint)
1. **Add More Economic Indicators**: 
   - Interest rates, foreign investment, export data
   - Requires updating `ingest_world_bank.py` and dbt models

2. **Ward-level Location Data**:
   - Change depth=2 to depth=3 in provinces API
   - Update `stg_vietnam_locations` to handle 3-level hierarchy

3. **Data Freshness Alerts**:
   - Send Slack notification if World Bank data > 365 days old
   - Alert if province data hasn't changed in 2 years (unusual)

### Medium-term (Next Quarter)
1. **SCD Type 2 for Location Changes**:
   - Track when districts are created, merged, or renamed
   - Requires versioning logic in gold layer

2. **API Rate Limiting**:
   - Implement exponential backoff in ingestion scripts
   - Add request throttling to avoid API blocks

3. **Metabase Integration**:
   - Create pre-built dashboards for economic trends
   - Add geographic map visualizations

### Long-term (Next Year)
1. **Additional Data Sources**:
   - Central bank interest rates
   - Industry-specific indices
   - Weather data (if relevant for certain SMEs)

2. **Machine Learning Features**:
   - Economic indicator forecasting
   - Anomaly detection in sales vs economic trends
   - Lead/lag correlation analysis

3. **Real-time Updates**:
   - Switch from monthly batch to daily incremental
   - Add change data capture (CDC) for location updates

---

## Conclusion

The external data integration project successfully added critical macro-economic and geographic context to the SME Pulse platform. Through a methodical 4-phase approach (Ingestion → Silver → Gold → Orchestration), we built a robust, scalable, and maintainable data pipeline.

**Key Achievements**:
- ✅ 2 external data sources integrated
- ✅ Bronze-Silver-Gold architecture implemented
- ✅ Automated monthly orchestration via Airflow
- ✅ Comprehensive data quality testing
- ✅ Production-ready with monitoring and error handling

**Technical Skills Demonstrated**:
- API integration and data extraction
- Parquet file format and MinIO object storage
- dbt for SQL-based transformations
- Apache Iceberg for lakehouse tables
- Airflow for workflow orchestration
- Docker for containerized services

**Business Value Delivered**:
- Analysts can correlate sales trends with national economic indicators
- Geographic analysis enabled by standardized location hierarchy
- Monthly automated updates with zero manual intervention
- Foundation for future ML models and predictive analytics

This documentation serves as both a technical reference and a learning resource for similar data integration projects.

---

**Document Version**: 1.0  
**Last Updated**: 2025-11-01  
**Author**: SME Pulse Data Team  
**Review Cycle**: Quarterly
