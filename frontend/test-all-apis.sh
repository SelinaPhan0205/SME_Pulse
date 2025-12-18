#!/bin/bash

# ===================================================================
# SME Pulse - Complete API Test Suite
# Test ALL frontend APIs against backend
# ===================================================================

echo ""
echo "🚀 SME PULSE - COMPREHENSIVE API TEST"
echo ""
echo "Testing all frontend API services against backend..."
echo "Skipping: Dashboard analytics APIs (as requested)"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Test results
TOTAL=0
PASSED=0
FAILED=0
declare -a FAILED_TESTS=()

# Function to test API
test_api() {
    local module=$1
    local method=$2
    local endpoint=$3
    local body=$4
    local description=$5
    
    ((TOTAL++))
    
    if [ "$method" == "GET" ]; then
        response=$(curl -s -L -w "\n%{http_code}" -X GET \
            -H "Authorization: Bearer $TOKEN" \
            -H "Content-Type: application/json" \
            "http://localhost:8000$endpoint" 2>/dev/null)
    else
        response=$(curl -s -L -w "\n%{http_code}" -X "$method" \
            -H "Authorization: Bearer $TOKEN" \
            -H "Content-Type: application/json" \
            -d "$body" \
            "http://localhost:8000$endpoint" 2>/dev/null)
    fi
    
    status_code=$(echo "$response" | tail -n1)
    
    if [ "$status_code" -ge 200 ] && [ "$status_code" -lt 300 ]; then
        echo -e "  ${GREEN}✅ $method $endpoint${NC}"
        ((PASSED++))
    else
        echo -e "  ${RED}❌ $method $endpoint [HTTP $status_code]${NC}"
        ((FAILED++))
        FAILED_TESTS+=("$module|$method|$endpoint|$status_code|$description")
    fi
}

# ===================================================================
# Step 1: Login
# ===================================================================
echo -e "${CYAN}🔐 Step 1: Authentication...${NC}"

LOGIN_RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d '{"email":"admin@sme.com","password":"admin123"}' \
    http://localhost:8000/auth/login)

TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo -e "  ${RED}❌ Login failed! Cannot proceed with tests.${NC}"
    exit 1
fi

echo -e "  ${GREEN}✅ Login successful! Token obtained.${NC}"
echo ""

# ===================================================================
# MODULE 1: AUTHENTICATION
# ===================================================================
echo -e "${CYAN}📦 MODULE 1: Authentication${NC}"

test_api "Auth" "GET" "/auth/me" "" "Get current user info"
test_api "Auth" "POST" "/auth/change-password" '{"old_password":"admin123","new_password":"admin123"}' "Change password"
test_api "Auth" "POST" "/auth/forgot-password" '{"email":"admin@sme.com"}' "Forgot password"

echo ""

# ===================================================================
# MODULE 2: USER MANAGEMENT
# ===================================================================
echo -e "${CYAN}📦 MODULE 2: User Management${NC}"

test_api "Users" "GET" "/api/v1/users/?limit=5" "" "List users"
test_api "Users" "GET" "/api/v1/users/1" "" "Get user by ID"

echo ""

# ===================================================================
# MODULE 3: CUSTOMERS
# ===================================================================
echo -e "${CYAN}📦 MODULE 3: Customers${NC}"

test_api "Customers" "GET" "/api/v1/customers/?limit=10" "" "List customers"

# Get first customer
CUSTOMERS=$(curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/v1/customers/?limit=1")
CUSTOMER_ID=$(echo $CUSTOMERS | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)

if [ ! -z "$CUSTOMER_ID" ]; then
    test_api "Customers" "GET" "/api/v1/customers/$CUSTOMER_ID" "" "Get customer by ID"
fi

echo ""

# ===================================================================
# MODULE 4: SUPPLIERS
# ===================================================================
echo -e "${CYAN}📦 MODULE 4: Suppliers${NC}"

test_api "Suppliers" "GET" "/api/v1/suppliers/?limit=10" "" "List suppliers"

# Get first supplier
SUPPLIERS=$(curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/v1/suppliers/?limit=1")
SUPPLIER_ID=$(echo $SUPPLIERS | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)

if [ ! -z "$SUPPLIER_ID" ]; then
    test_api "Suppliers" "GET" "/api/v1/suppliers/$SUPPLIER_ID" "" "Get supplier by ID"
fi

echo ""

# ===================================================================
# MODULE 5: CHART OF ACCOUNTS
# ===================================================================
echo -e "${CYAN}📦 MODULE 5: Chart of Accounts${NC}"

test_api "Accounts" "GET" "/api/v1/accounts/?limit=10" "" "List accounts"

# Get first account
ACCOUNTS=$(curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/v1/accounts/?limit=1")
ACCOUNT_ID=$(echo $ACCOUNTS | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)

if [ ! -z "$ACCOUNT_ID" ]; then
    test_api "Accounts" "GET" "/api/v1/accounts/$ACCOUNT_ID" "" "Get account by ID"
fi

echo ""

# ===================================================================
# MODULE 6: AR INVOICES
# ===================================================================
echo -e "${CYAN}📦 MODULE 6: AR Invoices${NC}"

test_api "Invoices" "GET" "/api/v1/invoices/?limit=10" "" "List AR invoices"

# Get first invoice
INVOICES=$(curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/v1/invoices/?limit=1")
INVOICE_ID=$(echo $INVOICES | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)

if [ ! -z "$INVOICE_ID" ]; then
    test_api "Invoices" "GET" "/api/v1/invoices/$INVOICE_ID" "" "Get invoice by ID"
fi

# Test create & post invoice
if [ ! -z "$CUSTOMER_ID" ]; then
    TIMESTAMP=$(date +%Y%m%d%H%M%S)
    ISSUE_DATE=$(date +%Y-%m-%d)
    DUE_DATE=$(date -d "+30 days" +%Y-%m-%d 2>/dev/null || date -v+30d +%Y-%m-%d)
    
    INVOICE_BODY="{\"invoice_no\":\"TEST-INV-$TIMESTAMP\",\"customer_id\":$CUSTOMER_ID,\"issue_date\":\"$ISSUE_DATE\",\"due_date\":\"$DUE_DATE\",\"total_amount\":999999,\"notes\":\"API Test Invoice\"}"
    
    CREATE_RESPONSE=$(curl -s -L -w "\n%{http_code}" -X POST \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d "$INVOICE_BODY" \
        "http://localhost:8000/api/v1/invoices")
    
    CREATE_STATUS=$(echo "$CREATE_RESPONSE" | tail -n1)
    
    if [ "$CREATE_STATUS" -ge 200 ] && [ "$CREATE_STATUS" -lt 300 ]; then
        echo -e "  ${GREEN}✅ POST /api/v1/invoices/${NC}"
        ((PASSED++))
        ((TOTAL++))
        
        NEW_INVOICE_ID=$(echo "$CREATE_RESPONSE" | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)
        
        if [ ! -z "$NEW_INVOICE_ID" ]; then
            test_api "Invoices" "POST" "/api/v1/invoices/$NEW_INVOICE_ID/post" "" "Post invoice"
            
            # Cleanup
            curl -s -X DELETE \
                -H "Authorization: Bearer $TOKEN" \
                "http://localhost:8000/api/v1/invoices/$NEW_INVOICE_ID" >/dev/null 2>&1
            echo -e "  ${CYAN}🗑️  Cleaned up test invoice${NC}"
        fi
    else
        echo -e "  ${RED}❌ POST /api/v1/invoices/ [HTTP $CREATE_STATUS]${NC}"
        ((FAILED++))
        ((TOTAL++))
    fi
fi

echo ""

# ===================================================================
# MODULE 7: AP BILLS
# ===================================================================
echo -e "${CYAN}📦 MODULE 7: AP Bills${NC}"

test_api "Bills" "GET" "/api/v1/bills/?limit=10" "" "List AP bills"

BILLS=$(curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/v1/bills/?limit=1")
BILL_ID=$(echo $BILLS | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)

if [ ! -z "$BILL_ID" ]; then
    test_api "Bills" "GET" "/api/v1/bills/$BILL_ID" "" "Get bill by ID"
fi

echo ""

# ===================================================================
# MODULE 8: PAYMENTS
# ===================================================================
echo -e "${CYAN}📦 MODULE 8: Payments${NC}"

test_api "Payments" "GET" "/api/v1/payments/?limit=10" "" "List payments"

PAYMENTS=$(curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/v1/payments/?limit=1")
PAYMENT_ID=$(echo $PAYMENTS | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)

if [ ! -z "$PAYMENT_ID" ]; then
    test_api "Payments" "GET" "/api/v1/payments/$PAYMENT_ID" "" "Get payment by ID"
fi

# Test create payment
POSTED_INVOICES=$(curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/v1/invoices/?status=posted&limit=1")
POSTED_INVOICE_ID=$(echo $POSTED_INVOICES | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)

if [ ! -z "$POSTED_INVOICE_ID" ] && [ ! -z "$ACCOUNT_ID" ]; then
    PAYMENT_DATE=$(date +%Y-%m-%d)
    TIMESTAMP=$(date +%Y%m%d%H%M%S)
    
    PAYMENT_BODY="{\"payment_date\":\"$PAYMENT_DATE\",\"amount\":100000,\"payment_method\":\"bank_transfer\",\"account_id\":$ACCOUNT_ID,\"reference_no\":\"TEST-PAY-$TIMESTAMP\",\"notes\":\"API Test Payment\",\"allocations\":[{\"invoice_id\":$POSTED_INVOICE_ID,\"amount\":100000}]}"
    
    PAYMENT_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d "$PAYMENT_BODY" \
        "http://localhost:8000/api/v1/payments/")
    
    PAYMENT_STATUS=$(echo "$PAYMENT_RESPONSE" | tail -n1)
    
    if [ "$PAYMENT_STATUS" -ge 200 ] && [ "$PAYMENT_STATUS" -lt 300 ]; then
        echo -e "  ${GREEN}✅ POST /api/v1/payments/${NC}"
        ((PASSED++))
        ((TOTAL++))
        
        NEW_PAYMENT_ID=$(echo "$PAYMENT_RESPONSE" | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)
        
        if [ ! -z "$NEW_PAYMENT_ID" ]; then
            curl -s -X DELETE \
                -H "Authorization: Bearer $TOKEN" \
                "http://localhost:8000/api/v1/payments/$NEW_PAYMENT_ID" >/dev/null 2>&1
            echo -e "  ${CYAN}🗑️  Cleaned up test payment${NC}"
        fi
    else
        echo -e "  ${RED}❌ POST /api/v1/payments/ [HTTP $PAYMENT_STATUS]${NC}"
        ((FAILED++))
        ((TOTAL++))
    fi
fi

echo ""

# ===================================================================
# MODULE 9: SETTINGS
# ===================================================================
echo -e "${CYAN}📦 MODULE 9: Settings${NC}"

test_api "Settings" "GET" "/api/v1/settings" "" "Get organization settings"

echo ""

# ===================================================================
# MODULE 10: RECONCILIATION
# ===================================================================
echo -e "${CYAN}📦 MODULE 10: Reconciliation${NC}"

test_api "Reconciliation" "GET" "/api/v1/analytics/kpi/reconciliation" "" "Get reconciliation KPI"

echo ""

# ===================================================================
# SUMMARY REPORT
# ===================================================================
echo "======================================================================"
echo -e "${CYAN}📊 TEST SUMMARY REPORT${NC}"
echo "======================================================================"
echo ""
echo "Total Tests: $TOTAL"
echo -e "${GREEN}✅ Passed: $PASSED${NC}"
echo -e "${RED}❌ Failed: $FAILED${NC}"

if [ $TOTAL -gt 0 ]; then
    SUCCESS_RATE=$(awk "BEGIN {printf \"%.2f\", ($PASSED/$TOTAL)*100}")
    echo -e "${YELLOW}Success Rate: $SUCCESS_RATE%${NC}"
fi

echo ""

# Failed endpoints
if [ $FAILED -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}⚠️  FAILED ENDPOINTS (Need Backend Implementation):${NC}"
    echo ""
    for test in "${FAILED_TESTS[@]}"; do
        IFS='|' read -r module method endpoint status_code description <<< "$test"
        echo -e "  ${RED}• $method $endpoint - $description${NC}"
        echo -e "    Status Code: $status_code"
    done
fi

echo ""
echo "======================================================================"
echo -e "${CYAN}✨ Test complete! Check results above.${NC}"
echo "======================================================================"
echo ""
