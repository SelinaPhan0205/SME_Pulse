import pandas as pd
import mlflow
import mlflow.prophet
from ops.ml.utils import get_trino_connector
import logging
import os
from datetime import datetime, timedelta

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cấu hình MLflow
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "file:///tmp/mlflow")
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
    
    # Load macro features
    macro_query = """
    SELECT 
        indicator_year,
        gdp_growth_annual_pct,
        inflation_annual_pct,
        unemployment_rate_pct
    FROM sme_lake.silver.ftr_macroeconomic
    ORDER BY indicator_year DESC
    LIMIT 1
    """
    
    macro_df = pd.read_sql(macro_query, conn)
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
    
    # Load model từ MLflow
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    model_uri = f"models:/{MODEL_NAME}/{MODEL_VERSION}"
    
    try:
        logger.info(f"Loading model from {model_uri}...")
        model = mlflow.prophet.load_model(model_uri)
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        logger.info("Attempting to load from latest run...")
        # Fallback: load từ run gần nhất
        client = mlflow.tracking.MlflowClient()
        experiment = client.get_experiment_by_name("sme_pulse_cashflow_forecast")
        if experiment:
            runs = client.search_runs(
                experiment_ids=[experiment.experiment_id],
                order_by=["start_time DESC"],
                max_results=1
            )
            if runs:
                run_id = runs[0].info.run_id
                model_uri = f"runs:/{run_id}/prophet_model"
                logger.info(f"Loading from run: {model_uri}")
                model = mlflow.prophet.load_model(model_uri)
            else:
                raise Exception("No trained model found!")
        else:
            raise Exception("Experiment not found!")
    
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
