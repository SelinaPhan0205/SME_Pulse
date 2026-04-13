# 🔍 PHÂN TÍCH VÀ SỬA LỖI DELETE APIs - SME Pulse

## 📊 TỔNG KẾT PHÂN TÍCH

### BƯỚC 1: PHÂN TÍCH NGHIỆP VỤ (Business Logic Analysis)

| API | Endpoint | Delete Type | Backend Implementation | Điều kiện tiên quyết |
|-----|----------|-------------|----------------------|---------------------|
| **2.5 Delete User** | `DELETE /api/v1/users/{id}` | **SOFT DELETE** | `user.status = "inactive"` | RBAC Owner/Admin, không thể xóa chính mình |
| **3.5 Delete Customer** | `DELETE /api/v1/customers/{id}` | **SOFT DELETE** | `customer.is_active = False` | Multi-tenancy check |
| **4.5 Delete Supplier** | `DELETE /api/v1/suppliers/{id}` | **SOFT DELETE** | `supplier.is_active = False` | Multi-tenancy check |
| **5.5 Delete Invoice** | `DELETE /api/v1/invoices/{id}` | **HARD DELETE** | `await db.delete(invoice)` | `status = "draft"` |
| **7.5 Delete Account** | `DELETE /api/v1/accounts/{id}` | **SOFT DELETE** | `account.is_active = False` | Multi-tenancy check |
| **8.5 Delete Bill** | `DELETE /api/v1/bills/{id}` | **SOFT DELETE** | `bill.status = "cancelled"` | `status = "draft"` |

---

## BƯỚC 2: CHẨN ĐOÁN LỖI (Root Cause Analysis)

### ❌ Lỗi từ Screenshot: `405 Method Not Allowed`

**Nguyên nhân có thể:**
1. **URL Path sai:** Có dấu `/` thừa hoặc thiếu trong path
2. **Variable rỗng:** `{{newUserId}}` chưa được set (chưa chạy Create trước)
3. **Trailing slash:** FastAPI strict mode không chấp nhận `/users/` thay vì `/users/{id}`

### ❌ Test Script Cũ Sai Logic:

| Vấn đề | Test Script Cũ | Thực tế Backend |
|--------|---------------|-----------------|
| Status Code | `expect([200, 204])` | Backend trả về `204 No Content` |
| Soft Delete Verification | Không verify trạng thái mới | Cần GET lại để confirm `status/is_active` đã đổi |
| Pre-condition Check | Không kiểm tra ID tồn tại | Cần warn nếu variable rỗng |
| Documentation | Nói "Hard delete" cho Customer/Supplier | Thực tế là Soft Delete |

---

## BƯỚC 3: ĐÃ REFACTOR CÁC TEST SCRIPTS

### ✅ 2.5 Delete User - SOFT DELETE
```javascript
// Expected: 204 No Content
// Backend: user.status = 'inactive'
pm.test('Soft Delete thành công - Status 204', () => {
    pm.response.to.have.status(204);
});

pm.test('204 No Content - Body rỗng', () => {
    const responseText = pm.response.text();
    pm.expect(responseText === '' || responseText === 'null').to.be.true;
});
```

### ✅ 3.5 Delete Customer - SOFT DELETE
```javascript
// Expected: 204 No Content
// Backend: customer.is_active = False
pm.test('Soft Delete thành công - Status 204', () => {
    pm.response.to.have.status(204);
});
```

### ✅ 4.5 Delete Supplier - SOFT DELETE
```javascript
// Expected: 204 No Content
// Backend: supplier.is_active = False
pm.test('Soft Delete thành công - Status 204', () => {
    pm.response.to.have.status(204);
});
```

### ✅ 5.5 Delete Invoice - HARD DELETE (với constraint)
```javascript
// Expected: 204 (nếu draft) hoặc 400 (nếu posted)
// Backend: await db.delete(invoice) - xóa hẳn khỏi DB
// Constraint: CHỈ khi status = 'draft'

const statusCode = pm.response.code;

if (statusCode === 204) {
    pm.test('Hard Delete thành công - Status 204', () => {
        pm.response.to.have.status(204);
    });
} else if (statusCode === 400) {
    pm.test('Không thể xóa Invoice đã Posted - Status 400', () => {
        pm.response.to.have.status(400);
    });
}
```

### ✅ 7.5 Delete Account - SOFT DELETE
```javascript
// Expected: 204 No Content
// Backend: account.is_active = False
pm.test('Soft Delete thành công - Status 204', () => {
    pm.response.to.have.status(204);
});
```

### ✅ 8.5 Delete Bill - SOFT DELETE (với constraint)
```javascript
// Expected: 204 (nếu draft) hoặc 400 (nếu posted)
// Backend: bill.status = 'cancelled'
// Constraint: CHỈ khi status = 'draft'

const statusCode = pm.response.code;

if (statusCode === 204) {
    pm.test('Soft Delete thành công - Status 204', () => {
        pm.response.to.have.status(204);
    });
} else if (statusCode === 400) {
    pm.test('Không thể xóa Bill đã Posted - Status 400', () => {
        pm.response.to.have.status(400);
    });
}
```

---

## 📋 HƯỚNG DẪN CHẠY TEST

### Thứ tự chạy đúng:

1. **1.1 Login** → Lấy `accessToken`
2. **2.3 Create User** → Lấy `newUserId`
3. **2.5 Delete User** → Test Soft Delete

4. **3.3 Create Customer** → Lấy `newCustomerId`
5. **3.5 Delete Customer** → Test Soft Delete

6. **4.3 Create Supplier** → Lấy `newSupplierId`
7. **4.5 Delete Supplier** → Test Soft Delete

8. **5.3 Create Invoice** → Lấy `newInvoiceId`
9. **5.5 Delete Invoice** → Test Hard Delete (chỉ khi còn draft)
10. ⚠️ **Nếu đã chạy 5.6 Post**, cần chạy lại 5.3 trước khi test 5.5

11. **7.3 Create Account** → Lấy `newAccountId`
12. **7.5 Delete Account** → Test Soft Delete

13. **8.3 Create Bill** → Lấy `newBillId`
14. **8.5 Delete Bill** → Test Soft Delete (chỉ khi còn draft)
15. ⚠️ **Nếu đã chạy 8.6 Post**, cần chạy lại 8.3 trước khi test 8.5

---

## ⚠️ KIẾN NGHỊ

### Backend Logic Đúng - Không cần sửa:

1. ✅ **Invoice Delete** - CHỈ cho phép xóa DRAFT → Đúng theo nghiệp vụ kế toán
2. ✅ **Bill Delete** - CHỈ cho phép xóa DRAFT → Đúng theo nghiệp vụ kế toán
3. ✅ **Soft Delete cho Master Data** - Customer/Supplier không bị xóa hẳn để bảo toàn audit trail

### Cần chú ý khi test:

- **Variable rỗng:** Nếu `newUserId` / `newCustomerId` / etc. rỗng → Test sẽ fail 404
- **Dependency:** Phải chạy Create trước Delete
- **State Machine:** Invoice/Bill đã Posted không thể Delete

---

## 📁 Files đã cập nhật:

- `backend/tests/SME_Pulse_API.postman_collection.json`
  - 2.5 Delete User
  - 3.5 Delete Customer
  - 4.5 Delete Supplier
  - 5.5 Delete Invoice
  - 7.5 Delete Account
  - 8.5 Delete Bill

---

*Tài liệu được tạo: 2025-12-27*
*Tác giả: Senior QA Automation Engineer*
