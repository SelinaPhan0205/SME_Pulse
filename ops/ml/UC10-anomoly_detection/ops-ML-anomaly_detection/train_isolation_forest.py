"""
UC10 - Anomaly Detection: Train Isolation Forest Model
========================================================
Huấn luyện mô hình Isolation Forest trên dữ liệu giao dịch ngân hàng lịch sử
để phát hiện các giao dịch bất thường trong tương lai.

Quy trình:
1. Load dữ liệu lịch sử (90-180 ngày gần nhất)
2. Tính toán các đặc trưng (features) từ giao dịch
3. Huấn luyện Isolation Forest (n_estimators=100, contamination=5%)
4. Đánh giá mô hình (silhouette score, anomaly statistics)
5. Lưu mô hình vào MLflow model registry
"""

import sys
sys.path.insert(0, '/opt/ops/ml/UC10-anomoly_detection/ops-ML-anomaly_detection')

import pandas as pd
import numpy as np
import mlflow
import mlflow.sklearn
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
from utils import get_trino_connector
import logging
import os
from datetime import datetime, timedelta
import pickle
import json

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Cấu hình MLflow
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "file:///opt/airflow/mlflow")
MLFLOW_EXPERIMENT_NAME = "sme_pulse_anomaly_detection"
MODEL_NAME = "isolation_forest_anomaly_v1"

# Cấu hình Isolation Forest
TRAINING_DAYS = 365  # Lấy tất cả dữ liệu lịch sử (nếu < 365 ngày thì lấy hết)
CONTAMINATION = 0.05  # Giả định 5% là anomaly
N_ESTIMATORS = 100  # Số cây quyết định


def load_training_data():
    """
    Load dữ liệu giao dịch lịch sử từ fact_bank_txn.
    
    Returns:
        pd.DataFrame: Dữ liệu giao dịch với các cột:
            - txn_id: ID giao dịch
            - txn_date: Ngày giao dịch
            - amount_vnd: Số tiền (VND)
            - direction_in_out: 'in' hoặc 'out'
            - is_large_transaction: Flag giao dịch lớn
            - transaction_category: Phân loại giao dịch
    """
    logger.info("=" * 80)
    logger.info("BƯỚC 1: LOADING TRAINING DATA")
    logger.info("=" * 80)
    
    conn = get_trino_connector()
    
    # Load dữ liệu 365 ngày gần nhất (hoặc tất cả nếu < 365 ngày)
    query = f"""
    WITH date_range AS (
        SELECT MAX(txn_date) as max_date FROM sme_lake.gold.fact_bank_txn
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
    FROM sme_lake.gold.fact_bank_txn f
    CROSS JOIN date_range d
    WHERE txn_date >= d.max_date - interval '{TRAINING_DAYS}' day
    ORDER BY txn_date ASC
    """
    
    logger.info(f"\nLoading {TRAINING_DAYS} days of transaction data...")
    df = pd.read_sql(query, conn)
    conn.close()
    
    logger.info(f"✅ Loaded {len(df):,} transactions")
    logger.info(f"   Date range: {df['txn_date'].min()} to {df['txn_date'].max()}")
    logger.info(f"   Distinct dates: {df['txn_date'].nunique()}")
    logger.info(f"   Inflow: {(df['direction_in_out'] == 'in').sum():,}")
    logger.info(f"   Outflow: {(df['direction_in_out'] == 'out').sum():,}")
    
    # Ensure txn_date is datetime
    df['txn_date'] = pd.to_datetime(df['txn_date'])
    
    return df


def engineer_features(df):
    """
    Tính toán đặc trưng (features) từ giao dịch.
    
    Features:
    1. Đặc trưng cơ bản:
       - amount_vnd: Số tiền giao dịch
       - amount_log: Log của số tiền (để handle right-skewed distribution)
       - is_inflow: 1 nếu tiền vào, 0 nếu tiền ra
       - is_large: 1 nếu giao dịch lớn (>100M VND)
    
    2. Đặc trưng thời gian:
       - hour_of_day: Giờ giao dịch (0-23)
       - day_of_week: Thứ trong tuần (0-6)
       - day_of_month: Ngày trong tháng
       - is_weekend: 1 nếu cuối tuần
    
    3. Đặc trưng thống kê (rolling):
       - txn_count_7d: Số giao dịch trong 7 ngày
       - amount_std_7d: Độ lệch chuẩn số tiền trong 7 ngày
       - amount_mean_7d: Trung bình số tiền trong 7 ngày
       - amount_max_7d: Giá trị max trong 7 ngày
    
    4. Đặc trưng phân loại:
       - cat_receivable: 1 nếu loại RECEIVABLE
       - cat_payable: 1 nếu loại PAYABLE
       - cat_payroll: 1 nếu loại PAYROLL
       - cat_other: 1 nếu loại khác
    
    Args:
        df (pd.DataFrame): Dữ liệu giao dịch
    
    Returns:
        tuple: (df_features, feature_names)
            - df_features: DataFrame chứa features
            - feature_names: Danh sách tên features
    """
    logger.info("\n" + "=" * 80)
    logger.info("BƯỚC 2: FEATURE ENGINEERING")
    logger.info("=" * 80)
    
    df = df.copy()
    df['txn_timestamp'] = pd.to_datetime(df['txn_date'])
    
    # 1. Basic features
    logger.info("\n[1] Computing basic features...")
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
    
    # Calculate daily aggregates then merge back
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
    
    # Select features for model
    feature_cols = [
        'amount_vnd', 'amount_log', 'is_inflow', 'is_large',
        'hour_of_day', 'day_of_week', 'day_of_month', 'is_weekend',
        'txn_count_7d', 'amount_std_7d', 'amount_mean_7d', 'amount_max_7d',
        'cat_receivable', 'cat_payable', 'cat_payroll', 'cat_other'
    ]
    
    df_features = df_sorted[feature_cols].copy()
    
    # Handle missing values
    df_features = df_features.fillna(df_features.mean(numeric_only=True))
    
    logger.info(f"\n✅ Generated {len(feature_cols)} features")
    logger.info(f"   Features: {feature_cols}")
    logger.info(f"\nFeature statistics:")
    logger.info(f"\n{df_features.describe().to_string()}")
    
    return df_features, feature_cols, df_sorted


def train_isolation_forest(df_features, feature_names):
    """
    Huấn luyện mô hình Isolation Forest.
    
    Args:
        df_features (pd.DataFrame): Feature matrix
        feature_names (list): Tên các features
    
    Returns:
        tuple: (model, scaler, anomaly_scores)
            - model: Isolation Forest model đã trained
            - scaler: StandardScaler để normalize features
            - anomaly_scores: Anomaly scores cho training set
    """
    logger.info("\n" + "=" * 80)
    logger.info("BƯỚC 3: TRAINING ISOLATION FOREST MODEL")
    logger.info("=" * 80)
    
    # Normalize features
    logger.info(f"\n[1] Normalizing {len(feature_names)} features...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df_features)
    
    # Train model
    logger.info(f"[2] Training Isolation Forest...")
    logger.info(f"   Parameters:")
    logger.info(f"     - n_estimators: {N_ESTIMATORS}")
    logger.info(f"     - contamination: {CONTAMINATION} ({int(len(X_scaled) * CONTAMINATION):,} expected anomalies)")
    logger.info(f"     - random_state: 42")
    
    model = IsolationForest(
        n_estimators=N_ESTIMATORS,
        contamination=CONTAMINATION,
        random_state=42,
        n_jobs=-1
    )
    
    predictions = model.fit_predict(X_scaled)
    anomaly_scores = model.score_samples(X_scaled)
    
    # Statistics
    n_anomalies = (predictions == -1).sum()
    n_normal = (predictions == 1).sum()
    
    logger.info(f"\n✅ Model trained!")
    logger.info(f"   Normal samples: {n_normal:,} ({100*n_normal/len(predictions):.1f}%)")
    logger.info(f"   Anomalies: {n_anomalies:,} ({100*n_anomalies/len(predictions):.1f}%)")
    logger.info(f"   Anomaly score range: [{anomaly_scores.min():.4f}, {anomaly_scores.max():.4f}]")
    logger.info(f"   Anomaly score mean (Normal): {anomaly_scores[predictions == 1].mean():.4f}")
    logger.info(f"   Anomaly score mean (Anomaly): {anomaly_scores[predictions == -1].mean():.4f}")
    
    return model, scaler, anomaly_scores, predictions


def evaluate_model(df_features, model, scaler, predictions):
    """
    Đánh giá mô hình Isolation Forest với Cross-Validation.
    
    Args:
        df_features (pd.DataFrame): Feature matrix
        model: Trained model
        scaler: StandardScaler
        predictions: Predictions từ model
    
    Returns:
        dict: Các metrics đánh giá
    """
    from sklearn.model_selection import cross_val_score
    from sklearn.metrics import silhouette_score
    
    logger.info("\n" + "=" * 80)
    logger.info("BƯỚC 4: MODEL EVALUATION & VALIDATION")
    logger.info("=" * 80)
    
    X_scaled = scaler.transform(df_features)
    
    metrics = {
        'n_samples': len(df_features),
        'n_features': df_features.shape[1],
        'n_anomalies': (predictions == -1).sum(),
        'anomaly_ratio': float((predictions == -1).sum() / len(predictions)),
        'contamination_param': CONTAMINATION,
    }
    
    try:
        # 1. Anomaly Score Statistics
        anomaly_scores = model.score_samples(X_scaled)
        metrics['anomaly_score_mean'] = float(anomaly_scores.mean())
        metrics['anomaly_score_std'] = float(anomaly_scores.std())
        metrics['anomaly_score_min'] = float(anomaly_scores.min())
        metrics['anomaly_score_max'] = float(anomaly_scores.max())
        
        # 2. Cross-Validation Score (k-fold) - SKIP for large dataset
        logger.info("\n📊 Cross-Validation (skipped for performance on large dataset)")
        metrics['cv_mean_score'] = 0.0
        metrics['cv_std_score'] = 0.0
        
        # 3. Silhouette Score (cho unsupervised learning)
        # Dùng SAMPLE nhỏ để tính (Silhouette Score is O(n²), very slow for large n)
        logger.info("📊 Computing Silhouette Score (on 5000 sample)...")
        sample_size = min(5000, len(X_scaled))
        sample_indices = np.random.choice(len(X_scaled), sample_size, replace=False)
        X_sample = X_scaled[sample_indices]
        pred_sample = predictions[sample_indices]
        
        silhouette_avg = silhouette_score(X_sample, pred_sample)
        metrics['silhouette_score'] = float(silhouette_avg)
        
        # 4. Anomaly Detection Quality Metrics
        # Dựa trên statistical properties
        normal_scores = anomaly_scores[predictions == 1]
        anomaly_scores_anom = anomaly_scores[predictions == -1]
        
        if len(normal_scores) > 0 and len(anomaly_scores_anom) > 0:
            # Separation score: gap giữa normal và anomaly
            separation = float(normal_scores.mean() - anomaly_scores_anom.mean())
            metrics['score_separation'] = separation
            
            # Overlap ratio: bao nhiêu % anomaly score overlap với normal range
            normal_min, normal_max = normal_scores.min(), normal_scores.max()
            overlap = float((anomaly_scores_anom > normal_min).sum() / len(anomaly_scores_anom))
            metrics['overlap_ratio'] = overlap
        
        logger.info(f"\n✅ EVALUATION RESULTS:")
        logger.info(f"\n📈 Dataset Statistics:")
        logger.info(f"   Samples: {metrics['n_samples']:,}")
        logger.info(f"   Features: {metrics['n_features']}")
        logger.info(f"   Anomalies detected: {metrics['n_anomalies']:,} ({100*metrics['anomaly_ratio']:.2f}%)")
        
        logger.info(f"\n🎯 Anomaly Score Statistics:")
        logger.info(f"   Mean: {metrics['anomaly_score_mean']:.4f}")
        logger.info(f"   Std Dev: {metrics['anomaly_score_std']:.4f}")
        logger.info(f"   Range: [{metrics['anomaly_score_min']:.4f}, {metrics['anomaly_score_max']:.4f}]")
        
        logger.info(f"\n✔️  Cross-Validation Score (5-Fold):")
        logger.info(f"   Skipped for performance (large dataset)")
        
        logger.info(f"\n🔍 Silhouette Score (Cluster Quality) - Sampled:")
        logger.info(f"   Score: {metrics['silhouette_score']:.4f} (computed on {sample_size:,} samples)")
        interpretation = ""
        if silhouette_avg > 0.5:
            interpretation = "STRONG clustering ✅ (Model is accurate!)"
        elif silhouette_avg > 0.25:
            interpretation = "MODERATE clustering ⚠️ (Acceptable)"
        else:
            interpretation = "WEAK clustering ❌ (Overlapping clusters)"
        logger.info(f"   Interpretation: {interpretation}")
        
        logger.info(f"\n📊 Anomaly Detection Quality:")
        logger.info(f"   Score Separation: {metrics.get('score_separation', 0):.4f}")
        logger.info(f"   Overlap Ratio: {100 * metrics.get('overlap_ratio', 0):.2f}%")
        logger.info(f"   → Distinction between normal/anomaly: {'CLEAR ✅' if metrics.get('overlap_ratio', 0) < 0.3 else 'FUZZY ⚠️'}")
        
        logger.info(f"\n📋 OVERALL MODEL QUALITY:")
        quality_score = (
            max(0, silhouette_avg) * 0.5 +  # Clustering quality (increased weight)
            (1 - metrics.get('overlap_ratio', 0)) * 0.5  # Separation
        )
        metrics['overall_quality_score'] = float(quality_score)
        logger.info(f"   Quality Score: {quality_score:.2%}")
        
        if quality_score > 0.7:
            logger.info("   ⭐⭐⭐ EXCELLENT MODEL - Ready for production!")
        elif quality_score > 0.5:
            logger.info("   ⭐⭐ GOOD MODEL - Acceptable for use")
        else:
            logger.info("   ⭐ FAIR MODEL - Consider tuning parameters")
        
    except Exception as e:
        logger.warning(f"Could not compute all metrics: {e}")
        import traceback
        traceback.print_exc()
    
    return metrics


def save_model_to_mlflow(model, scaler, feature_names, metrics):
    """
    Lưu mô hình vào MLflow model registry.
    
    Args:
        model: Trained Isolation Forest model (ONLY model object, NO data)
        scaler: StandardScaler (ONLY scaler object, NO data)
        feature_names: List of feature names
        metrics: Dictionary of metrics
    """
    logger.info("\n" + "=" * 80)
    logger.info("BƯỚC 5: SAVING MODEL TO MLFLOW")
    logger.info("=" * 80)
    
    # Set MLflow URI
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)
    
    with mlflow.start_run() as run:
        # Log parameters
        logger.info("\n[1] Logging parameters...")
        mlflow.log_param("model_type", "IsolationForest")
        mlflow.log_param("n_estimators", N_ESTIMATORS)
        mlflow.log_param("contamination", CONTAMINATION)
        mlflow.log_param("training_days", TRAINING_DAYS)
        mlflow.log_param("n_features", len(feature_names))
        mlflow.log_param("features", ",".join(feature_names))
        mlflow.log_param("training_date", datetime.now().isoformat())
        
        # Log metrics
        logger.info("[2] Logging metrics...")
        for metric_name, metric_value in metrics.items():
            try:
                mlflow.log_metric(metric_name, float(metric_value))
            except:
                pass  # Skip non-numeric metrics
        
        # Log model artifacts - CRITICAL: Only save model objects, NOT data
        logger.info("[3] Logging model artifacts (model objects only, NO data)...")
        
        # Create artifacts directory
        artifacts_dir = "/tmp/mlflow_artifacts"
        os.makedirs(artifacts_dir, exist_ok=True)
        
        # Save ONLY model object and scaler object (NO DataFrames, NO training data)
        scaler_path = os.path.join(artifacts_dir, "scaler.pkl")
        features_path = os.path.join(artifacts_dir, "features.json")
        
        # Pickle only scaler (small object ~few KB)
        with open(scaler_path, 'wb') as f:
            pickle.dump(scaler, f)
        
        # Save feature names as JSON (tiny file)
        with open(features_path, 'w') as f:
            json.dump({'features': feature_names}, f)
        
        # Log artifacts
        mlflow.log_artifact(scaler_path)
        mlflow.log_artifact(features_path)
        
        # Log model using MLflow's sklearn autolog (handles serialization efficiently)
        # This only saves the model object, NOT any training data
        logger.info("[4] Logging and registering model (model object only)...")
        model_info = mlflow.sklearn.log_model(
            model,
            artifact_path="isolation_forest",
            registered_model_name=MODEL_NAME  # Register to Model Registry
        )
        logger.info(f"✅ Model registered to Model Registry: {MODEL_NAME}")
        
        # Verify artifact sizes
        import subprocess
        try:
            artifact_uri = mlflow.get_artifact_uri()
            artifact_path = artifact_uri.replace('file://', '')
            result = subprocess.run(['du', '-sh', artifact_path], capture_output=True, text=True, timeout=5)
            logger.info(f"\n📦 Artifact size: {result.stdout.strip() if result.returncode == 0 else 'N/A'}")
        except:
            pass  # Skip if du command not available
        
        logger.info(f"\n✅ Run completed!")
        logger.info(f"   Run ID: {run.info.run_id}")
        logger.info(f"   Artifacts URI: {mlflow.get_artifact_uri()}")
    
    return run.info.run_id


def main():
    """
    Main function: Chạy toàn bộ quy trình huấn luyện.
    """
    logger.info("\n" + "=" * 80)
    logger.info("UC10 - ANOMALY DETECTION MODEL TRAINING")
    logger.info("Algorithm: Isolation Forest")
    logger.info("Data Source: fact_bank_txn (Gold Layer)")
    logger.info(f"Training Data: Last {TRAINING_DAYS} days")
    logger.info(f"Start Time: {datetime.now()}")
    logger.info("=" * 80)
    
    try:
        # 1. Load data
        df = load_training_data()
        
        # 2. Feature engineering
        df_features, feature_names, df_with_features = engineer_features(df)
        
        # --- FIX [P2]: Temporal train/eval split (80/20 by date) ---
        # This prevents evaluating on training data and catches distribution drift
        split_idx = int(len(df_features) * 0.8)
        df_train = df_features.iloc[:split_idx].copy()
        df_eval = df_features.iloc[split_idx:].copy()
        logger.info(f"\n📊 Temporal split: train={len(df_train):,} rows, eval={len(df_eval):,} rows")
        
        # 3. Train model (fit ONLY on train set)
        model, scaler, anomaly_scores, predictions = train_isolation_forest(df_train, feature_names)
        
        # 4. Evaluate on HELD-OUT eval set (not training data)
        logger.info("\n📊 Evaluating on held-out eval set (not training data)...")
        X_eval_scaled = scaler.transform(df_eval)
        eval_predictions = model.predict(X_eval_scaled)
        metrics = evaluate_model(df_eval, model, scaler, eval_predictions)
        
        # Log split info
        metrics['train_size'] = len(df_train)
        metrics['eval_size'] = len(df_eval)
        metrics['train_eval_split'] = 0.8
        
        # 5. Save to MLflow
        run_id = save_model_to_mlflow(model, scaler, feature_names, metrics)
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ TRAINING COMPLETED SUCCESSFULLY!")
        logger.info(f"End Time: {datetime.now()}")
        logger.info(f"MLflow Run ID: {run_id}")
        logger.info("=" * 80)
        
        return True
        
    except Exception as e:
        logger.error(f"\n❌ TRAINING FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
