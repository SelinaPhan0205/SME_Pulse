"""
UC10 - Anomaly Detection: Daily Anomaly Detection Script
========================================================
Chạy hàng ngày để:
1. Load mô hình đã trained từ MLflow
2. Load giao dịch mới (của hôm nay hoặc N ngày gần)
3. Tính toán anomaly scores
4. Lưu alerts vào Gold layer (ml_anomaly_alerts)
5. Ghi lại thống kê vào Gold layer (ml_anomaly_statistics)

Có thể tích hợp với Airflow DAG để chạy tự động
"""

import sys
sys.path.insert(0, '/opt/ops/ml/UC10-anomoly_detection/ops-ML-anomaly_detection')

import pandas as pd
import numpy as np
import mlflow
import mlflow.sklearn
from utils import get_trino_connector
import logging
import os
import pickle
import json
import time
from datetime import datetime, timedelta

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Cấu hình MLflow
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "file:///tmp/mlflow")
MODEL_NAME = "isolation_forest_anomaly_v1"
MODEL_VERSION = os.getenv("MODEL_VERSION", "1")

# Cấu hình Detection
DETECTION_DAYS = 7  # Lấy N ngày gần nhất để kiểm tra
ANOMALY_SCORE_THRESHOLD = -0.5  # Scores < threshold được coi là anomaly
ALERT_SEVERITY_MAPPING = {
    'CRITICAL': -1.0,      # Rất bất thường
    'HIGH': -0.75,         # Khá bất thường
    'MEDIUM': -0.5,        # Bất thường trung bình
}


def load_model_and_scaler():
    """
    Load mô hình và scaler từ local artifacts (fallback from MLflow).
    
    Returns:
        tuple: (model, scaler, feature_names)
    """
    logger.info("=" * 80)
    logger.info("BƯỚC 1: LOADING MODEL FROM ARTIFACTS")
    logger.info("=" * 80)
    
    artifacts_dir = "/tmp/mlflow_artifacts"
    
    # Try local artifacts first
    model_path = os.path.join(artifacts_dir, "isolation_forest_model.pkl")
    scaler_path = os.path.join(artifacts_dir, "scaler.pkl")
    features_path = os.path.join(artifacts_dir, "features.json")
    
    if os.path.exists(model_path) and os.path.exists(scaler_path) and os.path.exists(features_path):
        logger.info(f"\nLoading model from local artifacts: {artifacts_dir}")
        
        try:
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
            logger.info("✅ Model loaded!")
            
            with open(scaler_path, 'rb') as f:
                scaler = pickle.load(f)
            logger.info("✅ Scaler loaded!")
            
            with open(features_path, 'r') as f:
                features_data = json.load(f)
            feature_names = features_data['features']
            logger.info(f"✅ Features loaded! ({len(feature_names)} features)")
            
            return model, scaler, feature_names
        
        except Exception as e:
            logger.warning(f"Failed to load from local artifacts: {e}")
    
    # Fallback: try MLflow registry
    logger.info("Falling back to MLflow registry...")
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    
    try:
        logger.info(f"\nLoading model from registry: {MODEL_NAME} version {MODEL_VERSION}...")
        model_uri = f"models:/{MODEL_NAME}/{MODEL_VERSION}"
        model = mlflow.sklearn.load_model(model_uri)
        logger.info(f"✅ Model loaded from registry!")
        
        # Load artifacts from latest run
        client = mlflow.tracking.MlflowClient()
        experiment = client.get_experiment_by_name("sme_pulse_anomaly_detection")
        
        if not experiment:
            raise Exception("Experiment not found!")
        
        runs = client.search_runs(
            experiment_ids=[experiment.experiment_id],
            order_by=["start_time DESC"],
            max_results=1
        )
        
        if not runs:
            raise Exception("No trained runs found!")
        
        run_id = runs[0].info.run_id
        logger.info(f"Loading artifacts from run: {run_id}")
        
        # Load scaler and features from MLflow
        os.makedirs(artifacts_dir, exist_ok=True)
        client.download_artifacts(run_id, "scaler.pkl", artifacts_dir)
        client.download_artifacts(run_id, "features.json", artifacts_dir)
        
        with open(os.path.join(artifacts_dir, "scaler.pkl"), 'rb') as f:
            scaler = pickle.load(f)
        
        with open(os.path.join(artifacts_dir, "features.json"), 'r') as f:
            features_data = json.load(f)
        feature_names = features_data['features']
        
        logger.info("✅ All artifacts loaded from MLflow!")
        return model, scaler, feature_names
        
    except Exception as e:
        logger.error(f"\n❌ DETECTION FAILED: {e}")
        logger.error("Please ensure the model has been trained first using train_isolation_forest.py")
        raise


def load_new_transactions(days=DETECTION_DAYS):
    """
    Load giao dịch mới để kiểm tra (N ngày gần nhất).
    
    Args:
        days (int): Số ngày gần nhất
    
    Returns:
        pd.DataFrame: Giao dịch mới
    """
    logger.info("\n" + "=" * 80)
    logger.info("BƯỚC 2: LOADING NEW TRANSACTIONS FOR DETECTION")
    logger.info("=" * 80)
    
    conn = get_trino_connector()
    
    query = f"""
    WITH date_range AS (
        SELECT MAX(txn_date) as max_date FROM "sme_pulse".gold.fact_bank_txn
    )
    SELECT 
        txn_id,
        txn_date,
        amount_vnd,
        direction_in_out,
        currency_code,
        counterparty_name,
        is_inflow,
        is_large_transaction,
        transaction_category,
        created_at
    FROM "sme_pulse".gold.fact_bank_txn d,
         date_range
    WHERE d.txn_date >= date_range.max_date - interval '{days}' day
    ORDER BY txn_date DESC
    """
    
    logger.info(f"\nLoading transactions from last {days} days...")
    df = pd.read_sql(query, conn)
    conn.close()
    
    # Convert txn_date to datetime
    if len(df) > 0:
        df['txn_date'] = pd.to_datetime(df['txn_date'])
    
    logger.info(f"✅ Loaded {len(df):,} transactions")
    logger.info(f"   Date range: {df['txn_date'].min()} to {df['txn_date'].max()}")
    
    return df


def engineer_features_for_detection(df):
    """
    Tính toán features cho dữ liệu detection (tương tự training - KHỚP 100%).
    
    Args:
        df (pd.DataFrame): Giao dịch mới
    
    Returns:
        tuple: (df_features, df_sorted) - Feature matrix + dataframe with features
    """
    logger.info("\n" + "=" * 80)
    logger.info("BƯỚC 3: FEATURE ENGINEERING FOR NEW DATA")
    logger.info("=" * 80)
    
    df = df.copy()
    
    # Ensure txn_date and txn_timestamp are datetime
    df['txn_date'] = pd.to_datetime(df['txn_date'])
    df['txn_timestamp'] = pd.to_datetime(df['txn_timestamp']) if 'txn_timestamp' in df.columns else df['txn_date']
    
    logger.info("[1] Computing basic features...")
    # 1. Basic features
    df['amount_log'] = np.log1p(np.abs(df['amount_vnd']))
    df['is_inflow'] = (df['direction_in_out'] == 'in').astype(int)
    df['is_large'] = (df['is_large_transaction']).astype(int)
    
    # 2. Time features
    logger.info("[2] Computing time features...")
    df['hour_of_day'] = df['txn_timestamp'].dt.hour
    df['day_of_week'] = df['txn_timestamp'].dt.dayofweek
    df['day_of_month'] = df['txn_timestamp'].dt.day
    df['is_weekend'] = (df['day_of_week'].isin([5, 6])).astype(int)
    
    # 3. Rolling statistics (7 days) - calculate per transaction date
    logger.info("[3] Computing 7-day rolling statistics...")
    df_sorted = df.sort_values('txn_date').reset_index(drop=True)
    
    # Calculate daily aggregates then merge back (same as training)
    daily_stats = df_sorted.groupby(df_sorted['txn_date'].dt.date).agg({
        'amount_vnd': ['std', 'mean', lambda x: x.abs().max()],
    }).rolling(7, min_periods=1).mean()
    daily_stats.columns = ['amount_std_7d', 'amount_mean_7d', 'amount_max_7d']
    daily_stats = daily_stats.reset_index()
    daily_stats.rename(columns={'txn_date': 'date_key'}, inplace=True)
    daily_stats['date_key'] = pd.to_datetime(daily_stats['date_key'])
    
    # Count transactions per day
    daily_count = df_sorted.groupby(df_sorted['txn_date'].dt.date).size().rolling(7, min_periods=1).sum()
    daily_count.name = 'txn_count_7d'
    daily_count = daily_count.reset_index()
    daily_count.rename(columns={'txn_date': 'date_key'}, inplace=True)
    daily_count['date_key'] = pd.to_datetime(daily_count['date_key'])
    
    # Merge back to main dataframe
    df_sorted['txn_date_key'] = df_sorted['txn_date'].dt.date.astype('datetime64[ns]')
    df_sorted = df_sorted.merge(daily_count[['date_key', 'txn_count_7d']], left_on='txn_date_key', right_on='date_key', how='left')
    df_sorted = df_sorted.merge(daily_stats[['date_key', 'amount_std_7d', 'amount_mean_7d', 'amount_max_7d']], left_on='txn_date_key', right_on='date_key', how='left')
    
    # 4. Categorical features (one-hot encoding)
    logger.info("[4] Computing categorical features...")
    df_sorted['cat_receivable'] = (df_sorted['transaction_category'] == 'RECEIVABLE').astype(int)
    df_sorted['cat_payable'] = (df_sorted['transaction_category'] == 'PAYABLE').astype(int)
    df_sorted['cat_payroll'] = (df_sorted['transaction_category'] == 'PAYROLL').astype(int)
    df_sorted['cat_other'] = (~df_sorted['transaction_category'].isin(['RECEIVABLE', 'PAYABLE', 'PAYROLL'])).astype(int)
    
    # Select features (same order as training)
    feature_cols = [
        'amount_vnd', 'amount_log', 'is_inflow', 'is_large',
        'hour_of_day', 'day_of_week', 'day_of_month', 'is_weekend',
        'txn_count_7d', 'amount_std_7d', 'amount_mean_7d', 'amount_max_7d',
        'cat_receivable', 'cat_payable', 'cat_payroll', 'cat_other'
    ]
    
    df_features = df_sorted[feature_cols].copy()
    df_features = df_features.fillna(df_features.mean(numeric_only=True))
    
    logger.info(f"\n✅ Generated {len(feature_cols)} features for {len(df_features):,} transactions")
    
    return df_features, df_sorted


def detect_anomalies(model, scaler, df_features, df_with_features):
    """
    Phát hiện anomalies bằng mô hình Isolation Forest.
    
    Args:
        model: Trained model
        scaler: StandardScaler
        df_features: Feature matrix
        df_with_features: Original dataframe + features
    
    Returns:
        pd.DataFrame: Dataframe với anomaly_score, is_anomaly, severity
    """
    logger.info("\n" + "=" * 80)
    logger.info("BƯỚC 4: ANOMALY DETECTION")
    logger.info("=" * 80)
    
    # Scale features
    X_scaled = scaler.transform(df_features)
    
    # Get anomaly scores
    anomaly_scores = model.score_samples(X_scaled)
    predictions = model.predict(X_scaled)
    
    # Create results dataframe
    results = df_with_features[['txn_id', 'txn_date', 'amount_vnd', 'direction_in_out', 'counterparty_name', 'transaction_category']].copy()
    results['anomaly_score'] = anomaly_scores
    results['is_anomaly'] = (predictions == -1).astype(int)
    
    # Assign severity
    def assign_severity(score):
        for severity, threshold in sorted(ALERT_SEVERITY_MAPPING.items(), key=lambda x: x[1], reverse=True):
            if score <= threshold:
                return severity
        return 'LOW'
    
    results['severity'] = results['anomaly_score'].apply(assign_severity)
    results['detection_timestamp'] = datetime.now()
    
    # Statistics
    n_anomalies = (predictions == -1).sum()
    logger.info(f"\n✅ Detection completed!")
    logger.info(f"   Total transactions: {len(results):,}")
    logger.info(f"   Anomalies detected: {n_anomalies:,} ({100*n_anomalies/len(results):.2f}%)")
    logger.info(f"\n   Severity breakdown:")
    for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
        count = (results['severity'] == severity).sum()
        logger.info(f"     - {severity}: {count:,}")
    
    if n_anomalies > 0:
        logger.info(f"\n   Top 5 anomalies (lowest scores):")
        top_anomalies = results[results['is_anomaly'] == 1].nsmallest(5, 'anomaly_score')
        for idx, row in top_anomalies.iterrows():
            logger.info(f"     - TXN {row['txn_id']}: {row['txn_date']} | Amount: {row['amount_vnd']:,.0f} VND | Score: {row['anomaly_score']:.4f} | {row['severity']}")
    
    return results


def save_alerts_to_trino(alerts_df):
    """
    Lưu alerts vào Gold layer (ml_anomaly_alerts).
    
    Args:
        alerts_df (pd.DataFrame): Anomaly alerts
    """
    logger.info("\n" + "=" * 80)
    logger.info("BƯỚC 5: SAVING ALERTS TO GOLD LAYER")
    logger.info("=" * 80)
    
    conn = get_trino_connector()
    cursor = conn.cursor()
    
    # Create table if not exists
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS "sme_pulse".gold.ml_anomaly_alerts (
        alert_id VARCHAR,
        txn_id VARCHAR,
        txn_date DATE,
        amount_vnd DOUBLE,
        direction VARCHAR,
        counterparty_name VARCHAR,
        transaction_category VARCHAR,
        anomaly_score DOUBLE,
        severity VARCHAR,
        model_name VARCHAR,
        model_version VARCHAR,
        detection_timestamp TIMESTAMP,
        created_at TIMESTAMP
    )
    WITH (
        format = 'PARQUET'
    )
    """
    
    start_create = time.time()
    try:
        cursor.execute(create_table_sql)
        logger.info("✅ Table ml_anomaly_alerts created/verified")
    except Exception as e:
        logger.warning(f"Table creation note: {e}")
    logger.info(f"[Timing] Table creation: {time.time() - start_create:.2f}s")
    
    # Insert alerts (only anomalies)
    anomaly_alerts = alerts_df[alerts_df['is_anomaly'] == 1].copy()
    # Giới hạn số lượng anomaly insert (top 1000 để tránh SQL quá lớn)
    if len(anomaly_alerts) > 1000:
        anomaly_alerts = anomaly_alerts.nsmallest(1000, 'anomaly_score')
        logger.info(f"⚠️ Quá nhiều anomaly, chỉ insert top 1000 (lowest scores)")
    
    if len(anomaly_alerts) > 0:
        # FIX: Chia nhỏ insert thành batch để tránh Iceberg metadata conflict
        # Batch size = 500 records mỗi lần để SQL statement nhỏ hơn (< 50KB)
        BATCH_SIZE = 500
        now = datetime.now()
        total_inserted = 0
        
        # Step 1: DROP bảng cũ để xóa metadata (tránh corruption)
        try:
            cursor.execute('DROP TABLE IF EXISTS "sme_pulse".gold.ml_anomaly_alerts')
            logger.info("✅ Dropped old ml_anomaly_alerts table (fresh start)")
        except Exception as e:
            logger.warning(f"Could not drop table: {e}")
        
        # Step 2: Tạo bảng mới
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS "sme_pulse".gold.ml_anomaly_alerts (
            alert_id VARCHAR,
            txn_id VARCHAR,
            txn_date DATE,
            amount_vnd DOUBLE,
            direction VARCHAR,
            counterparty_name VARCHAR,
            transaction_category VARCHAR,
            anomaly_score DOUBLE,
            severity VARCHAR,
            model_name VARCHAR,
            model_version VARCHAR,
            detection_timestamp TIMESTAMP,
            created_at TIMESTAMP
        )
        WITH (format = 'PARQUET')
        """
        try:
            cursor.execute(create_table_sql)
            logger.info("✅ Created fresh ml_anomaly_alerts table")
        except Exception as e:
            logger.warning(f"Table creation note: {e}")
        
        # Step 3: Insert dữ liệu theo batch
        start_insert = time.time()
        num_batches = (len(anomaly_alerts) + BATCH_SIZE - 1) // BATCH_SIZE
        for batch_idx, batch_start in enumerate(range(0, len(anomaly_alerts), BATCH_SIZE)):
            batch_end = min(batch_start + BATCH_SIZE, len(anomaly_alerts))
            batch_data = anomaly_alerts.iloc[batch_start:batch_end]
            
            insert_sql = """
            INSERT INTO \"sme_pulse\".gold.ml_anomaly_alerts 
            (alert_id, txn_id, txn_date, amount_vnd, direction, counterparty_name, 
             transaction_category, anomaly_score, severity, model_name, model_version, 
             detection_timestamp, created_at)
            VALUES 
            """
            
            rows = []
            for _, row in batch_data.iterrows():
                alert_id = f"{row['txn_id']}_ANOMALY_{now.strftime('%Y%m%d%H%M%S')}"
                # Escape single quotes trong string để tránh SQL injection
                counterparty = str(row['counterparty_name']).replace("'", "''")
                category = str(row['transaction_category']).replace("'", "''")
                rows.append(f"('{alert_id}', '{row['txn_id']}', DATE '{row['txn_date'].date()}', {float(row['amount_vnd'])}, '{row['direction_in_out']}', "
                            f"'{counterparty}', '{category}', {float(row['anomaly_score'])}, "
                            f"'{row['severity']}', '{MODEL_NAME}', '{MODEL_VERSION}', TIMESTAMP '{row['detection_timestamp']}', TIMESTAMP '{now}')")
            
            # Insert batch này (1 transaction = 1 Iceberg commit)
            batch_sql = insert_sql + ",\n            ".join(rows)
            try:
                cursor.execute(batch_sql)
                total_inserted += len(batch_data)
                batch_num = batch_idx + 1
                logger.info(f"✅ Batch {batch_num}/{num_batches}: Inserted {len(batch_data):,} alerts | Total: {total_inserted:,}/{len(anomaly_alerts):,}")
            except Exception as e:
                logger.error(f"❌ Failed to insert batch {batch_idx + 1}: {e}")
                logger.error(f"Batch SQL size: {len(batch_sql):,} characters")
                raise
        
        logger.info(f"✅ All {total_inserted:,} anomaly alerts saved to ml_anomaly_alerts")
        logger.info(f"[Timing] Insert: {time.time() - start_insert:.2f}s (batch insert)")
    else:
        logger.info("ℹ️  No anomalies detected in this period")
    
    # Save detection statistics
    logger.info("\nSaving detection statistics...")
    stats_table_sql = """
    CREATE TABLE IF NOT EXISTS "sme_pulse".gold.ml_anomaly_statistics (
        statistic_date DATE,
        total_transactions BIGINT,
        anomalies_detected BIGINT,
        anomaly_ratio DOUBLE,
        critical_count BIGINT,
        high_count BIGINT,
        medium_count BIGINT,
        low_count BIGINT,
        avg_anomaly_score DOUBLE,
        min_anomaly_score DOUBLE,
        max_anomaly_score DOUBLE,
        model_name VARCHAR,
        model_version VARCHAR,
        created_at TIMESTAMP
    )
    WITH (
        format = 'PARQUET'
    )
    """
    
    try:
        cursor.execute(stats_table_sql)
        logger.info("✅ Table ml_anomaly_statistics created/verified")
    except Exception as e:
        logger.warning(f"Table creation note: {e}")
    
    # Insert statistics
    stats_insert_sql = """
    INSERT INTO "sme_pulse".gold.ml_anomaly_statistics
    (statistic_date, total_transactions, anomalies_detected, anomaly_ratio, 
     critical_count, high_count, medium_count, low_count,
     avg_anomaly_score, min_anomaly_score, max_anomaly_score, 
     model_name, model_version, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    try:
        cursor.execute(stats_insert_sql, (
            datetime.now().date(),
            len(alerts_df),
            len(anomaly_alerts),
            float(len(anomaly_alerts) / len(alerts_df)) if len(alerts_df) > 0 else 0.0,
            int((alerts_df['severity'] == 'CRITICAL').sum()),
            int((alerts_df['severity'] == 'HIGH').sum()),
            int((alerts_df['severity'] == 'MEDIUM').sum()),
            int((alerts_df['severity'] == 'LOW').sum()),
            float(alerts_df['anomaly_score'].mean()),
            float(alerts_df['anomaly_score'].min()),
            float(alerts_df['anomaly_score'].max()),
            MODEL_NAME,
            MODEL_VERSION,
            datetime.now()
        ))
        logger.info(f"✅ Saved detection statistics to ml_anomaly_statistics")
    except Exception as e:
        logger.error(f"Failed to insert statistics: {e}")
    
    conn.close()


def main():
    """
    Main function: Chạy toàn bộ quy trình detection hàng ngày.
    """
    logger.info("\n" + "=" * 80)
    logger.info("UC10 - DAILY ANOMALY DETECTION")
    logger.info(f"Start Time: {datetime.now()}")
    logger.info(f"Detection Window: Last {DETECTION_DAYS} days")
    logger.info(f"Model: {MODEL_NAME} (v{MODEL_VERSION})")
    logger.info("=" * 80)
    
    try:
        # 1. Load model
        model, scaler, feature_names = load_model_and_scaler()
        
        # 2. Load new transactions
        df_new = load_new_transactions(days=DETECTION_DAYS)
        
        # 3. Feature engineering
        df_features, df_with_features = engineer_features_for_detection(df_new)
        
        # 4. Detect anomalies
        alerts_df = detect_anomalies(model, scaler, df_features, df_with_features)
        
        # 5. Save to Gold layer
        save_alerts_to_trino(alerts_df)
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ DETECTION COMPLETED SUCCESSFULLY!")
        logger.info(f"End Time: {datetime.now()}")
        logger.info("=" * 80)
        
        return True
        
    except Exception as e:
        logger.error(f"\n❌ DETECTION FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

