# SME Pulse Lakehouse Platform

> **A modern, production-ready Medallion Lakehouse stack for SMEs, built with Trino, Iceberg, MinIO, Hive Metastore, dbt, and Airflow.**

---

## 🚀 System Architecture

```
[Excel/CSV/Source] 
    ↓
[MinIO S3 - Bronze]  ← (Batch ingest via Python/ops)
    ↓
[Trino + Iceberg + Hive Metastore]
    ↓
[dbt]  →  [Silver schema]  →  [Gold schema]
    ↓                        ↓
[Airflow orchestration]      ↓
    ↓                        ↓
[Metabase/BI]           [Trino SQL]
```

- **Single Trino catalog:** `sme_lake` (Iceberg connector)
- **Medallion schemas:** bronze, silver, gold (best practice)
- **MinIO:** S3 backend, endpoint `minio:9000`
- **Hive Metastore:** central metadata for Iceberg
- **dbt:** modular SQL transformation, Medallion modeling
- **Airflow:** robust orchestration, error handling, scheduling
- **Docker Compose:** unified, reproducible, health-checked stack

## 🛠️ Technology Stack

| Component      | Purpose                        | Version/Notes           |
| -------------- | ------------------------------ | ---------------------- |
| Trino          | SQL query engine               | v426+                  |
| Iceberg        | Table format (Lakehouse)       |                        |
| MinIO          | S3-compatible object storage   |                        |
| Hive Metastore | Metadata for Iceberg           |                        |
| dbt            | Data transformation            | v1.8+                  |
| Airflow        | Workflow orchestration         | v2.9+                  |
| Metabase       | BI dashboard                   |                        |
| Postgres       | Metadata, optionally raw data  | v15+                   |
| Redis          | Caching                        | v7+                    |

## 📁 Project Structure

```
├── docker-compose.yml      # All services
├── .env                    # Environment variables
├── airflow/
│   ├── dags/               # Airflow DAGs
│   └── entrypoint.sh       # Airflow entrypoint
├── dbt/
│   ├── dbt_project.yml     # dbt config
│   ├── profiles.yml        # dbt connection
│   └── models/             # dbt models (bronze/silver/gold)
├── ops/                    # Python ingest scripts
├── trino/
│   └── catalog/            # Trino catalog configs
├── sql/                    # SQL init scripts
└── README.md
```

## ⚡ Quickstart

1. **Copy environment file:**
   ```powershell
   Copy-Item .env.example .env
   ```
2. **Edit secrets:**
   - Update `POSTGRES_PASSWORD`, `MINIO_ROOT_PASSWORD` in `.env` if needed.
3. **Start all services:**
   ```powershell
   docker compose up -d
   ```
4. **Check service health:**
   ```powershell
   docker compose ps
   ```
5. **Access UIs:**
   - Airflow: http://localhost:8080 (admin/admin)
   - Metabase: http://localhost:3000
   - MinIO: http://localhost:9001 (minio/minio123)

## 🧪 Smoke Test

```powershell
# Check Postgres schemas
 docker compose exec postgres psql -U sme -d sme -c "\dn"
# Test dbt connection
 docker compose exec airflow-webserver dbt debug
# Run dbt models
 docker compose exec airflow-webserver dbt run
# Check data in Trino
 docker compose exec trino trino --execute "SHOW SCHEMAS FROM sme_lake;"
```

## 📊 Data Flow (Medallion)

1. **Ingest:** Raw Excel/CSV → MinIO (bronze)
2. **Transform:** dbt → silver (staging/cleaned)
3. **Aggregate:** dbt → gold (fact, marts)
4. **Orchestrate:** Airflow triggers ingest/dbt
5. **Visualize:** Metabase/Trino SQL

## 🩺 Troubleshooting & Best Practices

- **Permission denied (dbt/target):**
  - Delete `dbt/target` on host, let dbt recreate it.
  - Prefer Docker volumes over bind-mounts for cross-platform compatibility.
- **MinIO connection errors:**
  - Always use `minio:9000` (not localhost) for endpoint in Docker.
- **Airflow DAG stuck:**
  - Ensure both scheduler and webserver are running and healthy.
- **S3A/Iceberg access denied:**
  - Sync access key/secret and endpoint across all configs (Trino, Hive, dbt).
- **See** `LAKEHOUSE_KINH_NGHIEM.md` **for real-world error solutions and lessons learned.**

## 📚 References
- [dbt Documentation](https://docs.getdbt.com/)
- [Trino Iceberg Docs](https://trino.io/docs/current/connector/iceberg.html)
- [Airflow Docs](https://airflow.apache.org/docs/)
- [MinIO Docs](https://min.io/docs/)
- [Medallion Architecture](https://databricks.com/glossary/medallion-architecture)

---
**Maintainer:** SME Pulse Team  
**Last updated:** October 2025