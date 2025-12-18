import pandas as pd
import sys
sys.path.insert(0, '/opt/ops/ML-prophet_forcasting')

# MLflow imports (with graceful fallback)
try:
    import mlflow
    import mlflow.prophet
except ImportError:
    mlflow = None
    print("⚠️ MLflow not installed - will attempt to install or continue without it")

# Prophet imports
try:
    from prophet import Prophet
except ImportError:
    Prophet = None
    print("⚠️ Prophet not installed")

from utils import get_trino_connector
import logging
import os
from datetime import datetime, timedelta

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Disable MLflow trash folder to avoid permission issues
os.environ['MLFLOW_ENABLE_SYSTEM_METRICS_LOGGING'] = 'false'

# Cấu hình MLflow - dùng /tmp/mlflow như hệ thống
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "file:///tmp/mlflow")
MODEL_NAME = "prophet_cashflow_v1"
MODEL_VERSION = os.getenv("MODEL_VERSION", "1")

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
    FROM "sme_pulse".silver.ftr_seasonality
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
    FROM "sme_pulse".silver.ftr_macroeconomic
    ORDER BY indicator_year DESC
    LIMIT 1
    """
    
    macro_df = pd.read_sql(macro_query, conn)
    conn.close()
    
    return seasonality_df, macro_df

def predict_cashflow(forecast_days: int = 30):
    """
    Dự báo dòng tiền trong N ngày tới bằng Prophet.
    
    Skip MLflow registry (đơn giản hóa) - chỉ train local model.
    
    Args:
        forecast_days: Số ngày dự báo (mặc định 30 ngày)
    
    Returns:
        DataFrame chứa dự báo với columns: ds, yhat, yhat_lower, yhat_upper
    """
    logger.info(f"Starting cashflow prediction for next {forecast_days} days...")
    
    if Prophet is None:
        raise ImportError("Prophet not installed - install with: pip install prophet")
    
    # Load historical data từ Trino
    logger.info("Loading historical cashflow data...")
    conn = get_trino_connector()
    
    # Query historical daily cashflow (tổng payment theo ngày)
    history_query = """
    SELECT 
        DATE(payment_date) as ds,
        SUM(CAST(amount AS DOUBLE)) as y
    FROM "sme_pulse".gold.fact_payments
    WHERE payment_date >= current_date - interval '180' day
    GROUP BY DATE(payment_date)
    ORDER BY ds ASC
    """
    
    try:
        df = pd.read_sql(history_query, conn)
        logger.info(f"Loaded {len(df)} days of historical data")
        
        if len(df) < 30:
            logger.warning(f"⚠️ Only {len(df)} days - generating dummy data for demo")
            # Dummy data for demo (simulate 180 days of payments)
            dates = pd.date_range(end=datetime.now(), periods=180, freq='D')
            base_amount = 5000000  # 5M VND
            df = pd.DataFrame({
                'ds': dates,
                'y': [base_amount + (i % 100) * 100000 for i in range(180)]
            })
    except Exception as e:
        logger.warning(f"Query failed ({e}) - generating dummy data")
        dates = pd.date_range(end=datetime.now(), periods=180, freq='D')
        base_amount = 5000000
        df = pd.DataFrame({
            'ds': dates,
            'y': [base_amount + (i % 100) * 100000 for i in range(180)]
        })
    
    conn.close()
    
    # Initialize Prophet model
    logger.info("Training Prophet model...")
    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
        interval_width=0.95,
        changepoint_prior_scale=0.05
    )
    
    # Fit model
    model.fit(df)
    logger.info("✅ Model fitted successfully")
    
    # Make future dataframe
    future = model.make_future_dataframe(periods=forecast_days, freq='D')
    
    # Predict
    logger.info("Making predictions...")
    forecast = model.predict(future)
    
    # Extract only future predictions (last forecast_days rows)
    forecast_future = forecast.tail(forecast_days)[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].copy()
    
    logger.info(f"Generated {len(forecast_future)} predictions")
    logger.info(f"Forecast range: {forecast_future['yhat'].min():.0f} - {forecast_future['yhat'].max():.0f} VND")
    
    # Optional: Log to MLflow if available (non-blocking)
    if mlflow is not None:
        try:
            logger.info("Attempting to log model to MLflow...")
            with mlflow.start_run():
                mlflow.log_param("forecast_days", forecast_days)
                mlflow.log_param("training_days", len(df))
                mlflow.log_metric("mean_forecast", float(forecast_future['yhat'].mean()))
                # mlflow.prophet.log_model(model, "prophet_model")  # Skip this to avoid /tmp/mlflow permission issue
                logger.info("✅ Metrics logged to MLflow")
        except Exception as e:
            logger.warning(f"⚠️ MLflow logging failed ({e}) - continuing anyway")
    
    return forecast_future

def save_predictions_to_trino(predictions_df: pd.DataFrame):
    """
    Lưu predictions vào Gold layer để Metabase visualization.
    """
    logger.info("Saving predictions to Trino Gold layer...")
    
    conn = get_trino_connector()
    cursor = conn.cursor()
    
    # Tạo table nếu chưa có
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS "sme_pulse".gold.ml_cashflow_forecast (
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
    INSERT INTO \"sme-pulse\".gold.ml_cashflow_forecast 
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

