import pandas as pd
import mlflow
import mlflow.prophet
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, '/opt/ops/ml/UC09-forecasting')
from utils import get_trino_connector

import logging
from datetime import datetime, timedelta

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cấu hình MLflow
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "file:///opt/airflow/mlflow")
MODEL_NAME = "prophet_cashflow_v1"
MODEL_VERSION = os.getenv("MODEL_VERSION", "1")  # Có thể override từ env

def load_latest_features():
    """
    Load features mới nhất từ Trino để làm regressors cho prediction.
    """
    logger.info("Loading latest features from Trino...")
    
    conn = get_trino_connector()
    
    # Load seasonality features
    seasonality_query = """
    SELECT 
        date_actual,
        is_weekend,
        is_holiday_vn,
        month_of_year,
        quarter_of_year,
        day_of_month,
        is_beginning_of_month,
        is_end_of_month,
        sin_month,
        cos_month,
        sin_day_of_week,
        cos_day_of_week
    FROM sme_lake.silver.ftr_seasonality
    WHERE date_actual >= current_date - interval '30' day
    ORDER BY date_actual DESC
    LIMIT 1
    """
    
    seasonality_df = pd.read_sql(seasonality_query, conn)
    
    # Macro features are optional (skipped if ftr_macroeconomic doesn't exist)
    macro_df = pd.DataFrame()  # Empty dataframe
    
    conn.close()
    
    return seasonality_df, macro_df


def load_active_org_ids(cursor):
    """Load active organization IDs for tenant-safe forecast writes."""
    queries = [
        "SELECT DISTINCT org_id FROM sme_lake.silver.stg_payments_app_db WHERE org_id IS NOT NULL",
        "SELECT DISTINCT org_id FROM sme_lake.silver.stg_ar_invoices_app_db WHERE org_id IS NOT NULL",
    ]

    org_ids = set()
    for query in queries:
        try:
            cursor.execute(query)
            for row in cursor.fetchall():
                if row and row[0] is not None:
                    org_ids.add(int(row[0]))
        except Exception as e:
            logger.warning(f"Could not load org IDs from query [{query}]: {e}")

    if not org_ids:
        env_org_ids = os.getenv("ML_ORG_IDS", "").strip()
        if env_org_ids:
            parsed = sorted({int(x.strip()) for x in env_org_ids.split(',') if x.strip()})
            if parsed:
                logger.warning(f"No tenant org_id found in Trino sources. Using ML_ORG_IDS={parsed}")
                return parsed

        default_org_id = int(os.getenv("DEFAULT_ORG_ID", "1"))
        logger.warning(
            f"No tenant org_id found in app_db silver tables. Falling back to DEFAULT_ORG_ID={default_org_id}."
        )
        return [default_org_id]

    return sorted(org_ids)

def predict_cashflow(forecast_days: int = 30):
    """
    Dự báo dòng tiền trong N ngày tới.
    
    Args:
        forecast_days: Số ngày dự báo (mặc định 30 ngày)
    
    Returns:
        DataFrame chứa dự báo với columns: ds, yhat, yhat_lower, yhat_upper
    """
    logger.info(f"Starting cashflow prediction for next {forecast_days} days...")
    
    # Load model từ MLflow Model Registry (best practice)
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    
    try:
        # Try to load from Model Registry (production)
        logger.info(f"Loading model from registry: {MODEL_NAME} version {MODEL_VERSION}...")
        model_uri = f"models:/{MODEL_NAME}/{MODEL_VERSION}"
        model = mlflow.prophet.load_model(model_uri)
        logger.info(f"✅ Model loaded from registry successfully!")
    except Exception as e:
        logger.warning(f"Failed to load from registry: {e}")
        logger.info("Falling back to latest run...")
        
        # Fallback: load từ run gần nhất (for development)
        client = mlflow.tracking.MlflowClient()
        experiment = client.get_experiment_by_name("sme_pulse_cashflow_forecast")
        if not experiment:
            raise Exception("Experiment 'sme_pulse_cashflow_forecast' not found! Please train the model first.")
        
        runs = client.search_runs(
            experiment_ids=[experiment.experiment_id],
            order_by=["start_time DESC"],
            max_results=1
        )
        if not runs:
            raise Exception("No trained runs found in experiment! Please train the model first.")
        
        run_id = runs[0].info.run_id
        model_uri = f"runs:/{run_id}/prophet_model"
        logger.info(f"Loading model from run: {model_uri}")
        model = mlflow.prophet.load_model(model_uri)
    
    # Tạo future dataframe
    future = model.make_future_dataframe(periods=forecast_days, freq='D')

    # Prophet stores regressors as a dict {name: metadata}
    model_regressors = getattr(model, 'extra_regressors', None)
    if model_regressors is None:
        model_regressors = getattr(model, 'extra_regressors_', None)
    regressor_names = set(model_regressors.keys()) if isinstance(model_regressors, dict) else set()
    
    # Load features cho regressors (nếu model có regressors)
    # Đơn giản hóa: giả định features gần nhất cho tất cả future dates
    seasonality_df, macro_df = load_latest_features()
    
    # --- FIX [P1]: Compute per-day features instead of replicating a single row ---
    import math

    if not seasonality_df.empty:
        future['is_weekend'] = future['ds'].dt.dayofweek.isin([5, 6]).astype(int)
        future['is_beginning_of_month'] = (future['ds'].dt.day <= 5).astype(int)
        future['is_end_of_month'] = (future['ds'].dt.day >= 25).astype(int)
        future['sin_month'] = future['ds'].dt.month.apply(lambda m: math.sin(2 * math.pi * m / 12))
        future['cos_month'] = future['ds'].dt.month.apply(lambda m: math.cos(2 * math.pi * m / 12))
        future['sin_day_of_week'] = future['ds'].dt.dayofweek.apply(lambda d: math.sin(2 * math.pi * d / 7))
        future['cos_day_of_week'] = future['ds'].dt.dayofweek.apply(lambda d: math.cos(2 * math.pi * d / 7))

        # Vietnamese holidays (Tet, Reunification, National Day, etc.) — approximate
        vn_holidays_mmdd = {'01-01', '04-30', '05-01', '09-02'}
        future['is_holiday_vn'] = future['ds'].dt.strftime('%m-%d').isin(vn_holidays_mmdd).astype(int)

        # Only assign columns the model actually expects as regressors
        for col in list(future.columns):
            if col not in ('ds', 'y') and col not in regressor_names:
                future.drop(columns=[col], inplace=True, errors='ignore')

    if not macro_df.empty:
        # Macro features are annual — safe to replicate latest known value
        if 'gdp_growth_annual_pct' in macro_df.columns and 'macro_gdp_growth' in regressor_names:
            future['macro_gdp_growth'] = macro_df['gdp_growth_annual_pct'].iloc[0]
        if 'inflation_annual_pct' in macro_df.columns and 'macro_inflation' in regressor_names:
            future['macro_inflation'] = macro_df['inflation_annual_pct'].iloc[0]
    
    # Predict
    logger.info("Making predictions...")
    forecast = model.predict(future)
    
    # Chỉ lấy phần future (không lấy historical)
    # Tính từ ngày cuối cùng của training data
    last_historical_date = future['ds'].iloc[-forecast_days - 1] if len(future) > forecast_days else future['ds'].min()
    forecast_future = forecast[forecast['ds'] > last_historical_date].tail(forecast_days).copy()
    
    logger.info(f"Generated {len(forecast_future)} predictions.")
    
    return forecast_future[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]

def save_predictions_to_trino(predictions_df: pd.DataFrame):
    """
    Lưu predictions vào Gold layer để Metabase visualization.
    """
    logger.info("Saving predictions to Trino Gold layer...")
    
    conn = get_trino_connector()
    cursor = conn.cursor()
    
    # Tạo table nếu chưa có
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS sme_lake.gold.ml_cashflow_forecast (
        org_id BIGINT,
        forecast_date DATE,
        predicted_cashflow DOUBLE,
        lower_bound DOUBLE,
        upper_bound DOUBLE,
        model_name VARCHAR,
        model_version VARCHAR,
        prediction_timestamp TIMESTAMP,
        prediction_run_id VARCHAR,
        forecast_generated_date DATE
    )
    WITH (
        format = 'PARQUET'
    )
    """
    
    try:
        cursor.execute(create_table_sql)
        logger.info("Table ml_cashflow_forecast created/verified.")
    except Exception as e:
        logger.warning(f"Table creation warning (may already exist): {e}")

    # Backward-compatible schema evolution for existing tables
    alter_statements = [
        "ALTER TABLE sme_lake.gold.ml_cashflow_forecast ADD COLUMN org_id BIGINT",
        "ALTER TABLE sme_lake.gold.ml_cashflow_forecast ADD COLUMN prediction_run_id VARCHAR",
        "ALTER TABLE sme_lake.gold.ml_cashflow_forecast ADD COLUMN forecast_generated_date DATE",
    ]
    for alter_sql in alter_statements:
        try:
            cursor.execute(alter_sql)
        except Exception as e:
            logger.info(f"Schema evolution note (likely already applied): {e}")
    
    # --- FIX [P2]: Batch INSERT instead of row-by-row (30 Iceberg commits → 1) ---
    prediction_timestamp = datetime.now()
    prediction_run_id = prediction_timestamp.strftime("%Y%m%d%H%M%S")
    forecast_generated_date = prediction_timestamp.date()
    org_ids = load_active_org_ids(cursor)

    min_forecast_date = predictions_df['ds'].min().strftime('%Y-%m-%d')
    max_forecast_date = predictions_df['ds'].max().strftime('%Y-%m-%d')
    org_id_list_sql = ", ".join(str(org_id) for org_id in org_ids)

    # Idempotent strategy: delete same model-version window then insert
    delete_sql = (
        "DELETE FROM sme_lake.gold.ml_cashflow_forecast "
        f"WHERE model_name = '{MODEL_NAME}' "
        f"AND model_version = '{MODEL_VERSION}' "
        f"AND forecast_date BETWEEN DATE '{min_forecast_date}' AND DATE '{max_forecast_date}' "
        f"AND org_id IN ({org_id_list_sql})"
    )
    try:
        cursor.execute(delete_sql)
        logger.info("Deleted existing forecast rows for idempotent rewrite.")
    except Exception as e:
        logger.warning(f"Delete phase warning (continuing): {e}")

    values_list = []
    for org_id in org_ids:
        for _, row in predictions_df.iterrows():
            values_list.append(
                f"({org_id}, "
                f"DATE '{row['ds'].strftime('%Y-%m-%d')}', "
                f"{float(row['yhat']):.4f}, "
                f"{float(row['yhat_lower']):.4f}, "
                f"{float(row['yhat_upper']):.4f}, "
                f"'{MODEL_NAME}', '{MODEL_VERSION}', "
                f"TIMESTAMP '{prediction_timestamp.strftime('%Y-%m-%d %H:%M:%S')}', "
                f"'{prediction_run_id}', "
                f"DATE '{forecast_generated_date.strftime('%Y-%m-%d')}')"
            )

    if values_list:
        batch_sql = (
            "INSERT INTO sme_lake.gold.ml_cashflow_forecast "
            "(org_id, forecast_date, predicted_cashflow, lower_bound, upper_bound, "
            "model_name, model_version, prediction_timestamp, prediction_run_id, forecast_generated_date) VALUES\n"
            + ",\n".join(values_list)
        )
        try:
            cursor.execute(batch_sql)
            logger.info(
                f"Batch-inserted {len(values_list)} forecast rows for {len(org_ids)} org(s) in a single commit."
            )
        except Exception as e:
            logger.error(f"Batch insert failed: {e}")
            raise
    
    conn.close()
    logger.info(f"Saved {len(predictions_df)} predictions to Gold layer.")

if __name__ == "__main__":
    try:
        # Dự báo 30 ngày
        predictions = predict_cashflow(forecast_days=30)
        
        logger.info("\n=== Sample Predictions ===")
        logger.info(f"\n{predictions.head(10)}")
        
        # Lưu vào Trino
        save_predictions_to_trino(predictions)
        
        logger.info("\n✅ Cashflow prediction completed successfully!")
        
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise
