Chính xác! Mỗi bảng data assembly trong thư mục `silver/ml_training/` được thiết kế để phục vụ cho **một mô hình ML cụ thể**, nhằm giải quyết **một Use Case nghiệp vụ (UC)** trong hệ thống SME Pulse.

Đây là bảng tóm tắt mối quan hệ 1-1 giữa bảng dữ liệu, mô hình, và Use Case:

| **Tên bảng (Data Assembly)** | **Mô hình ML phục vụ** | **Use Case chính (UC)** | **Mục tiêu nghiệp vụ** |
| --- | --- | --- | --- |
| `ml_training_payment_pred` | **Hồi quy/Phân loại (Prophet, XGBoost)** | **UC05: Quản lý công nợ phải thu (AR)** | Dự đoán *số ngày* khách hàng sẽ trả tiền (days-to-pay). |
| `ml_training_ar_scoring` | **Thuật toán chấm điểm (Heuristic Scoring)** | **UC05: Quản lý công nợ phải thu (AR)** | Xếp hạng ưu tiên thu hồi nợ (Collection Priority Score). |
| `ml_training_cashflow_fcst` | **Dự báo chuỗi thời gian (Prophet)** | **UC09: Dự báo dòng tiền (Forecast)** | Dự báo dòng tiền thuần (`y`) hàng ngày trong tương lai. |

---

## 📊 Giải mã chi tiết vai trò từng bảng ML_Training

### 1. `ml_training_payment_pred.sql`

- **Dữ liệu tập hợp:** Tất cả các đặc trưng (`ftr_invoice_risk`, `ftr_customer_behavior`, `ftr_seasonality`...).
- **Mục tiêu chính:** Chứa **Label** (đáp án) là cột `target_days_to_pay`.
- **Mô hình phục vụ:** Mô hình Hồi quy hoặc Phân loại (Regression/Classification Model).
- **Use Case trong hệ thống:** **UC05 - Quản lý công nợ phải thu (AR)**.
    - Mô hình này được huấn luyện để dự đoán chính xác khi nào một hóa đơn **sẽ được thanh toán**.
    - Sau khi mô hình dự đoán, kết quả (ví dụ: `predicted_payment_date`) sẽ được đưa vào lớp **Gold Layer** (`score_payment_pred`).
    - **Giá trị:** Giúp kế toán biết chính xác hóa đơn nào cần nhắc nhở *sớm* nhất (vì dự đoán trễ hạn) và hóa đơn nào có thể để sau (vì dự đoán đúng hạn).

---

### 2. `ml_training_ar_scoring.sql`

- **Dữ liệu tập hợp:** Tương tự `ml_training_payment_pred`, nhưng **chỉ dành cho các hóa đơn đang mở (`is_open = true`)**.
- **Mục tiêu chính:** Đây là bảng **Inference/Scoring** (dự đoán).
- **Mô hình phục vụ:** Mô hình Chấm điểm/Xếp hạng (Heuristic Scoring Algorithm).
    - Mô hình này không cần huấn luyện phức tạp mà dùng logic nghiệp vụ (heuristic) để tính điểm ưu tiên thu nợ dựa trên các feature như `days_overdue`, `total_open_amount` và `risk_flags`.
- **Use Case trong hệ thống:** **UC05 - Quản lý công nợ phải thu (AR)**.
    - **Giá trị:** Giúp kế toán hoặc thu ngân sắp xếp danh sách công nợ theo **"Điểm ưu tiên"** giảm dần, để tập trung nguồn lực vào những khoản nợ có nguy cơ cao nhất hoặc giá trị lớn nhất.

---

### 3. `ml_training_cashflow_fcst.sql`

- **Dữ liệu tập hợp:** Dữ liệu chuỗi thời gian (time series) với cột `ds` (ngày) và `y` (Net Cash Flow), cùng các biến ngoại sinh (regressors) như `is_holiday_vn`, `macro_gdp_growth`.
- **Mục tiêu chính:** Chứa dữ liệu lịch sử của dòng tiền để mô hình Prophet học các quy luật.
- **Mô hình phục vụ:** **Prophet** (Thư viện dự báo chuỗi thời gian của Facebook).
- **Use Case trong hệ thống:** **UC09 - Dự báo dòng tiền (Forecast)**.
    - **Giá trị:** Giúp chủ doanh nghiệp nhìn thấy biểu đồ dự báo dòng tiền trong 30-90 ngày tới và nhận **cảnh báo âm quỹ** kịp thời.

---

### 🚨 Về Anomaly Detection (Phát hiện bất thường)

Bạn có đề cập đến **Anomaly Detection** (Phát hiện bất thường) - **UC10**.

Trong thiết kế hiện tại, mô hình này (`Isolation Forest`) không sử dụng một bảng `ml_training` riêng biệt mà:

- **Nó đọc trực tiếp từ các bảng Feature (hoặc Fact):** Ví dụ, nó có thể đọc `ftr_invoice_risk` hoặc `fact_bank_txn` để tìm các điểm dữ liệu "xa lạ" (outliers) như một khoản chi tiêu đột biến hoặc doanh thu ngày giảm sút bất thường.
- **Lý do:** Isolation Forest là thuật toán **học không giám sát** (Unsupervised Learning), nó không cần Label (đáp án) để huấn luyện. Do đó, nó không cần bảng *tập hợp* (assembly) riêng như các mô hình học giám sát khác.

---

## 🤖 Các Use Case (UC) áp dụng ML/AI

| **Mã UC** | **Tên Use Case chính** | **Mô hình/Thuật toán áp dụng** | **Mục tiêu giải quyết** |
| --- | --- | --- | --- |
| **UC05** | **Quản lý Công nợ Phải thu (AR)** | **Heuristic Scoring** & **Payment Prediction Model** | Xếp hạng ưu tiên thu nợ và dự đoán ngày thanh toán để cải thiện DSO. |
| **UC09** | **Dự báo Dòng tiền (Forecast)** | **Prophet (Time Series)** | Dự báo dòng tiền vào/ra (inflow/outflow) 14-30-90 ngày và cảnh báo nguy cơ âm quỹ. |
| **UC10** | **Phát hiện Bất thường (Anomaly Detection)** | **Isolation Forest** | Phát hiện giao dịch bất thường (chi phí spike, hoàn tiền lạ) để cảnh báo cho chủ doanh nghiệp. |

---

## 📊 Chi tiết các Mô hình (Model) đang triển khai

Chúng ta đang triển khai tổng cộng **4 mô hình/thuật toán** chính, được nhóm lại thành các Use Case như sau:

### 1. 💰 UC09: Dự báo Dòng tiền (Cashflow Forecasting)

| **Model** | **Thuật toán** | **Nguồn dữ liệu (Input)** | **Tác vụ (Output)** |
| --- | --- | --- | --- |
| **Cashflow Forecast** | **Prophet** | Bảng `ml_training_cashflow_fcst` (chứa `ds`, `y` (Net Cash Flow) và các regressors vĩ mô, mùa vụ) | Dự báo giá trị $Y_{t+n}$ (Dòng tiền ròng trong $n$ ngày tới). |
|  | **Isolation Forest** (Hỗ trợ) | Đọc các chỉ số KPI theo ngày/tháng | Phát hiện điểm bất thường (spikes/dips) trong dữ liệu lịch sử để làm sạch trước khi đưa vào Prophet. |

---

### 2. 🧾 UC05: Quản lý Công nợ (AR Management)

| **Model** | **Thuật toán** | **Nguồn dữ liệu (Input)** | **Tác vụ (Output)** |
| --- | --- | --- | --- |
| **Payment Prediction** | **Hồi quy/XGBoost** | Bảng `ml_training_payment_pred` (chứa Label `target_days_to_pay`) | Dự đoán `predicted_days_to_pay` và `predicted_payment_date` cho các hóa đơn **đang mở**. |
| **AR Priority Scoring** | **Heuristic Scoring** | Đọc các đặc trưng rủi ro (`ftr_invoice_risk`, `ftr_customer_behavior`) | Gán **Điểm ưu tiên** thu hồi nợ (dựa trên: số ngày quá hạn, số tiền, rủi ro khách hàng). |

---

### 3. 🚨 UC10: Phát hiện Bất thường (Anomaly Detection)

| **Model** | **Thuật toán** | **Nguồn dữ liệu (Input)** | **Tác vụ (Output)** |
| --- | --- | --- | --- |
| **Transaction/KPI Anomaly** | **Isolation Forest** | Các chỉ số tài chính theo ngày/tháng (ví dụ: `fact_bank_txn`, `kpi_daily_revenue`) | Gán **Anomaly Score** và tạo cảnh báo (Alert) nếu score vượt ngưỡng. |

Would you like me to focus on creating the final Python scripts for the **Cashflow Forecast (UC09)** model next?