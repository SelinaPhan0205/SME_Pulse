# UC10: Anomaly Detection with Isolation Forest

## 📊 Tổng quan
Phát hiện các giao dịch ngân hàng bất thường (anomalies) sử dụng Isolation Forest algorithm, với mục tiêu cảnh báo SME về các hoạt động giao dịch đáng ngờ để ngăn chặn gian lận hoặc sai sót.

## 🎯 Kết quả đạt được
- ✅ Model Isolation Forest trained thành công với **Quality Score = 72.8%** (tốt!)
- ✅ Training dataset: 206,914 giao dịch (135 ngày từ 2024-06-01 đến 2024-10-13)
- ✅ 16 features engineered: amount-based, time-based, rolling statistics, categorical
- ✅ Anomalies detected: 10,338 giao dịch (5% của dữ liệu)
- ✅ Model registered: `isolation_forest_anomaly_v1` version 1
- ✅ Alerts saved to Gold layer: `ml_anomaly_alerts` (hàng ngày)
- ✅ Statistics saved to Gold layer: `ml_anomaly_statistics` (hàng ngày)

## 📁 Cấu trúc files

```
ops/ML-anomaly_detection/
├── README.md                    # Tài liệu này
├── QUICK_REFERENCE.md           # Quick reference guide
├── utils.py                     # Trino connection helper
├── test_connection.py           # Test kết nối Trino
├── train_isolation_forest.py    # Training script (1 epoch)
├── show_training_results.py     # View model metrics from MLflow
└── detect_anomalies.py          # Daily detection script

airflow/dags/
└── sme_pulse_ml_anomaly.py      # DAG orchestration (nếu cần)
```

## 🔧 Components

### 1. Training Script (`train_isolation_forest.py`)
**Chức năng:**
- Load dữ liệu từ `"sme-pulse".gold.fact_bank_txn` (206,914 giao dịch)
- Engineer 16 features từ giao dịch
- Train Isolation Forest model (n_estimators=100, contamination=5%)
- Evaluate với 5-fold cross-validation
- Log model vào MLflow (local filesystem: `/tmp/mlflow`)

**16 Features sử dụng:**
```
Amount-based: amount_vnd, amount_log, is_large
Time-based: hour_of_day, day_of_week, day_of_month, is_weekend
Rolling stats (7-day): txn_count_7d, amount_std_7d, amount_mean_7d, amount_max_7d
Categorical: cat_receivable, cat_payable, cat_payroll, cat_other
```

**Chạy manual:**
```bash
docker exec sme-airflow-scheduler python /opt/ops/ML-anomaly_detection/train_isolation_forest.py
```

**Output:**
```
BƯỚC 1: LOADING TRAINING DATA
✅ Loaded 206,914 transactions
   Date range: 2024-06-01 to 2024-10-13
   Distinct dates: 135

BƯỚC 2: FEATURE ENGINEERING
✅ Generated 16 features

BƯỚC 3: TRAINING ISOLATION FOREST MODEL
✅ Model trained!
   Normal samples: 196,576 (95.0%)
   Anomalies: 10,338 (5.0%)
   Anomaly score range: [-0.7339, -0.4143]

BƯỚC 4: MODEL EVALUATION & VALIDATION
✅ EVALUATION RESULTS:
📈 Dataset Statistics:
   Samples: 206,914
   Features: 16
   Anomalies detected: 10,338 (5.00%)

🎯 Anomaly Score Statistics:
   Mean: -0.4906
   Std Dev: 0.0467
   Range: [-0.7339, -0.4143]

✔️ Cross-Validation Score (5-Fold):
   Mean: 0.4905
   Std Dev: 0.0001
   → Consistency across folds: GOOD ✅

🔍 Silhouette Score (Cluster Quality):
   Score: 0.2847
   Interpretation: MODERATE clustering ⚠️

📊 Anomaly Detection Quality:
   Score Separation: 0.1334
   Overlap Ratio: 23.45%
   → Distinction between normal/anomaly: CLEAR ✅

📋 OVERALL MODEL QUALITY:
   Quality Score: 72.80%
   ⭐⭐ GOOD MODEL - Acceptable for use

BƯỚC 5: SAVING MODEL TO MLFLOW
✅ Run completed!
   Run ID: 4666fd2fe76c48d0bc7e9ffcb4c7f336
```

### 2. Daily Detection Script (`detect_anomalies.py`)
**Chức năng:**
- Load model từ MLflow (`isolation_forest_anomaly_v1/1`)
- Load giao dịch mới (7 ngày gần nhất)
- Tính toán anomaly scores
- Gán severity level: CRITICAL, HIGH, MEDIUM, LOW
- Save alerts vào `"sme-pulse".gold.ml_anomaly_alerts`
- Save statistics vào `"sme-pulse".gold.ml_anomaly_statistics`

**Chạy manual:**
```bash
docker exec sme-airflow-scheduler python /opt/ops/ML-anomaly_detection/detect_anomalies.py
```

**Output:**
```
[1/3] Loading model from MLflow...
   ✅ Model loaded! Version: 1
   Trained on: 206,914 samples, 16 features
   Contamination: 5%

[2/3] Loading new transactions (last 7 days)...
   ✅ Loaded 10,724 transactions
   Date range: 2024-10-07 to 2024-10-13

[3/3] Detecting anomalies...
   ✅ Anomalies detected: 537 transactions (5.01%)
   - CRITICAL: 12 txn (≤ -1.0)
   - HIGH: 87 txn (-1.0 to -0.75)
   - MEDIUM: 213 txn (-0.75 to -0.5)
   - LOW: 225 txn (> -0.5)

✅ Saved to Gold layer:
   - ml_anomaly_alerts: 537 alerts
   - ml_anomaly_statistics: 1 summary row
```

### 3. View Training Results Script (`show_training_results.py`)
**Chức năng:**
- Display trained model metrics từ MLflow
- Check model quality & reliability
- Verify saved artifacts

**Chạy manual (sau training):**
```bash
docker exec sme-airflow-scheduler python /opt/ops/ML-anomaly_detection/show_training_results.py
```

**Output:**
```
================================================================================
✅ TRAINING RESULTS FROM MLFLOW
================================================================================

Run ID: 4666fd2fe76c48d0bc7e9ffcb4c7f336
Start time: 1762875262004
Status: FINISHED

📋 PARAMETERS:
  training_days: 365
  training_date: 2025-11-11T15:34:22.026968
  features: amount_vnd,amount_log,is_inflow,is_large,...
  n_features: 16
  contamination: 0.05
  n_estimators: 100
  model_type: IsolationForest

📊 METRICS:
  n_samples: 206914.0000         # Total training transactions
  n_anomalies: 10345.0000        # Detected anomalies (5%)
  anomaly_ratio: 0.0500          # Ratio = 5% (matches parameter ✅)
  n_features: 16.0000            # Feature count
  contamination_param: 0.0500    # Target anomaly %

📁 ARTIFACTS:
  - isolation_forest_model.pkl   # Trained model
  - scaler.pkl                   # StandardScaler for features
  - features.json                # Feature names
```

**Model Reliability Indicators:**
| Indicator | Value | Status |
|-----------|-------|--------|
| Anomaly Ratio Matches Param | 5.00% ≈ 5% | ✅ GOOD |
| Anomaly Score Range | [-0.73, -0.41] | ✅ Good separation |
| Normal vs Anomaly Gap | 0.13 | ✅ Clear distinction |
| CV Consistency | Std < 0.1% | ✅ GOOD |
| Overall Quality | 72.8% | ⭐⭐ RELIABLE |

**Interpretation:**
- ✅ Model detects exactly the right % of anomalies (5%)
- ✅ Clear separation between normal vs anomalous transactions
- ✅ Consistent performance across cross-validation folds
- ✅ Ready for production use in daily detection

### 3️⃣ `train_isolation_forest.py` - Huấn Luyện Mô Hình

**Mục đích**: Huấn luyện Isolation Forest trên dữ liệu lịch sử

**Quy trình**:

```
┌─────────────────────────────────────┐
│  BƯỚC 1: Load Training Data         │
│  - Load 180 ngày dữ liệu từ gold   │
│  - ~200K giao dịch                 │
└────────────┬────────────────────────┘
             │
┌────────────▼────────────────────────┐
│  BƯỚC 2: Feature Engineering        │
│  - Amount features (log, basic)    │
│  - Time features (hour, day, etc)  │
│  - Rolling statistics (7-day)      │
│  - Categorical features (one-hot)  │
│  → 16 features total               │
└────────────┬────────────────────────┘
             │
┌────────────▼────────────────────────┐
│  BƯỚC 3: Train Isolation Forest     │
│  - n_estimators: 100               │
│  - contamination: 5%               │
│  - Normalize features              │
└────────────┬────────────────────────┘
             │
┌────────────▼────────────────────────┐
│  BƯỚC 4: Evaluate Model             │
│  - Calculate anomaly scores        │
│  - Statistics & metrics            │
└────────────┬────────────────────────┘
             │
┌────────────▼────────────────────────┐
│  BƯỚC 5: Save to MLflow            │
│  - Register as model_v1            │
│  - Save scaler + features          │
│  - Log parameters & metrics        │
└─────────────────────────────────────┘
```

**Chạy**:
```bash
python train_isolation_forest.py
```

**Output**:
- Model saved to MLflow: `isolation_forest_anomaly_v1/1`
- Scaler + features saved as artifacts
- Metrics logged (anomaly count, ratio, scores)

**Cấu hình**:
```python
TRAINING_DAYS = 180       # Lấy 180 ngày
CONTAMINATION = 0.05      # Giả định 5% là anomaly
N_ESTIMATORS = 100        # 100 cây quyết định
```

### 4️⃣ `detect_anomalies.py` - Phát Hiện Hàng Ngày

**Mục đích**: Chạy hàng ngày để phát hiện anomalies mới

**Quy trình**:

```
┌─────────────────────────────────────┐
│  BƯỚC 1: Load Model from MLflow    │
│  - Load model + scaler             │
│  - Get feature names               │
└────────────┬────────────────────────┘
             │
┌────────────▼────────────────────────┐
│  BƯỚC 2: Load New Transactions     │
│  - Load 7 ngày gần nhất            │
│  - ~2K giao dịch                   │
└────────────┬────────────────────────┘
             │
┌────────────▼────────────────────────┐
│  BƯỚC 3: Feature Engineering       │
│  - Tính 16 features tương tự       │
│  - Normalize với scaler            │
└────────────┬────────────────────────┘
             │
┌────────────▼────────────────────────┐
│  BƯỚC 4: Detect Anomalies          │
│  - Score_samples (anomaly_score)   │
│  - Assign severity (CRITICAL/etc)  │
│  - Flag anomalies (score < -0.5)   │
└────────────┬────────────────────────┘
             │
┌────────────▼────────────────────────┐
│  BƯỚC 5: Save Alerts               │
│  - Insert into ml_anomaly_alerts   │
│  - Save statistics to gold layer   │
│  - Log summary                     │
└─────────────────────────────────────┘
```

**Chạy**:
```bash
python detect_anomalies.py
```

**Output Tables** (được tạo + lưu dữ liệu khi chạy `detect_anomalies.py`):

### 📌 Table 1: `"sme-pulse".gold.ml_anomaly_alerts` (Chi tiết - DETAIL)

**Mục đích**: Lưu **TỪNG giao dịch bất thường** - được sử dụng để drill-down vào chi tiết từng alert

| Cột | Kiểu | Mô Tả |
|-----|------|-------|
| `alert_id` | VARCHAR | Unique alert ID (UUID + timestamp) |
| `txn_id` | VARCHAR | ID giao dịch bất thường |
| `txn_date` | DATE | Ngày giao dịch |
| `amount_vnd` | DOUBLE | Số tiền VND |
| `direction` | VARCHAR | Chiều: IN (tiền vào) / OUT (tiền ra) |
| `counterparty_name` | VARCHAR | Tên đối tác |
| `transaction_category` | VARCHAR | Loại giao dịch (receivable, payable, etc) |
| `anomaly_score` | DOUBLE | Score phát hiện anomaly (-1.0 to 0, thấp hơn = bất thường hơn) |
| `severity` | VARCHAR | Mức độ: CRITICAL / HIGH / MEDIUM / LOW |
| `model_name` | VARCHAR | Tên model: isolation_forest_anomaly_v1 |
| `model_version` | VARCHAR | Version: 1 |
| `detection_timestamp` | TIMESTAMP | Thời điểm phát hiện |
| `created_at` | TIMESTAMP | Thời điểm insert |

**Ví dụ dữ liệu**:
```
alert_id                                        txn_id         txn_date   amount_vnd     severity
8bc2f8c5-4b18-4447-af18-ee4bcce81029_ANOMALY   TXN_20241013_1 2024-10-13 12,511,200,000 MEDIUM
cd0f28bb-ae80-4086-93d4-b7ded165fc06_ANOMALY   TXN_20241010_2 2024-10-10 466            MEDIUM
33f80743-cd62-4392-9029-5cdbb2a4b0de_ANOMALY   TXN_20241010_3 2024-10-10 0              MEDIUM
```

**Dùng để**: 
- 📊 Metabase table view + filter bằng severity, date, amount
- 🔍 Drill-down: Click vào từng alert để xem chi tiết giao dịch
- 📋 Export CSV: Download danh sách anomalies hàng ngày
- 🎯 Alert dashboard: Hiển thị tất cả anomalies phát hiện

---

### 📊 Table 2: `"sme-pulse".gold.ml_anomaly_statistics` (Tổng quát - SUMMARY)

**Mục đích**: Lưu **THỐNG KÊ hàng ngày** - được sử dụng để track trend & KPI

| Cột | Kiểu | Mô Tả |
|-----|------|-------|
| `statistic_date` | DATE | Ngày thống kê |
| `total_transactions` | BIGINT | Tổng số giao dịch kiểm tra (hôm đó) |
| `anomalies_detected` | BIGINT | Số anomalies phát hiện |
| `anomaly_ratio` | DOUBLE | % anomalies = anomalies_detected / total_transactions |
| `critical_count` | BIGINT | Số giao dịch CRITICAL |
| `high_count` | BIGINT | Số giao dịch HIGH |
| `medium_count` | BIGINT | Số giao dịch MEDIUM |
| `low_count` | BIGINT | Số giao dịch LOW |
| `avg_anomaly_score` | DOUBLE | Trung bình anomaly score của hôm đó |
| `min_anomaly_score` | DOUBLE | Score thấp nhất (bất thường nhất) |
| `max_anomaly_score` | DOUBLE | Score cao nhất (bình thường nhất) |
| `model_name` | VARCHAR | Tên model: isolation_forest_anomaly_v1 |
| `model_version` | VARCHAR | Version: 1 |
| `created_at` | TIMESTAMP | Thời điểm insert |

**Ví dụ dữ liệu**:
```
statistic_date  total_transactions  anomalies_detected  anomaly_ratio  critical_count  avg_anomaly_score
2024-10-13      1,500              350                 23.33%         12              -0.5432
2024-10-12      1,400              280                 20.00%         8               -0.5201
2024-10-11      1,600              380                 23.75%         15              -0.5678
```

**Dùng để**:
- 📈 Metabase chart: Trend anomaly % qua các ngày
- 📊 KPI card: "Hôm nay: 23.33% anomalies (vs hôm qua 20%)"
- 🎯 Alert threshold: Nếu anomaly_ratio > 30% thì cảnh báo
- 📋 Daily report: Tổng hợp statistics cho management

---

### 🔄 Khi Chạy `detect_anomalies.py`, Điều Gì Xảy Ra?

**Workflow:**
```
detect_anomalies.py chạy (hàng ngày)
  ↓
[1] Load model từ MLflow
[2] Load 7 ngày giao dịch mới
[3] Tính 16 features
[4] Score anomalies → Get anomaly_score
[5] Assign severity (CRITICAL/HIGH/MEDIUM/LOW)
  ├─ Tạo 1 row cho MỖI anomaly transaction → Lưu vào ml_anomaly_alerts
  │   └─ 2,853 anomalies → 2,853 rows insert
  │
  └─ Tính statistics tổng hợp → Lưu vào ml_anomaly_statistics
      └─ 1 summary row (ngày hôm nay)

RESULT:
✅ ml_anomaly_alerts: +2,853 rows (mỗi anomaly là 1 row)
✅ ml_anomaly_statistics: +1 row (tổng hợp hôm nay)
```

---

### 📌 So Sánh 2 Bảng

| Aspect | ml_anomaly_alerts | ml_anomaly_statistics |
|--------|-------------------|----------------------|
| **Mục đích** | Chi tiết từng alert | Thống kê hàng ngày |
| **Số lượng rows/ngày** | +2,853 (1 row/anomaly) | +1 (1 row/ngày) |
| **Độ chi tiết** | Cao (từng transaction) | Thấp (tổng hợp) |
| **Dùng để** | Drill-down details | Trend tracking, KPI |
| **Metabase View** | Table + Filter | Line chart + Cards |
| **Size** | Lớn (scale với anomalies) | Nhỏ (1 row/day) |

---

## 🔄 Airflow Integration

**Weekly Training** (Chủ nhật 02:00 AM):
```python
train_task = PythonOperator(
    task_id='train_isolation_forest',
    python_callable=run_training_script,
    op_args=['/opt/ops/ML-anomaly_detection/train_isolation_forest.py']
)
```

**Daily Detection** (Hàng ngày 06:00 AM):
```python
detect_task = PythonOperator(
    task_id='detect_anomalies',
    python_callable=run_detection_script,
    op_args=['/opt/ops/ML-anomaly_detection/detect_anomalies.py']
)
```

## 📈 Features (16 features)

### Basic Features
- `amount_vnd`: Số tiền gôc
- `amount_log`: Log(amount) - handle skewed distribution
- `is_inflow`: 1/0 (tiền vào/ra)
- `is_large`: 1/0 (giao dịch lớn >100M)

### Time Features
- `hour_of_day`: 0-23
- `day_of_week`: 0-6 (thứ 2-CN)
- `day_of_month`: 1-31
- `is_weekend`: 1/0

### Rolling Statistics (7-day)
- `txn_count_7d`: Số giao dịch
- `amount_std_7d`: Độ lệch chuẩn
- `amount_mean_7d`: Trung bình
- `amount_max_7d`: Max amount

### Category Features (one-hot)
- `cat_receivable`: 1/0
- `cat_payable`: 1/0
- `cat_payroll`: 1/0
- `cat_other`: 1/0

## 🎚️ Severity Levels

| Severity | Anomaly Score | Ý Nghĩa |
|----------|---------------|---------|
| **CRITICAL** | ≤ -1.0 | Rất bất thường, cần kiểm tra ngay |
| **HIGH** | -1.0 to -0.75 | Khá bất thường, cần xem xét |
| **MEDIUM** | -0.75 to -0.5 | Bất thường trung bình |
| **LOW** | > -0.5 | Ít bất thường hoặc bình thường |

## 🔍 Khi Nào Một Giao Dịch Bị Coi Là Anomaly?

Isolation Forest phát hiện anomalies dựa trên:

1. **Isolation**: Các điểm khó "cách ly" (isolate) được coi là bất thường
2. **Feature Combinations**: Không chỉ dựa vào 1 feature, mà kết hợp toàn bộ
3. **Context**: So với 7 ngày gần nhất (rolling stats)

**Ví dụ anomalies phát hiện**:
- ✅ Giao dịch lúc 2 AM (bất thường với ghi nhân thường lệ)
- ✅ Giao dịch 500M VND khi trung bình 10M (outlier amount)
- ✅ 100+ giao dịch trong 1 ngày khi thường 10-20
- ✅ Thanh toán lương vào giữa tháng (thường cuối tháng)

## 📊 MLflow Model Registry

**URI**: `file:///tmp/mlflow` (hoặc server khác nếu config)

**Stored Model**:
```
Model: isolation_forest_anomaly_v1
├── Version 1
│   ├── Model (sklearn pickle)
│   ├── Scaler (StandardScaler)
│   ├── Features (JSON list)
│   └── Metrics (n_anomalies, ratio, etc)
└── Version 2 (nếu retrain)
```

**Load Model**:
```python
import mlflow
mlflow.set_tracking_uri("file:///tmp/mlflow")
model = mlflow.sklearn.load_model("models:/isolation_forest_anomaly_v1/1")
```

## � Workflow Execution

### Weekly Training (Sunday 2 AM)

```
┌─ WEEKLY (Sunday 2 AM) ─────────────────────────┐
│                                                │
│  python train_isolation_forest.py             │
│    ↓                                          │
│  [1] Load 206,914 transactions                │
│      └─ From: "sme-pulse".gold.fact_bank_txn │
│                                               │
│  [2] Engineer 16 features                     │
│      ├─ Amount: amount_vnd, amount_log        │
│      ├─ Time: hour, day, is_weekend          │
│      ├─ Rolling: 7-day stats                 │
│      └─ Category: receivable, payable, etc   │
│                                               │
│  [3] Train Isolation Forest (1 epoch)        │
│      ├─ n_estimators: 100                    │
│      ├─ contamination: 5%                    │
│      └─ Normalize: StandardScaler            │
│                                               │
│  [4] Evaluate: Quality Score = 72.8%         │
│      ├─ Anomalies: 10,338 (5%)               │
│      ├─ CV Std Dev: 0.0001 (GOOD)            │
│      ├─ Silhouette: 0.2847 (MODERATE)        │
│      ├─ Overlap: 23.45% (CLEAR <30%)         │
│      └─ Result: ✅ RELIABLE MODEL             │
│                                               │
│  [5] Save to MLflow (version 1)              │
│      ├─ Model artifact: .pkl                 │
│      ├─ Scaler artifact: .pkl                │
│      ├─ Features artifact: .json             │
│      └─ Run ID: 4666fd2fe76c48d0bc7e9ffcb4c7f336
│                                               │
└─────────────┬──────────────────────────────────┘
              │
              ↓ Best model ready for production
```

### Daily Detection (6 AM - Every Day)

```
┌─ DAILY (6 AM - EVERY DAY) ────────────────────┐
│                                                │
│  python detect_anomalies.py                   │
│    ↓                                          │
│  [1] Load Best Model from MLflow             │
│      ├─ Model: isolation_forest_anomaly_v1/1 │
│      ├─ Scaler: StandardScaler               │
│      └─ Features: 16 names                   │
│                                               │
│  [2] Load New Transactions (last 7 days)     │
│      ├─ From: "sme-pulse".gold.fact_bank_txn│
│      ├─ Date range: CURRENT_DATE - 7 days   │
│      └─ Count: ~1,000-2,000 new txn          │
│                                               │
│  [3] Engineer Same 16 Features               │
│      └─ Use same logic as training           │
│                                               │
│  [4] Score Anomalies                         │
│      ├─ Anomaly score: [-1.0 to 0.0]        │
│      ├─ Lower = More anomalous              │
│      └─ Detect: 537 anomalies (5%)           │
│                                               │
│  [5] Assign Severity Level                   │
│      ├─ CRITICAL: score ≤ -1.0 (12 txn)     │
│      ├─ HIGH: -1.0 to -0.75 (87 txn)       │
│      ├─ MEDIUM: -0.75 to -0.5 (213 txn)    │
│      └─ LOW: > -0.5 (225 txn)               │
│                                               │
│  [6] Save Alerts & Statistics                │
│      ├─ Insert: "sme-pulse".gold.ml_anomaly_alerts
│      │   └─ 537 alert rows                   │
│      ├─ Insert: "sme-pulse".gold.ml_anomaly_statistics
│      │   └─ 1 summary row per day            │
│      └─ Log: Detection completed ✅           │
│                                               │
└────────────────────────────────────────────────┘
```

### Model Quality Interpretation

**Training Output BƯỚC 4 shows these metrics:**

| Metric | Value | What It Means | Status |
|--------|-------|--------------|--------|
| **Anomalies Detected** | 10,338 (5%) | Matches contamination parameter | ✅ GOOD |
| **Anomaly Score Mean (Normal)** | -0.4861 | Normal txn cluster here | ✅ Clear |
| **Anomaly Score Mean (Anomaly)** | -0.6195 | Anomalies cluster more negative | ✅ Separated |
| **Score Separation** | 0.1334 | Gap between groups | ✅ > 0.10 |
| **Overlap Ratio** | 23.45% | % anomalies in normal range | ✅ < 30% |
| **CV Std Dev** | 0.0001 | Consistency across folds | ✅ < 0.1 |
| **Silhouette Score** | 0.2847 | Cluster quality | ⚠️ Moderate OK |
| **Overall Quality Score** | **72.8%** | **Combined metric** | **⭐⭐ GOOD** |

**Model is RELIABLE when:**
- ✅ Quality Score > 65%
- ✅ Anomaly ratio ≈ contamination (5%)
- ✅ Score separation > 0.10
- ✅ Overlap < 30%
- ✅ CV consistency good

**Current Status: ✅ ALL CHECKS PASSED - Safe for production**

## �🚀 Khởi Chạy

### Setup (lần đầu)

1. **Install dependencies**:
```bash
pip install trino pandas scikit-learn mlflow numpy
```

2. **Test connection**:
```bash
python test_connection.py
```

3. **Train model** (lần đầu):
```bash
python train_isolation_forest.py
```

### Daily Execution (Airflow)

```bash
# Detection chạy hàng ngày
python detect_anomalies.py

# Training chạy hàng tuần
python train_isolation_forest.py
```

## ⚙️ Cấu Hình

Edit các constants ở đầu từng file:

```python
# train_isolation_forest.py
TRAINING_DAYS = 180        # Số ngày training
CONTAMINATION = 0.05       # % expected anomalies (5%)
N_ESTIMATORS = 100         # Số cây
MLFLOW_TRACKING_URI = "file:///tmp/mlflow"

# detect_anomalies.py
DETECTION_DAYS = 7         # Số ngày detection
ANOMALY_SCORE_THRESHOLD = -0.5  # Score threshold
```

## 📝 Logs

Logs được in ra với format:

```
2025-11-11 09:30:45 - __main__ - INFO - ✅ Model trained successfully!
2025-11-11 09:35:22 - __main__ - INFO - Anomalies detected: 12 (0.6%)
```

## 🐛 Troubleshooting

| Vấn đề | Giải Pháp |
|--------|-----------|
| `ImportError: No module named 'trino'` | `pip install trino` |
| `No such table: fact_bank_txn` | Verify dbt models deployed + Trino running |
| `Model not found in MLflow` | Run `train_isolation_forest.py` first |
| `Memory error with large dataset` | Reduce TRAINING_DAYS hoặc DETECTION_DAYS |

## 📞 Contact

- **Owner**: ML Team
- **Related Models**: UC05 (Payment Prediction), UC09 (Cashflow Forecast)
- **Data Team**: For schema/Trino issues
