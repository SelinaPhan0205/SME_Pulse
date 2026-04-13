# AGENTS CONTEXT KNOWLEDGE AND DELIVERY PLAYBOOK

## 1) Purpose
This file is the persistent working memory for technical due diligence and implementation.
Goals:
- Keep system context concise but complete to reduce repeated token usage.
- Define execution protocol: plan first, get user approval, implement, self-validate, then commit only after user approval.
- Prioritize Data Pipeline and ML Pipeline gaps first.
- Leave README rewrite and non-critical cleanup for the final phase.

## 2) Current System Snapshot (Reality Check)

### 2.1 Runtime Architecture
- Lakehouse stack: Trino + Iceberg + MinIO + Hive Metastore.
- Orchestration: Airflow DAGs (daily ETL, ML predict, weekly ML retrain, external data sync).
- Backend serving: FastAPI + SQLAlchemy async + JWT auth + Celery worker.
- Frontend: React + React Query.
- BI: Metabase.

### 2.2 Compose Services (Current)
Current docker compose defines 11 services:
1. postgres
2. redis
3. minio
4. airflow-scheduler
5. airflow-webserver
6. hive-metastore
7. trino
8. metabase
9. postgres_application_db
10. backend
11. celery-worker

Important note:
- dbt is NOT a standalone compose service.
- dbt is installed inside Airflow image and executed from airflow containers.
- Agreed direction:
  - Phase 0-2 (restore + hardening): keep dbt inside Airflow to minimize migration risk.
  - Post-stabilization (Phase 3+): split dbt into standalone service for cleaner separation and CI/CD.

### 2.3 Repository Map (What lives where)
- airflow/
  - dags/
    - sme_pulse_daily_etl.py: daily Bronze -> Silver -> Gold and trigger ML predict.
    - sme_pulse_ml_predict.py: ML inference DAG (UC09 forecast + UC10 anomaly).
    - sme_pulse_ml_training.py: weekly retraining DAG.
    - sme_pulse_external_data_sync.py: provinces + optional World Bank sync.
  - config/pipeline_config.yml: dbt commands, infra endpoints, thresholds.
- backend/
  - app/main.py: app wiring, middleware, routers.
  - app/core/: config, security, celery config.
  - app/models/: core and finance ORM models.
  - app/modules/: auth, users, finance, analytics, partners, settings.
  - app/modules/analytics/service.py: Trino ML read path + PG fallback.
  - app/modules/analytics/tasks.py: Celery export tasks.
  - app/db/seeds/: default roles/users/org seeds.
  - alembic/: OLTP schema migrations.
- dbt/
  - models/silver: staging/features/ml_training datasets.
  - models/gold: dimensions/facts/links/kpi/ml_scores.
  - dbt_project.yml and profiles.yml.
- ops/
  - ingest_*.py: bronze ingest scripts from raw files.
  - run_all_ingest.py: orchestrated ingest run.
  - external_sources/: world bank and provinces ingest scripts.
  - ml/UC09-forecasting: Prophet train/predict scripts.
  - ml/UC10-anomoly_detection: Isolation Forest train/detect scripts.
- sql/
  - bootstrap schemas and external table scripts.
- tools/
  - bootstrap_lakehouse.sh.

## 3) Data Pipeline and ML Pipeline (Priority Focus)

### 3.1 Data Pipeline Current Flow
1. Raw data ingest scripts upload parquet to MinIO bronze paths.
2. Trino/Hive external tables read bronze parquet.
3. Airflow daily ETL runs dbt tags in sequence:
   - staging -> features -> ml_training -> gold dimensions -> gold facts -> links/kpi/ml_scores.
4. Daily ETL triggers ML predict DAG.
5. Weekly ML training DAG retrains UC09 and UC10.

### 3.2 ML Pipeline Current Flow
- UC09 Prophet training:
  - Reads from silver.ml_training_cashflow_fcst.
  - Logs model to MLflow registry.
- UC09 Prophet prediction:
  - Loads model from MLflow.
  - Predicts 30 days.
  - Inserts into gold.ml_cashflow_forecast.
- UC10 Isolation Forest training:
  - Reads from gold.fact_bank_txn.
  - Trains and logs model/scaler/features to MLflow.
- UC10 detection:
  - Reads recent gold.fact_bank_txn.
  - Scores anomalies.
  - Inserts alerts/stats into gold tables.

## 4) Known Gaps (Ordered)

### P0 - Must fix first
1. Multi-tenant data isolation gap in ML serving path.
   - ML gold tables currently lack org_id in write/read path for forecast/anomaly.
   - Backend analytics queries do not enforce org_id filter for Trino ML tables.

2. Backend caching gap.
   - Redis exists for Celery broker/backend but analytics response caching is not implemented as true L2 cache.
   - ML predict DAG cache refresh/invalidation functions are placeholders.

### P1 - High priority next
3. MLflow tracking URI inconsistency across DAG/scripts/env.
4. Forecast write path is append-only (no upsert/merge), can duplicate snapshots.
5. Reliability and quality hardening for ML prediction output and pipeline idempotency.

### P2 - After priority stream
6. Documentation drift (README claims vs runtime reality).
7. Optional external macro pipeline alignment (World Bank optional/disabled by default).
8. Platform architecture cleanup: decouple dbt from Airflow into standalone service after pipeline stabilization.

## 5) Execution Protocol (Mandatory)

### Rule A - Plan first, then implement
Before any code change:
1. Propose big-step plan.
2. Break each big step into small tasks.
3. Wait for user approval.
4. Implement only approved scope.

### Rule B - Validation gate per big step
For each big step:
1. Implement.
2. Run relevant verification tests/queries.
3. Report result with pass/fail evidence.
4. Ask user approval to proceed.

### Rule C - Commit policy
- Never commit automatically after coding.
- Commit only when user explicitly approves.
- If approved, commit message must include:
  - scope
  - validation summary
  - risk/rollback note

## 6) Step-by-Step Delivery Roadmap

## Phase 0 - Baseline verification (no risky edits)
Goal:
- Validate reproducible startup and identify hard blockers.
Tasks:
1. Verify compose services health.
2. Verify lakehouse schemas and external tables.
3. Verify dbt runtime from airflow container.
4. Verify Airflow DAG import health.
5. Verify backend auth and analytics endpoints boot.
Validation:
- docker compose ps healthy
- trino schema/table checks
- dbt debug/run smoke
- airflow dags list contains key dags
Gate:
- user confirms go/no-go for Phase 1.

## Phase 1 - Data Pipeline hardening (priority)
Goal:
- Stabilize bronze -> silver -> gold reliability and idempotency.
Tasks:
1. Normalize bronze table definitions vs actual parquet schema.
2. Remove pipeline drift between sql scripts and ingest outputs.
3. Add/adjust dbt tests for critical models and keys.
4. Ensure daily ETL flow and dependencies are deterministic.
Validation:
- dbt run/test for silver and gold critical selectors
- row count sanity checks on key tables
- one manual DAG run success
Gate:
- user approves before moving to Phase 2.

## Phase 2 - ML Pipeline and Serving correctness (priority)
Goal:
- Ensure ML output is tenant-safe, reproducible, and consumable by backend.
Tasks:
1. Add org_id strategy for ML output tables and query filters in backend.
2. Make forecast/anomaly write path idempotent (merge/upsert strategy).
3. Unify MLflow URI and model loading consistency.
4. Add minimal model quality and data freshness checks in DAG flow.
5. Replace placeholder cache invalidation with real backend cache invalidation contract.
Validation:
- ML train/predict DAG successful run
- backend forecast/anomaly endpoint checks by org_id
- no duplicate records for same key window
Gate:
- user approves before moving to Phase 3.

## Phase 3 - Remaining gaps and platform polish
Goal:
- Complete non-priority gaps and operational quality improvements.
Tasks:
1. RBAC enforcement coverage audit and fixes where missing.
2. Security and config consistency cleanup.
3. Improve fallback behavior determinism and observability.
4. Introduce standalone dbt service and migrate runbook without breaking DAG reliability.
Validation:
- targeted API tests + smoke tests
- dbt run/test/docs from standalone dbt service
- Airflow DAGs still execute dbt commands successfully after migration
Gate:
- user approves before README rewrite phase.

## Phase 4 - README rewrite (final)
Goal:
- Rewrite README to match actual system behavior 100%.
Tasks:
1. Correct service inventory and runbook commands.
2. Correct auth algorithm/roles/caching claims to real implementation.
3. Add verified startup + pipeline execution guide.
Validation:
- command checklist dry-run
- docs consistency check with compose and code
Gate:
- user final approval, then commit.

## 7) Validation Checklist Templates

### 7.1 Data Pipeline Gate Checklist
- compose health check pass
- trino bootstrap schemas exist: bronze/silver/gold
- external tables queryable with expected row counts
- dbt run selector pass
- dbt test selector pass
- airflow daily ETL run pass

### 7.2 ML Pipeline Gate Checklist
- weekly training DAG pass
- daily predict DAG pass
- MLflow model artifacts available and loadable
- forecast and anomaly tables updated for latest run
- backend endpoints return tenant-correct result set
- no duplicate records for key dimensions

### 7.3 Pre-Commit Checklist
- changed files list reviewed
- relevant tests executed and reported
- migration/rollback notes prepared
- user explicit approval recorded

## 8) Working Agreement with User
- Always present the next big-step plan first.
- Always wait for approval before applying code changes.
- Always report verification output after each big step.
- Commit only after explicit user consent.

## 9) Current Next Action (Immediate)
Proposed immediate execution order:
1. Phase 0 baseline verification.
2. Phase 1 Data Pipeline hardening.
3. Phase 2 ML Pipeline and backend serving safety.
4. Phase 3 remaining technical gaps.
5. Phase 4 README rewrite as final step.

---
Last updated: 2026-03-20
Owner: Technical Due Diligence Agent
Status: Active working playbook
