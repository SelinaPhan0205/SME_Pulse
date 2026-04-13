# Phase 2 Production Quality Report

Date: 2026-04-13
Status: Completed, pending user approval
Scope: ML pipeline and serving correctness (UC09 forecast, UC10 anomaly)

## Goal

Close Phase 2 with evidence that:
- model evaluation is out-of-sample and reproducible,
- prediction serving is tenant-safe,
- write paths are idempotent for operational use,
- backend analytics endpoints consume latest outputs correctly.

## Implemented changes in this phase

### 1) UC09 evaluation hardening

- File updated: `ops/ml/UC09-forecasting/train_cashflow_model.py`
- Change:
  - Replaced weak in-sample fallback with temporal holdout fallback when Prophet CV windows are not feasible.
  - Added holdout metrics logging (`holdout_mae`, `holdout_smape`, `holdout_rows`) and `evaluation_mode` metadata.
- Why:
  - Prevent optimistic bias from in-sample metrics in low-history periods.

### 2) UC09 model artifact loading hint fix

- File updated: `ops/ml/UC09-forecasting/show_training_result.py`
- Change:
  - Corrected model URI hint to Prophet artifact (`runs:/<run_id>/prophet_model`) and loader (`mlflow.prophet.load_model`).
- Why:
  - Avoid operator confusion and wrong loader usage during inference checks.

### 3) UC10 evaluation logging fix

- File updated: `ops/ml/UC10-anomoly_detection/ops-ML-anomaly_detection/train_isolation_forest.py`
- Change:
  - Removed unsupported logger argument (`end=`) and replaced with explicit interpretation logging.
- Why:
  - Ensure full quality output is always visible for run acceptance.

## Fresh training and metric evidence

### UC09 (Prophet)

- Latest run id: `f1b9293a78314092b3eb07fa2d1418c6`
- Key metrics:
  - `evaluation_mode=temporal_holdout`
  - `mape=0.0396`
  - `rmse=147382514099.3615`
  - `holdout_mae=103267505311.7788`
  - `holdout_smape=0.0381`
  - `holdout_rows=27`

Assessment:
- Out-of-sample fallback is active and stable.
- Error profile is consistent with current data scale.

### UC10 (Isolation Forest)

- Latest run id: `b479f5b4a97b4beb918bea1463fd3112`
- Key metrics:
  - `overall_quality_score=0.6284`
  - `silhouette_score=0.2569`
  - `overlap_ratio=0.0000`
  - `score_separation=0.1106`
  - `anomaly_ratio=0.1282`

Assessment:
- Unsupervised quality is acceptable for production baseline.
- Cluster separation and overlap profile are coherent with detection behavior.

## Runtime pipeline validation evidence

### Airflow prediction tasks

- DAG task-test outcomes:
  - `predict_cashflow_uc09`: SUCCESS
  - `detect_anomalies_uc10`: SUCCESS

### Gold table safety checks (Trino)

- Forecast outputs:
  - `forecast_org_null=0`
  - `forecast_dup_keys=0`
  - `forecast_total=30`

- Anomaly outputs:
  - `anomaly_org_null=0`
  - `anomaly_dup_keys=0`
  - `anomaly_total=1000`

Interpretation:
- Tenant key population and idempotency checks passed for current write windows.

### Backend serving smoke

- Forecast endpoint:
  - Response keys: `data, model_name, total_days, timestamp`
  - `FORECAST_LEN=30`

- Anomaly endpoint:
  - Response keys: `data, total_anomalies, severity_breakdown, timestamp`
  - `ANOMALY_LEN=1000`

Interpretation:
- Serving path is functional and returns expected payload structure and data volume.

## Phase 2 gate checklist

- Weekly/adhoc model training successful for UC09 and UC10: PASS
- Daily prediction tasks successful for UC09 and UC10: PASS
- MLflow artifacts available and loadable with corrected hints: PASS
- Forecast/anomaly outputs updated in Gold layer: PASS
- Backend forecast/anomaly endpoints return tenant-consistent datasets: PASS
- Duplicate key checks for validated windows: PASS

## Gate decision

- Gate: PASS
- Phase 2 (ML pipeline and serving correctness): COMPLETE
- Ready to transition to Phase 3, pending user approval.

## Residual risks and monitoring policy

### Residual risks (non-blocking)

- UC10 remains unsupervised; data drift can shift anomaly ratio unexpectedly.
- UC09 holdout slice currently limited (`holdout_rows=27`), so confidence should be increased as more history accumulates.

### Recommended runtime alerts

- UC09 alert if `MAPE > 0.10` or if 7-day moving MAPE doubles from baseline.
- UC10 alert if anomaly ratio exceeds 2x rolling 14-day median.
- Pipeline alert on first consecutive prediction-task failure.

## Rollback notes

- Code rollback:
  - Revert phase-scoped commits touching UC09/UC10 train and result scripts.
- Data rollback:
  - Delete current prediction window rows for impacted model/version/org scope and rerun prediction task.
- Operational rollback:
  - Keep serving endpoint active with last valid Gold snapshot while retraining is re-executed.
