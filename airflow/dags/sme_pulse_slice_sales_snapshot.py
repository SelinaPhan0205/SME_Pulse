from __future__ import annotations
import os
import sys
import glob
import importlib.util
import subprocess
from datetime import datetime, timedelta

from airflow.decorators import dag, task_group
from airflow.operators.python import PythonOperator
from airflow.providers.docker.operators.docker import DockerOperator

# ====== ENV & Defaults ======
S3_ENDPOINT      = os.getenv("S3_ENDPOINT", "http://minio:9001")
S3_ACCESS_KEY    = os.getenv("S3_ACCESS_KEY", "minioadmin")
S3_SECRET_KEY    = os.getenv("S3_SECRET_KEY", "minioadmin123")
S3_SCHEME        = os.getenv("S3_SCHEME",   "s3a")
LAKEHOUSE_BUCKET = os.getenv("LAKEHOUSE_BUCKET", "sme-lake")

DATA_DIR         = os.getenv("DATA_DIR", "/opt/data")
XLSX_DIR         = os.getenv("XLSX_DIR", f"{DATA_DIR}/source")
PARQUET_DIR      = os.getenv("PARQUET_DIR", f"{DATA_DIR}/raw")

OPS_INGEST_PATH  = os.getenv("OPS_INGEST_PATH", "/opt/ops/ingest_batch_snapshot.py")
RAW_PREFIX       = os.getenv("RAW_PREFIX", "bronze/raw/sales_snapshot")
SOURCE_PREFIX    = os.getenv("SOURCE_PREFIX", "bronze/source/sales_snapshot")

DBT_DIR          = os.getenv("DBT_DIR", "/opt/dbt")
DBT_SILVER_SEL   = os.getenv("DBT_SILVER_SEL", "path:models/silver")
DBT_GOLD_SEL     = os.getenv("DBT_GOLD_SEL", "path:models/gold")

REDIS_HOST       = os.getenv("REDIS_HOST", "redis")
REDIS_PORT       = int(os.getenv("REDIS_PORT", "6379"))
ORG_ID           = os.getenv("ORG_ID", "org-sme-001")

DEFAULT_ARGS = {
    "owner": "airflow",
    "retries": 2,
    "retry_delay": timedelta(minutes=3),
    "depends_on_past": False,
}

# ====== Helper: robust import/run ingest script ======
def _run_ingest_wrapper():
    """
    Tries to import /opt/ops/ingest_batch_snapshot.py and call one of:
      - main()
      - run()
      - ingest()
      - upload_and_convert()
    If none exist, fallback to: `python /opt/ops/ingest_batch_snapshot.py` with env/args.
     Script is expected to:
         - upload all .xlsx from XLSX_DIR to s3a://sme-lake/bronze/source/sales_snapshot/{YYYYMMDD}/...
         - convert to parquet and upload to s3a://sme-lake/bronze/raw/sales_snapshot/{YYYYMMDD}/...
    """
    import logging
    log = logging.getLogger("ingest_wrapper")

    if not os.path.exists(OPS_INGEST_PATH):
        raise FileNotFoundError(f"Ingest script not found: {OPS_INGEST_PATH}")

    # Prefer import so we keep logs in same task
    try:
        spec = importlib.util.spec_from_file_location("ingest_mod", OPS_INGEST_PATH)
        mod = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(mod)
        log.info("Imported ingest module from %s", OPS_INGEST_PATH)

        candidates = ["main", "run", "ingest", "upload_and_convert"]
        for fn in candidates:
            if hasattr(mod, fn) and callable(getattr(mod, fn)):
                log.info("Calling function %s(...) in ingest module", fn)
                # Chỉ truyền đúng 2 tham số folder, prefix cho hàm ingest
                getattr(mod, fn)(
                    folder=XLSX_DIR,
                    prefix="sales_snapshot"
                )
                return

        # If we got here, no callable found: fallback to subprocess
        log.warning("No callable found in module; fallback to CLI invocation")
        _fallback_cli_run(log)

    except Exception as e:
        log.warning("Import path failed (%s). Fallback to CLI.", e)
        _fallback_cli_run(log)


def _fallback_cli_run(log):
    # Build a best-effort CLI call. If your script doesn't accept args, it should still read ENV.
    cmd = [
        sys.executable, OPS_INGEST_PATH,
        "--folder", XLSX_DIR,
        "--prefix", "sales_snapshot"
    ]
    log.info("Running ingest via CLI: %s", " ".join(cmd))
    subprocess.run(cmd, check=True)


def _verify_inputs():
    import logging
    log = logging.getLogger("verify_inputs")

    for p, kind in [(DATA_DIR, "DATA_DIR"), (XLSX_DIR, "XLSX_DIR"), (PARQUET_DIR, "PARQUET_DIR")]:
        if not os.path.exists(p):
            raise FileNotFoundError(f"{kind} not found: {p}")
        log.info("✅ Exists: %s  (%s)", p, kind)

    # Require at least 1 xlsx file
    xlsx_files = []
    for suf in ("*.xlsx", "*.xls"):
        xlsx_files.extend(glob.glob(os.path.join(XLSX_DIR, suf)))
    if not xlsx_files:
        raise RuntimeError(f"No XLSX files found in {XLSX_DIR}")
    log.info("📄 Found %d xlsx files (first 3): %s", len(xlsx_files), xlsx_files[:3])

    # Show ingest script presence
    if not os.path.exists(OPS_INGEST_PATH):
        raise FileNotFoundError(f"Ingest script missing: {OPS_INGEST_PATH}")
    log.info("🧩 Ingest script OK: %s", OPS_INGEST_PATH)

    # Show critical ENV (masked)
    log.info("S3_ENDPOINT=%s", S3_ENDPOINT)
    log.info("LAKEHOUSE_BUCKET=%s | SOURCE_PREFIX=%s | RAW_PREFIX=%s", LAKEHOUSE_BUCKET, SOURCE_PREFIX, RAW_PREFIX)
    return True


def _invalidate_cache():
    import redis
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
    keys = [
        f"v1:{ORG_ID}:cash:overview",
        f"v1:{ORG_ID}:kpi:dso",
        f"v1:{ORG_ID}:kpi:dpo",
        f"v1:{ORG_ID}:kpi:ccc",
    ]
    deleted = 0
    for k in keys:
        deleted += int(r.delete(k))
    print(f"✅ Redis invalidated {deleted}/{len(keys)} keys for {ORG_ID}")


@dag(
    dag_id="sme_pulse_sales_snapshot",
    description="Vertical slice orchestration for Kaggle sales_snapshot → silver→gold (raw zone is external table in minio.default)",
    schedule="@daily",          # đổi @hourly nếu muốn
    start_date=datetime(2025, 10, 26),
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["sme-pulse", "slice", "lakehouse", "iceberg", "kaggle"]
)
def sales_snapshot_pipeline():

    # ---------- Verify ----------
    verify_inputs = PythonOperator(
        task_id="verify_inputs",
        python_callable=_verify_inputs,
    )

    # ---------- Ingest: XLSX→MinIO + Parquet→MinIO ----------
    @task_group(group_id="ingest")
    def ingest_group():
        ingest_task = PythonOperator(
            task_id="upload_xlsx_and_parquet_to_minio",
            python_callable=_run_ingest_wrapper,
        )
        return ingest_task

    # ---------- dbt: Silver ----------
    @task_group(group_id="dbt_silver")
    def dbt_silver_group():
        from airflow.operators.bash import BashOperator
        run_silver = BashOperator(
            task_id="dbt_run_silver",
            bash_command="cd /opt/dbt && dbt run --select 'path:models/silver'"
        )
        test_silver = BashOperator(
            task_id="dbt_test_silver",
            bash_command="cd /opt/dbt && dbt test --select 'path:models/silver'"
        )
        run_silver >> test_silver
        return test_silver

    # ---------- dbt: Gold ----------
    @task_group(group_id="dbt_gold")
    def dbt_gold_group():
        from airflow.operators.bash import BashOperator
        run_gold = BashOperator(
            task_id="dbt_run_gold",
            bash_command="cd /opt/dbt && dbt run --select 'path:models/gold'"
        )
        test_gold = BashOperator(
            task_id="dbt_test_gold",
            bash_command="cd /opt/dbt && dbt test --select 'path:models/gold'"
        )
        run_gold >> test_gold
        return test_gold

    # ---------- Serve / Cache ----------
    serve = PythonOperator(
        task_id="invalidate_cache",
        python_callable=_invalidate_cache,
    )

    # Wiring
    verify_inputs >> ingest_group() >> dbt_silver_group() >> dbt_gold_group() >> serve

dag = sales_snapshot_pipeline()
