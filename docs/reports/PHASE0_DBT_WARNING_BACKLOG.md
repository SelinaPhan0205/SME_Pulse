# Phase 0 DBT and Infra Warning Backlog

Date: 2026-03-20
Scope: Reconstructed from live runtime verification after chat context loss

## Summary

- Phase 0 core services are up and healthy (postgres, redis, minio, trino, airflow, backend).
- Airflow DAG import is healthy (daily ETL, data quality, external sync, ml predict, ml training).
- dbt connection to Trino is healthy when executed from /opt/dbt.
- Legacy drift and runtime warnings were found; critical ones were fixed below.

## Resolved in this pass

### 1) Trino catalog drift: iceberg catalog missing

- Severity: High
- Symptom:
	- SHOW SCHEMAS FROM iceberg failed with Catalog 'iceberg' not found.
	- Legacy scripts/docs still reference iceberg.*.
- Root cause:
	- Active catalog is sme_lake, but compatibility alias iceberg was not defined.
- Fix applied:
	- Added Trino catalog alias file trino/catalog/iceberg.properties with same Iceberg/MinIO/HMS configuration as sme_lake.
- Verification target:
	- SHOW CATALOGS should include iceberg after trino restart/recreate.

### 2) dbt debug non-zero exit due missing git in Airflow image

- Severity: Medium
- Symptom:
	- dbt debug passed connection but failed dependency check: git not found.
- Root cause:
	- Custom Airflow image did not install git.
- Fix applied:
	- Updated airflow/Dockerfile to install git via apt-get before switching to airflow user.
- Verification target:
	- dbt debug --profiles-dir /opt/dbt --project-dir /opt/dbt --target dev exits successfully.

### 3) dbt helper path drift and config threshold mismatch

- Severity: Medium
- Symptom:
	- Helper defaults referenced /opt/airflow/dbt (old path).
	- Helper appended --profiles-dir blindly, risking duplicated flags.
	- Row count threshold keys in helper did not match pipeline_config.yml structure.
- Root cause:
	- Legacy helper code from pre-migration path and config structure.
- Fix applied:
	- Updated airflow/dags/utils/dbt_helpers.py:
		- default dbt_dir/profiles_dir to /opt/dbt
		- append --profiles-dir and --project-dir only if absent
		- read thresholds from data_quality.row_count_variance.warning/critical

### 4) Airflow deprecated setting warning

- Severity: Low
- Symptom:
	- dag_concurrency deprecation warning in scheduler logs.
- Root cause:
	- docker-compose used AIRFLOW__CORE__DAG_CONCURRENCY.
- Fix applied:
	- Replaced with AIRFLOW__CORE__MAX_ACTIVE_TASKS_PER_DAG in docker-compose.yml.

## Expected post-reset state (not treated as Phase 0 defects)

### A) Empty/partial lakehouse tables

- Context:
	- Docker images/containers/volumes/data were reset before this pass.
	- Services are rebuilt, but dbt full rebuild and ingest have not been executed yet.
- Current observation:
	- minio.default has baseline raw external tables for legacy sources.
	- sme_lake.silver contains partial objects only.
	- sme_lake.gold is empty at this point.
- Classification:
	- Expected initialization state after reset.
	- To be completed in Phase 1 execution runbook.

### B) App DB extraction sources missing in MinIO

- Context:
	- dbt staging smoke now reaches execution layer, then fails on missing sources:
		- minio.default.ar_invoices_app
		- minio.default.payments_app
		- minio.default.payment_allocations_app
- Root reason in current state:
	- App DB migrations/seed and extraction path have not been re-initialized post-reset.
- Classification:
	- Expected initialization dependency, not a runtime regression.
	- To be handled in Phase 1 tasks (migration -> seed -> extract -> external table refresh -> dbt).

## Evidence checklist snapshot (latest)

- docker compose up -d: services up, core health checks passing.
- airflow dags list: key DAGs imported.
- dbt debug from /opt/dbt: all checks passed after image patch (git + profiles/project path).
- Trino metadata:
	- catalogs: iceberg, kol_hive, kol_lake, minio, sme_lake, system (after alias patch)
	- schemas in sme_lake: bronze, silver, gold, default
	- tables in minio.default: raw external tables present
	- dbt staging smoke: fails only on expected missing app_db external sources post-reset

## Next verification commands

1. Rebuild/restart trino and airflow images:
	 - docker compose up -d --build trino airflow-scheduler airflow-webserver
2. Validate compatibility catalog:
	 - docker exec sme-trino trino --execute "SHOW CATALOGS"
	 - docker exec sme-trino trino --execute "SHOW SCHEMAS FROM iceberg"
3. Validate dbt runtime clean:
	 - docker exec sme-airflow-scheduler bash -lc "cd /opt/dbt && dbt debug --profiles-dir /opt/dbt --project-dir /opt/dbt --target dev"
4. Re-initialize reset state for data path:
	 - docker compose exec backend alembic upgrade head
	 - docker compose exec backend python app/db/seeds/run_all.py
	 - docker compose exec backend python /opt/ops/run_all_ingest.py
	 - docker exec sme-airflow-scheduler bash -lc "cd /opt/dbt && dbt seed --profiles-dir /opt/dbt --project-dir /opt/dbt --target dev"
	 - docker exec sme-airflow-scheduler bash -lc "cd /opt/dbt && dbt run --select tag:staging --profiles-dir /opt/dbt --project-dir /opt/dbt --target dev"

