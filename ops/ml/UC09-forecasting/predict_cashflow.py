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
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "file:///tmp/airflow_mlflow")
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
    
    # Load features cho regressors (nếu model có regressors)
    # Đơn giản hóa: giả định features gần nhất cho tất cả future dates
    seasonality_df, macro_df = load_latest_features()
    
    if not seasonality_df.empty:
        # Replicate seasonality features cho future dates
        # Lưu ý: đây là simplification, production nên tính toán chính xác cho từng ngày
        for col in ['is_weekend', 'is_holiday_vn', 'is_beginning_of_month', 'is_end_of_month',
                    'sin_month', 'cos_month', 'sin_day_of_week', 'cos_day_of_week']:
            if col in seasonality_df.columns:
                # Giả định pattern lặp lại
                future[col] = seasonality_df[col].iloc[0]
    
    if not macro_df.empty:
        # Replicate macro features (assume last year's values)
        if 'gdp_growth_annual_pct' in macro_df.columns:
            future['macro_gdp_growth'] = macro_df['gdp_growth_annual_pct'].iloc[0]
        if 'inflation_annual_pct' in macro_df.columns:
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
        forecast_date DATE,
        predicted_cashflow DOUBLE,
        lower_bound DOUBLE,
        upper_bound DOUBLE,
        model_name VARCHAR,
        model_version VARCHAR,
        prediction_timestamp TIMESTAMP
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
    
    # Insert predictions
    insert_sql = """
    INSERT INTO sme_lake.gold.ml_cashflow_forecast 
    (forecast_date, predicted_cashflow, lower_bound, upper_bound, model_name, model_version, prediction_timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    
    prediction_timestamp = datetime.now()
    
    for _, row in predictions_df.iterrows():
        try:
            cursor.execute(insert_sql, (
                row['ds'].date(),
                float(row['yhat']),
                float(row['yhat_lower']),
                float(row['yhat_upper']),
                MODEL_NAME,
                MODEL_VERSION,
                prediction_timestamp
            ))
        except Exception as e:
            logger.error(f"Failed to insert row {row['ds']}: {e}")
    
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
