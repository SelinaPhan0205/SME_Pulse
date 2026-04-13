import pandas as pd
import mlflow
import mlflow.prophet
from prophet import Prophet
from prophet.diagnostics import cross_validation, performance_metrics
import sys
import os
import numpy as np

# Add current directory to path for imports
sys.path.insert(0, '/opt/ops/ml/UC09-forecasting')
from utils import get_trino_connector

import logging

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cấu hình MLflow (Dùng local filesystem với quyền write)
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "file:///opt/airflow/mlflow")
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
        df = df.sort_values('ds').reset_index(drop=True)
        
        # 2. Chuẩn bị Regressors (Các biến ngoại sinh)
        # Prophet tự động hiểu 'ds' và 'y'.
        # Chúng ta cần đăng ký các cột feature khác làm "regressors".
        # NOTE: macro_gdp_growth and macro_inflation removed - World Bank data not available
        regressors = [
            'is_weekend', 'is_holiday_vn', 'is_beginning_of_month', 'is_end_of_month',
            'sin_month', 'cos_month', 'sin_day_of_week', 'cos_day_of_week'
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
            logger.info("Running model evaluation...")
            data_span_days = int((df['ds'].max() - df['ds'].min()).days)
            horizon_days = max(7, min(30, data_span_days // 5 if data_span_days > 0 else 7))
            initial_days = max(30, min(365, data_span_days - horizon_days - 1))
            period_days = max(7, min(90, horizon_days // 2))

            if data_span_days > (horizon_days + initial_days + 1):
                logger.info(
                    f"Cross-validation windows: initial={initial_days}d, period={period_days}d, horizon={horizon_days}d"
                )
                df_cv = cross_validation(
                    model,
                    initial=f'{initial_days} days',
                    period=f'{period_days} days',
                    horizon=f'{horizon_days} days'
                )
                df_p = performance_metrics(df_cv)

                mape = float(df_p['mape'].mean())
                rmse = float(df_p['rmse'].mean())
                logger.info(f"Cross-Validation MAPE: {mape}")
                mlflow.log_metric("mape", mape)
                mlflow.log_metric("rmse", rmse)
                mlflow.log_param("evaluation_mode", "cross_validation")
            else:
                logger.warning(
                    "Insufficient history for Prophet CV windows. Falling back to temporal holdout evaluation."
                )
                split_idx = max(1, int(len(df) * 0.8))
                train_df = df.iloc[:split_idx].copy()
                holdout_df = df.iloc[split_idx:].copy()

                if len(holdout_df) == 0:
                    holdout_df = df.tail(1).copy()
                    train_df = df.iloc[:-1].copy()

                eval_model = Prophet(yearly_seasonality=True, weekly_seasonality=True, daily_seasonality=False)
                eval_model.add_country_holidays(country_name='VN')
                for reg in regressors:
                    eval_model.add_regressor(reg)
                eval_model.fit(train_df)

                holdout_input_cols = ['ds'] + regressors
                holdout_forecast = eval_model.predict(holdout_df[holdout_input_cols])

                y_true = holdout_df['y'].astype(float).values
                y_pred = holdout_forecast['yhat'].astype(float).values
                denominator = np.where(np.abs(y_true) < 1e-9, 1.0, np.abs(y_true))
                mape = float(np.mean(np.abs((y_true - y_pred) / denominator)))
                rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
                mae = float(np.mean(np.abs(y_true - y_pred)))
                smape = float(np.mean(2.0 * np.abs(y_pred - y_true) / (np.abs(y_true) + np.abs(y_pred) + 1e-9)))

                mlflow.log_metric("mape", mape)
                mlflow.log_metric("rmse", rmse)
                mlflow.log_metric("holdout_mae", mae)
                mlflow.log_metric("holdout_smape", smape)
                mlflow.log_metric("holdout_rows", len(holdout_df))
                mlflow.log_param("evaluation_mode", "temporal_holdout")
                mlflow.log_param("cv_skipped", True)
                mlflow.log_param("cv_skip_reason", "insufficient_history")
            
            # 6. Log Model (Quan trọng nhất: lưu lại model đã train)
            logger.info("Logging model to MLflow...")
            model_info = mlflow.prophet.log_model(
                model, 
                artifact_path="prophet_model",
                registered_model_name="prophet_cashflow_v1"  # Register to Model Registry
            )
            logger.info(f"Model registered to Model Registry: prophet_cashflow_v1")
            
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