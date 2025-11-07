import pandas as pd
import mlflow
import mlflow.prophet
from prophet import Prophet
from prophet.diagnostics import cross_validation, performance_metrics
from ops.ml.utils import get_trino_connector # Import hàm helper
import logging
import os

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cấu hình MLflow (Dùng local filesystem nếu không có MLflow server)
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "file:///tmp/mlflow")
MLFLOW_EXPERIMENT_NAME = "sme_pulse_cashflow_forecast"

def train_cashflow_forecast():
    """
    Script chính để huấn luyện và lưu trữ mô hình Prophet.
    """
    logger.info("Starting cashflow forecast training...")
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)

    try:
        # 1. Load Data (Đọc từ "mâm cơm" dbt đã chuẩn bị)
        logger.info("Loading data from Trino...")
        conn = get_trino_connector()
        query = "SELECT * FROM sme_lake.silver.ml_training_cashflow_fcst"
        df = pd.read_sql(query, conn)
        
        if df.empty:
            logger.warning("No data found. Skipping training.")
            return

        # Dữ liệu 501 rows là hơi ít, nhưng đủ để chạy
        logger.info(f"Loaded {len(df)} rows from ml_training_cashflow_fcst.")
        
        # 2. Chuẩn bị Regressors (Các biến ngoại sinh)
        # Prophet tự động hiểu 'ds' và 'y'.
        # Chúng ta cần đăng ký các cột feature khác làm "regressors".
        regressors = [
            'is_weekend', 'is_holiday_vn', 'is_beginning_of_month', 'is_end_of_month',
            'sin_month', 'cos_month', 'sin_day_of_week', 'cos_day_of_week',
            'macro_gdp_growth', 'macro_inflation'
        ]
        
        # Bắt đầu 1 "Run" trong MLflow
        with mlflow.start_run() as run:
            
            # 3. Khởi tạo & Huấn luyện Model
            logger.info("Initializing Prophet model...")
            # Thêm các ngày lễ của VN (Prophet có sẵn)
            model = Prophet(yearly_seasonality=True, weekly_seasonality=True, daily_seasonality=False)
            model.add_country_holidays(country_name='VN')
            
            # Thêm các regressors
            for reg in regressors:
                model.add_regressor(reg)

            logger.info("Fitting model...")
            model.fit(df)
            
            # 4. Log Parameters (Lưu lại thông số)
            mlflow.log_param("model_type", "Prophet")
            mlflow.log_param("regressors", regressors)
            mlflow.log_param("training_rows", len(df))
            mlflow.log_param("data_start_date", df['ds'].min())
            mlflow.log_param("data_end_date", df['ds'].max())
            
            # 5. Đánh giá Model (Backtesting)
            # Chạy cross-validation 30 ngày, 3 lần
            logger.info("Running cross-validation...")
            df_cv = cross_validation(model, initial='365 days', period='90 days', horizon='30 days')
            df_p = performance_metrics(df_cv)
            
            # Log Metrics (Lưu lại kết quả đánh giá)
            mape = df_p['mape'].mean()
            logger.info(f"Cross-Validation MAPE: {mape}")
            mlflow.log_metric("mape", mape)
            mlflow.log_metric("rmse", df_p['rmse'].mean())
            
            # 6. Log Model (Quan trọng nhất: lưu lại model đã train)
            logger.info("Logging model to MLflow...")
            mlflow.prophet.log_model(model, 
                                     artifact_path="prophet_model",
                                     registered_model_name="prophet_cashflow_v1") # Đăng ký tên model
            
            # 7. Log Artifacts (Plots)
            future = model.make_future_dataframe(periods=30)
            # Thêm regressors cho tương lai (cần logic phức tạp hơn)
            # Tạm thời log plot components
            fig = model.plot_components(model.predict(df))
            mlflow.log_figure(fig, "forecast_components.png")

            logger.info(f"Model trained successfully! Run ID: {run.info.run_id}")

    except Exception as e:
        logger.error(f"Training failed: {e}")
        raise

if __name__ == "__main__":
    # Lệnh này cho phép bạn chạy file thủ công để test
    train_cashflow_forecast()