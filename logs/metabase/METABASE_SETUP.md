# Metabase - Trino Connection Setup Guide

## 📋 Thông tin kết nối Trino

Sau khi JDBC driver đã được mount vào Metabase, làm theo các bước sau:

### 1. Truy cập Metabase
- URL: http://localhost:3000
- Nếu lần đầu: Setup admin account (email/password tùy ý)

### 2. Thêm Database Connection
- Click vào **Settings** (⚙️) ở góc trên bên phải
- Chọn **Admin settings** → **Databases** → **Add database**

### 3. Cấu hình Trino Connection

**Database type:** Trino (should appear after JDBC driver loaded)

**Display name:** `SME Lakehouse - Trino`

**Host:** `trino` (service name trong Docker network)

**Port:** `8080`

**Database name:** `iceberg` (catalog name)

**Username:** `metabase` (hoặc bất kỳ username nào, Trino không check auth trong local mode)

**Password:** Leave blank (no authentication)

**Additional JDBC connection string options:**
```
SSL=false
```

### 4. Test Connection
- Click **Test connection** button
- Nếu thành công sẽ hiện: ✅ "Successfully connected to database"

### 5. Click **Save**

---

## 📊 Tạo Dashboard từ Gold tables

### Query iceberg.gold.fact_orders

```sql
SELECT 
  order_date,
  org_id,
  payment_method,
  total_orders,
  unique_customers,
  total_revenue,
  avg_order_value,
  discount_rate_pct,
  revenue_per_order
FROM iceberg.gold.fact_orders
WHERE order_date >= CURRENT_DATE - INTERVAL '30' DAY
ORDER BY order_date DESC, total_revenue DESC;
```

### Tạo Visualizations

1. **Line Chart**: Revenue theo thời gian
   - X-axis: order_date
   - Y-axis: total_revenue
   - Group by: payment_method

2. **Bar Chart**: Orders by Organization
   - X-axis: org_id
   - Y-axis: total_orders
   
3. **Number**: KPIs
   - Total Revenue: `SUM(total_revenue)`
   - Total Orders: `SUM(total_orders)`
   - Avg Order Value: `AVG(avg_order_value)`

---

## ✅ Verification Steps

### 1. Browse schema trong Metabase
- Sau khi connect, click vào database "SME Lakehouse - Trino"
- Sẽ thấy 3 schemas: `bronze`, `silver`, `gold`
- Click vào `gold` → sẽ thấy table `fact_orders`

### 2. Run sample query
- Click **Ask a question** → **Native query**
- Chọn database: SME Lakehouse - Trino
- Paste query trên và Run

### 3. Verify data
- Kết quả phải trả về rows từ Gold layer (data từ ngày 2025-10-19)
- Số liệu phải khớp với kết quả từ Trino CLI:
  ```
  Total revenue > 400K VND
  Total orders = 20
  ```

---

## 🔧 Troubleshooting

### Issue: "Trino" không xuất hiện trong Database type dropdown
**Solution:** 
- Check JDBC driver: `docker exec sme-metabase ls -lh /plugins/`
- Restart Metabase: `docker compose restart metabase`
- Wait 1-2 minutes for Metabase to scan plugins folder

### Issue: Connection test failed - "Could not connect to trino"
**Solution:**
- Verify Trino is running: `docker ps | grep trino`
- Check Trino health: `docker exec sme-trino trino --execute "SELECT 1"`
- Ensure both services on same network: `sme-network`

### Issue: "Access Denied" error
**Solution:**
- Trino local mode không cần authentication
- Leave Password field blank
- Username có thể là bất kỳ string nào (e.g., "metabase", "admin")

---

## 📌 Connection Info Summary

| Field | Value |
|-------|-------|
| Type | Trino |
| Host | `trino` |
| Port | `8080` |
| Catalog | `iceberg` |
| Username | `metabase` |
| Password | (blank) |
| SSL | `false` |
| JDBC Driver | `/plugins/trino-jdbc-435.jar` |

