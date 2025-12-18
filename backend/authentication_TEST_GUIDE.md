# PHASE 4: Security Edge Cases Testing Guide

**Date:** November 20, 2025  
**Project:** SME Pulse Backend  
**Phase:** PHASE 4 - Security Edge Cases Testing  
**Status:** Test Scenarios & Expected Results

---

## Overview

This document provides comprehensive test scenarios for PHASE 4 of the authentication system. Each test case includes:
- **Test Description**
- **How to Execute**
- **Expected Result**
- **Verification Steps**

All tests should pass if the authentication, middleware, and exception handling are properly implemented.

---

## Test Scenarios & Expected Results

### 1. Invalid Credentials Handling

#### Test 1.1: Wrong Password
```bash
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "admin@sme.com",
  "password": "wrongpassword"
}
```
**Expected Result:** 
- Status: `401 Unauthorized`
- Response: `{"error": "Incorrect email or password"}`
- Log: Warning entry for failed login attempt

---

#### Test 1.2: Non-existent Email
```bash
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "nonexistent@test.com",
  "password": "123456"
}
```
**Expected Result:**
- Status: `401 Unauthorized`
- Response: `{"error": "Incorrect email or password"}`
- Log: Warning entry for non-existent email

---

#### Test 1.3: Empty Password
```bash
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "admin@sme.com",
  "password": ""
}
```
**Expected Result:**
- Status: `422 Unprocessable Entity`
- Response: Validation error with field `password`
- Detail: `"Field required"` or `"at least 1 character"`

---

#### Test 1.4: Invalid Email Format
```bash
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "invalid-email",
  "password": "123456"
}
```
**Expected Result:**
- Status: `422 Unprocessable Entity`
- Response: Validation error for email field
- Detail: `"value is not a valid email address"`

---

### 2. Valid Login Flow

#### Test 2.1: Successful Login
```bash
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "admin@sme.com",
  "password": "123456"
}
```
**Expected Result:**
- Status: `200 OK`
- Response includes:
  - `access_token`: Valid JWT token
  - `token_type`: `"bearer"`
  - `expires_in`: `1800` (seconds)
  - `user`: User object with id, email, full_name, org_id, status
  - `roles`: Array of role codes (e.g., `["owner", "admin"]`)

**Response Example:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": 1,
    "email": "admin@sme.com",
    "full_name": "Administrator",
    "org_id": 2,
    "status": "active"
  },
  "roles": ["owner", "admin"]
}
```

---

### 3. Token Validation

#### Test 3.1: Valid Token
```bash
GET /api/v1/auth/me
Authorization: Bearer <valid_token_from_2.1>
```
**Expected Result:**
- Status: `200 OK`
- Returns user data matching token payload
- Response includes org_id matching token's org_id

---

#### Test 3.2: Malformed JWT - Invalid Format
```bash
GET /api/v1/auth/me
Authorization: Bearer invalid.token
```
**Expected Result:**
- Status: `401 Unauthorized`
- Response: `{"detail": "Could not validate credentials"}`

---

#### Test 3.3: Incomplete JWT - Header Only
```bash
GET /api/v1/auth/me
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9
```
**Expected Result:**
- Status: `401 Unauthorized`
- Log: Warning "JWT decode error: Not enough segments"

---

#### Test 3.4: Tampered Token Signature
**Steps:**
1. Obtain valid token from Test 2.1
2. Decode JWT payload and modify `org_id` value
3. Re-encode and send request with modified token

```bash
GET /api/v1/auth/me
Authorization: Bearer <tampered_token>
```
**Expected Result:**
- Status: `401 Unauthorized`
- Reason: Signature verification fails
- Log: Error entry for invalid token

---

#### Test 3.5: Missing Authorization Header
```bash
GET /api/v1/auth/me
```
**Expected Result:**
- Status: `401 Unauthorized` or `403 Forbidden`
- Response: `{"detail": "Not authenticated"}`

---

### 4. Multi-Tenancy Isolation

#### Test 4.1: Verify org_id in Token
```bash
# Obtain token from Test 2.1
# Decode JWT payload (base64 decode the middle part)
```
**Expected Result:**
- JWT payload contains `org_id: 2`
- JWT payload contains `sub: "1"` (user_id)
- JWT payload contains `roles: ["owner", "admin"]`
- JWT payload contains `exp` (expiration timestamp)

**Expected JWT Payload:**
```json
{
  "sub": "1",
  "org_id": 2,
  "roles": ["owner", "admin"],
  "exp": 1763641934
}
```

---

#### Test 4.2: Verify org_id in Response
```bash
GET /api/v1/auth/me
Authorization: Bearer <token_from_2.1>
```
**Expected Result:**
- Response includes `org_id: 2`
- org_id in response matches org_id in JWT payload
- org_id in response matches database record

---

#### Test 4.3: Token Tampering with org_id
**Steps:**
1. Get valid token
2. Decode and change `org_id` from 2 to 9999
3. Send with tampered org_id

```bash
GET /api/v1/auth/me
Authorization: Bearer <tampered_org_id_token>
```
**Expected Result:**
- Status: `401 Unauthorized`
- Reason: JWT signature verification fails
- Log: Warning about invalid token

---

### 5. Rate Limiting on Login

#### Test 5.1: Normal Login Attempts
```bash
# Make 5 login attempts (valid or invalid)
for i in {1..5}; do
  curl -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"wrong"}'
done
```
**Expected Result:**
- Requests 1-5: Status `401 Unauthorized`
- No rate limiting triggered

---

#### Test 5.2: Exceed Rate Limit (6th Request)
```bash
# 6th request within 60 seconds
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"wrong"}'
```
**Expected Result:**
- Status: `429 Too Many Requests`
- Response header: `Retry-After: 60`
- Response body:
```json
{
  "error": "Too many requests",
  "detail": "Rate limit exceeded. Please try again in 60 seconds.",
  "retry_after": 60
}
```

---

### 6. Security Headers

#### Test 6.1: Verify Security Headers on Any Endpoint
```bash
curl -i http://localhost:8000/health
```
**Expected Result:**
All responses should include these headers:

| Header | Expected Value |
|--------|-----------------|
| X-Content-Type-Options | nosniff |
| X-Frame-Options | DENY |
| X-XSS-Protection | 1; mode=block |
| Strict-Transport-Security | max-age=31536000; includeSubDomains |
| Referrer-Policy | strict-origin-when-cross-origin |

---

### 7. Request Tracking

#### Test 7.1: Verify Request ID and Process Time
```bash
curl -i http://localhost:8000/api/v1/auth/me
```
**Expected Result:**
- Response header `X-Request-ID`: UUID v4 format (e.g., `9f204f7a-aed1-4601-a32c-2131585123de`)
- Response header `X-Process-Time`: Float value in seconds (e.g., `0.0005486011505126953`)
- Each request has unique ID

---

### 8. Validation Error Handling

#### Test 8.1: Missing Required Field
```bash
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "admin@sme.com"
}
```
**Expected Result:**
- Status: `422 Unprocessable Entity`
- Response:
```json
{
  "error": "Validation error",
  "detail": [
    {
      "loc": ["body", "password"],
      "msg": "Field required",
      "type": "missing"
    }
  ],
  "request_id": "<unique-request-id>"
}
```

---

#### Test 8.2: Invalid Data Type
```bash
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "admin@sme.com",
  "password": 12345
}
```
**Expected Result:**
- Status: `422 Unprocessable Entity`
- Response includes type validation error

---

### 9. Structured Logging

#### Test 9.1: Check Backend Logs
```bash
docker compose logs backend --tail 50
```
**Expected Result:**
- Logs in JSON format (machine-parseable)
- Each log entry includes:
  - `timestamp`: ISO 8601 format
  - `level`: INFO, WARNING, ERROR
  - `message`: Clear description
  - `request_id`: Unique identifier
  - `path`: API endpoint path
  - `status_code`: HTTP status
  - `process_time`: Execution time in seconds

**Example Log Entry:**
```json
{
  "timestamp": "2025-11-20T12:29:32.581043Z",
  "level": "INFO",
  "logger": "app.middleware.security",
  "message": "Request completed",
  "request_id": "473f1c90-f305-4fa5-a3a7-46d5a376d742",
  "method": "POST",
  "path": "/api/v1/auth/login",
  "status_code": 200,
  "process_time": 0.038,
  "client_ip": "172.18.0.1"
}
```

---

## Expected Test Results Summary

| Test Case | Expected Status | Expected Behavior |
|-----------|-----------------|-------------------|
| **Invalid Credentials** | | |
| Wrong password | 401 | Reject with "Incorrect email or password" |
| Non-existent email | 401 | Reject with "Incorrect email or password" |
| Empty password | 422 | Validation error: field required |
| Invalid email format | 422 | Validation error: invalid email |
| **Valid Login** | | |
| Successful login | 200 | Return JWT token + user data + roles |
| Token format | Valid | `header.payload.signature` format |
| Roles extraction | ['owner', 'admin'] | Correctly extracted from database |
| **Token Validation** | | |
| Valid token | 200 | Return authenticated user data |
| Malformed token | 401 | Reject invalid format |
| Incomplete JWT | 401 | Reject incomplete token |
| Tampered signature | 401 | Reject signature mismatch |
| Missing auth header | 401 | Reject unauthenticated request |
| **Multi-tenancy** | | |
| org_id in JWT | 2 | Correctly set in token payload |
| org_id in response | 2 | Matches database and JWT |
| Tampered org_id | 401 | Signature verification fails |
| **Rate Limiting** | | |
| Requests 1-5 | 401 | Normal processing (invalid creds) |
| Request 6 | 429 | Rate limit exceeded |
| Retry-After header | 60 | Specifies retry window |
| **Security Headers** | | |
| X-Content-Type-Options | nosniff | Present on all responses |
| X-Frame-Options | DENY | Present on all responses |
| X-XSS-Protection | 1; mode=block | Present on all responses |
| Strict-Transport-Security | Set | Present on all responses |
| **Request Tracking** | | |
| X-Request-ID | UUID v4 | Unique identifier present |
| X-Process-Time | Float (seconds) | Performance metric recorded |
| **Validation Errors** | | |
| Missing field | 422 | Detailed field error info |
| Invalid type | 422 | Type mismatch error |
| Error details | Error object | Includes request_id for tracking |
| **Exception Handling** | | |
| Auth errors (401) | 401 | Logged + error message returned |
| Validation (422) | 422 | Logged + field details returned |
| Rate limit (429) | 429 | Logged + retry instructions returned |
| Unhandled errors | 500 | Logged fully + generic message returned |
| **Structured Logging** | | |
| Log format | JSON | Machine-parseable format |
| Fields included | All | timestamp, level, message, request_id, etc. |
| Request tracking | request_id | Consistent across all operations |

---

## How to Execute Tests

### Option 1: Manual Testing (Postman/curl)
```bash
# Test 1: Wrong password
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@sme.com","password":"wrong"}'

# Test 2: Valid login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@sme.com","password":"123456"}'

# Test 3: Valid token (use token from Test 2)
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/auth/me

# Test 4: Check headers
curl -i http://localhost:8000/health
```

### Option 2: Python Script Testing
```python
import requests

# Run all tests
BASE_URL = "http://localhost:8000"

# Test invalid credentials
response = requests.post(
    f"{BASE_URL}/api/v1/auth/login",
    json={"email": "admin@sme.com", "password": "wrong"}
)
assert response.status_code == 401, "Should reject wrong password"

# Test valid login
response = requests.post(
    f"{BASE_URL}/api/v1/auth/login",
    json={"email": "admin@sme.com", "password": "123456"}
)
assert response.status_code == 200, "Should accept valid credentials"

token = response.json()["access_token"]

# Test token validation
response = requests.get(
    f"{BASE_URL}/api/v1/auth/me",
    headers={"Authorization": f"Bearer {token}"}
)
assert response.status_code == 200, "Should accept valid token"

print("All tests passed!")
```

### Option 3: Backend Logs
```bash
# Check logs in real-time
docker compose logs -f backend | grep -E "401|422|429|200"

# Check specific test results
docker compose logs backend --tail 100 | grep "request_id"
```

---

## Test Environment

- **Backend:** FastAPI 0.115.0
- **Database:** PostgreSQL 15 (async via asyncpg)
- **Security:** JWT (HS256), Bcrypt password hashing
- **Middleware:** RequestContext, SecurityHeaders, RateLimit
- **Logging:** Structured JSON logging to file + console

**Seed Data:**
- User: `admin@sme.com` / `123456`
- Org ID: 2
- Roles: owner, admin

---

## Notes for Testers

1. **Rate limiting resets after 60 seconds** - Wait if you hit 429 error
2. **Token expires after 30 minutes** - Refresh login if /auth/me returns 401
3. **Each request gets unique X-Request-ID** - Use for debugging
4. **Logs are in JSON format** - Parse with `jq` or Python json module
5. **Multi-tenancy enforced on every endpoint** - org_id must match token

---

**Guide Version:** 1.0  
**Last Updated:** 2025-11-20  
**Status:** Ready for Testing
