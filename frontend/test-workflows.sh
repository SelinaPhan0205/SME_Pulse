#!/bin/bash

# ===================================================================
# SME Pulse - E2E Workflow & RBAC Testing
# Test complete business flows and role-based access control
# ===================================================================

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "========================================================================"
echo "🧪 SME PULSE - E2E WORKFLOW & RBAC TESTING"
echo "========================================================================"
echo -e "${NC}"

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Function to test API with assertions
test_workflow() {
    local test_name="$1"
    local method="$2"
    local endpoint="$3"
    local body="$4"
    local token="$5"
    local expected_status="$6"
    
    echo -e "${YELLOW}Testing:${NC} $test_name"
    
    if [ "$method" == "GET" ]; then
        RESPONSE=$(curl -s -w "\n%{http_code}" -H "Authorization: Bearer $token" "http://localhost:8000$endpoint")
    else
        RESPONSE=$(curl -s -w "\n%{http_code}" -X $method -H "Authorization: Bearer $token" -H "Content-Type: application/json" -d "$body" "http://localhost:8000$endpoint")
    fi
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | head -n-1)
    
    if [ "$HTTP_CODE" == "$expected_status" ]; then
        echo -e "  ${GREEN}✅ PASS${NC} [HTTP $HTTP_CODE]"
        ((TESTS_PASSED++))
        echo "$BODY"
        return 0
    else
        echo -e "  ${RED}❌ FAIL${NC} [Expected $expected_status, got $HTTP_CODE]"
        echo -e "  ${RED}Response: $BODY${NC}"
        ((TESTS_FAILED++))
        return 1
    fi
}

# ===================================================================
# SETUP: Login as different users
# ===================================================================
echo -e "\n${CYAN}🔐 STEP 1: Authentication Setup${NC}\n"

# Admin login
echo "Logging in as Admin..."
ADMIN_RESPONSE=$(curl -s -X POST "http://localhost:8000/auth/login" -H "Content-Type: application/json" -d '{"email":"admin@sme.com","password":"admin123"}')
ADMIN_TOKEN=$(echo $ADMIN_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$ADMIN_TOKEN" ]; then
    echo -e "${RED}❌ Admin login failed!${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Admin logged in${NC}"

# Accountant login
echo "Logging in as Accountant..."
ACCOUNTANT_RESPONSE=$(curl -s -X POST "http://localhost:8000/auth/login" -H "Content-Type: application/json" -d '{"email":"accountant@sme.com","password":"accountant123"}')
ACCOUNTANT_TOKEN=$(echo $ACCOUNTANT_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$ACCOUNTANT_TOKEN" ]; then
    echo -e "${YELLOW}⚠️  Accountant login failed (may not exist yet)${NC}"
    ACCOUNTANT_TOKEN=""
else
    echo -e "${GREEN}✅ Accountant logged in${NC}"
fi

# Cashier login
echo "Logging in as Cashier..."
CASHIER_RESPONSE=$(curl -s -X POST "http://localhost:8000/auth/login" -H "Content-Type: application/json" -d '{"email":"cashier2@sme.com","password":"cashier123"}')
CASHIER_TOKEN=$(echo $CASHIER_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$CASHIER_TOKEN" ]; then
    echo -e "${YELLOW}⚠️  Cashier login failed (may not exist yet)${NC}"
    CASHIER_TOKEN=""
else
    echo -e "${GREEN}✅ Cashier logged in${NC}"
fi

# ===================================================================
# WORKFLOW 1: Complete AR Invoice → Payment Flow
# ===================================================================
echo -e "\n${CYAN}======================================================================${NC}"
echo -e "${CYAN}📋 WORKFLOW 1: AR Invoice → Post → Payment → Reconciliation${NC}"
echo -e "${CYAN}======================================================================${NC}\n"

# Step 1: Get customer for invoice
echo -e "${YELLOW}Step 1.1: Get Customer ID${NC}"
CUSTOMERS=$(curl -s -L -H "Authorization: Bearer $ADMIN_TOKEN" "http://localhost:8000/api/v1/customers?limit=1")
CUSTOMER_ID=$(echo $CUSTOMERS | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)

if [ -z "$CUSTOMER_ID" ]; then
    echo -e "${RED}❌ No customers found! Creating one...${NC}"
    # Create customer
    CUSTOMER_BODY='{"name":"Test Customer LLC","email":"test@customer.com","phone":"0123456789","tax_code":"TEST001"}'
    NEW_CUSTOMER=$(curl -s -L -X POST -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" -d "$CUSTOMER_BODY" "http://localhost:8000/api/v1/customers")
    CUSTOMER_ID=$(echo $NEW_CUSTOMER | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)
fi
echo -e "${GREEN}✅ Customer ID: $CUSTOMER_ID${NC}"

# Step 2: Create draft invoice
echo -e "\n${YELLOW}Step 1.2: Create Draft Invoice${NC}"
INVOICE_BODY=$(cat <<EOF
{
  "invoice_no": "INV-WORKFLOW-$(date +%Y%m%d%H%M%S)",
  "customer_id": $CUSTOMER_ID,
  "issue_date": "$(date +%Y-%m-%d)",
  "due_date": "2025-12-31",
  "total_amount": 5000000,
  "notes": "E2E Workflow Test Invoice"
}
EOF
)

CREATE_INVOICE=$(curl -s -L -X POST -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" -d "$INVOICE_BODY" "http://localhost:8000/api/v1/invoices")
INVOICE_ID=$(echo $CREATE_INVOICE | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)

if [ -z "$INVOICE_ID" ]; then
    echo -e "${RED}❌ Failed to create invoice${NC}"
    echo "$CREATE_INVOICE"
else
    echo -e "${GREEN}✅ Invoice created: ID=$INVOICE_ID${NC}"
fi

# Step 3: Post invoice (draft → posted)
echo -e "\n${YELLOW}Step 1.3: Post Invoice (Change status to 'posted')${NC}"
POST_INVOICE=$(curl -s -L -X POST -H "Authorization: Bearer $ADMIN_TOKEN" "http://localhost:8000/api/v1/invoices/$INVOICE_ID/post")
INVOICE_STATUS=$(echo $POST_INVOICE | grep -o '"status":"[^"]*' | cut -d'"' -f4)

if [ "$INVOICE_STATUS" == "posted" ]; then
    echo -e "${GREEN}✅ Invoice posted successfully${NC}"
else
    echo -e "${RED}❌ Failed to post invoice. Status: $INVOICE_STATUS${NC}"
fi

# Step 4: Get bank account for payment
echo -e "\n${YELLOW}Step 1.4: Get Bank Account ID${NC}"
ACCOUNTS=$(curl -s -L -H "Authorization: Bearer $ADMIN_TOKEN" "http://localhost:8000/api/v1/accounts?limit=10")
BANK_ACCOUNT_ID=$(echo $ACCOUNTS | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)

if [ -z "$BANK_ACCOUNT_ID" ]; then
    echo -e "${RED}❌ No accounts found!${NC}"
else
    echo -e "${GREEN}✅ Bank Account ID: $BANK_ACCOUNT_ID${NC}"
fi

# Step 5: Create payment with allocation
echo -e "\n${YELLOW}Step 1.5: Create Payment with Invoice Allocation${NC}"
PAYMENT_BODY=$(cat <<EOF
{
  "transaction_date": "$(date +%Y-%m-%d)",
  "amount": 2000000,
  "payment_method": "bank_transfer",
  "account_id": $BANK_ACCOUNT_ID,
  "reference_no": "PAY-WORKFLOW-$(date +%Y%m%d%H%M%S)",
  "notes": "E2E Workflow Test Payment",
  "allocations": [{
    "ar_invoice_id": $INVOICE_ID,
    "allocated_amount": 2000000
  }]
}
EOF
)

CREATE_PAYMENT=$(curl -s -L -X POST -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" -d "$PAYMENT_BODY" "http://localhost:8000/api/v1/payments")
PAYMENT_ID=$(echo $CREATE_PAYMENT | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)

if [ -z "$PAYMENT_ID" ]; then
    echo -e "${RED}❌ Failed to create payment${NC}"
    echo "$CREATE_PAYMENT"
else
    echo -e "${GREEN}✅ Payment created: ID=$PAYMENT_ID, Amount=2,000,000 VND${NC}"
fi

# Step 6: Verify invoice updated to partial
echo -e "\n${YELLOW}Step 1.6: Verify Invoice Status Updated${NC}"
UPDATED_INVOICE=$(curl -s -H "Authorization: Bearer $ADMIN_TOKEN" "http://localhost:8000/api/v1/invoices/$INVOICE_ID")
UPDATED_STATUS=$(echo $UPDATED_INVOICE | grep -o '"status":"[^"]*' | cut -d'"' -f4)
PAID_AMOUNT=$(echo $UPDATED_INVOICE | grep -o '"paid_amount":[0-9.]*' | cut -d: -f2)
REMAINING=$(echo $UPDATED_INVOICE | grep -o '"remaining_amount":[0-9.]*' | cut -d: -f2)

echo -e "  Status: ${CYAN}$UPDATED_STATUS${NC}"
echo -e "  Paid: ${CYAN}${PAID_AMOUNT:-0} VND${NC}"
echo -e "  Remaining: ${CYAN}${REMAINING:-0} VND${NC}"

if [ "$UPDATED_STATUS" == "partial" ]; then
    echo -e "${GREEN}✅ Invoice correctly updated to 'partial' status${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ Expected 'partial', got '$UPDATED_STATUS'${NC}"
    ((TESTS_FAILED++))
fi

# Step 7: Check reconciliation KPI
echo -e "\n${YELLOW}Step 1.7: Verify Reconciliation KPI${NC}"
RECON=$(curl -s -H "Authorization: Bearer $ADMIN_TOKEN" "http://localhost:8000/api/v1/analytics/kpi/reconciliation")
echo "$RECON" | head -c 500
echo -e "\n${GREEN}✅ Reconciliation data retrieved${NC}"

# ===================================================================
# WORKFLOW 2: RBAC Testing
# ===================================================================
echo -e "\n${CYAN}======================================================================${NC}"
echo -e "${CYAN}🔒 WORKFLOW 2: Role-Based Access Control (RBAC) Testing${NC}"
echo -e "${CYAN}======================================================================${NC}\n"

# Create a test invoice for RBAC testing
echo -e "${YELLOW}Setup: Creating test invoice for RBAC tests${NC}"
if [ -z "$CUSTOMER_ID" ]; then
    CUSTOMER_BODY='{"name":"RBAC Test Customer","email":"rbac@test.com","phone":"0987654321","tax_code":"RBAC001"}'
    NEW_CUSTOMER=$(curl -s -L -X POST -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" -d "$CUSTOMER_BODY" "http://localhost:8000/api/v1/customers")
    CUSTOMER_ID=$(echo $NEW_CUSTOMER | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)
fi

RBAC_INVOICE_BODY=$(cat <<EOF
{
  "invoice_no": "INV-RBAC-$(date +%Y%m%d%H%M%S)",
  "customer_id": $CUSTOMER_ID,
  "issue_date": "$(date +%Y-%m-%d)",
  "due_date": "2025-12-31",
  "total_amount": 500000,
  "notes": "RBAC Test Invoice"
}
EOF
)
RBAC_INVOICE=$(curl -s -L -X POST -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" -d "$RBAC_INVOICE_BODY" "http://localhost:8000/api/v1/invoices")
RBAC_INVOICE_ID=$(echo $RBAC_INVOICE | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)
echo -e "${GREEN}✅ Test Invoice ID: $RBAC_INVOICE_ID${NC}\n"

# Test 2.1: Cashier CANNOT post invoice (403)
if [ ! -z "$CASHIER_TOKEN" ] && [ ! -z "$RBAC_INVOICE_ID" ]; then
    echo -e "${YELLOW}Test 2.1: Cashier tries to post invoice (should FAIL)${NC}"
    CASHIER_POST=$(curl -s -L -w "\n%{http_code}" -X POST -H "Authorization: Bearer $CASHIER_TOKEN" "http://localhost:8000/api/v1/invoices/$RBAC_INVOICE_ID/post")
    CASHIER_CODE=$(echo "$CASHIER_POST" | tail -n1)
    
    if [ "$CASHIER_CODE" == "403" ] || [ "$CASHIER_CODE" == "401" ]; then
        echo -e "${GREEN}✅ PASS - Cashier correctly denied (HTTP $CASHIER_CODE)${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ FAIL - Cashier was allowed! (HTTP $CASHIER_CODE)${NC}"
        ((TESTS_FAILED++))
    fi
else
    echo -e "${YELLOW}⚠️  Skip - No cashier account${NC}"
fi

# Test 2.2: Accountant CAN create invoice
if [ ! -z "$ACCOUNTANT_TOKEN" ]; then
    echo -e "\n${YELLOW}Test 2.2: Accountant creates invoice (should PASS)${NC}"
    ACC_INVOICE_BODY=$(cat <<EOF
{
  "invoice_no": "INV-ACC-$(date +%Y%m%d%H%M%S)",
  "customer_id": $CUSTOMER_ID,
  "issue_date": "$(date +%Y-%m-%d)",
  "due_date": "2025-12-31",
  "total_amount": 1000000,
  "notes": "Accountant RBAC Test"
}
EOF
)
    
    ACC_CREATE=$(curl -s -w "\n%{http_code}" -X POST -H "Authorization: Bearer $ACCOUNTANT_TOKEN" -H "Content-Type: application/json" -d "$ACC_INVOICE_BODY" "http://localhost:8000/api/v1/invoices")
    ACC_CODE=$(echo "$ACC_CREATE" | tail -n1)
    
    if [ "$ACC_CODE" == "201" ]; then
        echo -e "${GREEN}✅ PASS - Accountant created invoice (HTTP $ACC_CODE)${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ FAIL - Accountant denied (HTTP $ACC_CODE)${NC}"
        ((TESTS_FAILED++))
    fi
else
    echo -e "${YELLOW}⚠️  Skip - No accountant account${NC}"
fi

# Test 2.3: Cashier CANNOT update organization settings
if [ ! -z "$CASHIER_TOKEN" ]; then
    echo -e "\n${YELLOW}Test 2.3: Cashier tries to update settings (should FAIL)${NC}"
    SETTINGS_BODY='{"name":"Hacked Company"}'
    CASHIER_SETTINGS=$(curl -s -w "\n%{http_code}" -X PUT -H "Authorization: Bearer $CASHIER_TOKEN" -H "Content-Type: application/json" -d "$SETTINGS_BODY" "http://localhost:8000/api/v1/settings")
    CASHIER_SETTINGS_CODE=$(echo "$CASHIER_SETTINGS" | tail -n1)
    
    if [ "$CASHIER_SETTINGS_CODE" == "403" ]; then
        echo -e "${GREEN}✅ PASS - Cashier correctly denied (HTTP $CASHIER_SETTINGS_CODE)${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ FAIL - Cashier was allowed! (HTTP $CASHIER_SETTINGS_CODE)${NC}"
        ((TESTS_FAILED++))
    fi
else
    echo -e "${YELLOW}⚠️  Skip - No cashier account${NC}"
fi

# Test 2.4: Admin CAN update settings
echo -e "\n${YELLOW}Test 2.4: Admin updates settings (should PASS)${NC}"
ADMIN_SETTINGS_BODY='{"tax_code":"9999999999"}'
ADMIN_SETTINGS=$(curl -s -w "\n%{http_code}" -X PUT -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" -d "$ADMIN_SETTINGS_BODY" "http://localhost:8000/api/v1/settings")
ADMIN_SETTINGS_CODE=$(echo "$ADMIN_SETTINGS" | tail -n1)

if [ "$ADMIN_SETTINGS_CODE" == "200" ]; then
    echo -e "${GREEN}✅ PASS - Admin updated settings (HTTP $ADMIN_SETTINGS_CODE)${NC}"
    ((TESTS_PASSED++))
    
    # Revert change
    REVERT='{"tax_code":"1234567890"}'
    curl -s -X PUT -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" -d "$REVERT" "http://localhost:8000/api/v1/settings" > /dev/null
    echo -e "  ${CYAN}(Settings reverted)${NC}"
else
    echo -e "${RED}❌ FAIL - Admin denied (HTTP $ADMIN_SETTINGS_CODE)${NC}"
    ((TESTS_FAILED++))
fi

# ===================================================================
# SUMMARY
# ===================================================================
echo -e "\n${CYAN}======================================================================${NC}"
echo -e "${CYAN}📊 TEST SUMMARY${NC}"
echo -e "${CYAN}======================================================================${NC}\n"

TOTAL=$((TESTS_PASSED + TESTS_FAILED))
SUCCESS_RATE=$(awk "BEGIN {printf \"%.2f\", ($TESTS_PASSED / $TOTAL) * 100}")

echo -e "Total Tests: ${YELLOW}$TOTAL${NC}"
echo -e "✅ Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "❌ Failed: ${RED}$TESTS_FAILED${NC}"
echo -e "Success Rate: ${YELLOW}$SUCCESS_RATE%${NC}\n"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL TESTS PASSED!${NC}\n"
    exit 0
else
    echo -e "${RED}⚠️  SOME TESTS FAILED${NC}\n"
    exit 1
fi
