#!/bin/bash
# Demo script to test AIWF authentication and security features

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║       AIWF Phase 1 Security Features Demo                   ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Set JWT secret for demo
export JWT_SECRET="demo-secret-key-for-testing"

# Function to generate JWT token
generate_token() {
    python3 << EOF
import jwt
import json

payload = {
    "user_id": "demo-user-123",
    "actor": "jake@sustainnet.io",
    "role": "developer"
}

token = jwt.encode(payload, "$JWT_SECRET", algorithm="HS256")
print(token)
EOF
}

echo "📋 Step 1: Generate JWT Token"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TOKEN=$(generate_token)
echo -e "${GREEN}✓ Token generated: ${TOKEN:0:50}...${NC}"
echo ""

echo "🔒 Step 2: Test Authentication (Should Fail Without Token)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Request: GET /workflows (no auth header)"
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" http://localhost:5000/workflows 2>/dev/null || echo "Connection refused - SustainBot not running")
if [[ "$RESPONSE" == *"Connection refused"* ]]; then
    echo -e "${YELLOW}⚠  SustainBot not running at localhost:5000${NC}"
    echo "   Start with: cd sustainbot && python3 main.py"
else
    HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)
    if [ "$HTTP_STATUS" == "401" ]; then
        echo -e "${GREEN}✓ Correctly rejected (401 Unauthorized)${NC}"
    else
        echo -e "${RED}✗ Expected 401, got $HTTP_STATUS${NC}"
    fi
fi
echo ""

echo "✅ Step 3: Test Authentication (Should Succeed With Token)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Request: GET /workflows (with Bearer token)"
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
    -H "Authorization: Bearer $TOKEN" \
    http://localhost:5000/workflows 2>/dev/null || echo "Connection refused")
if [[ "$RESPONSE" == *"Connection refused"* ]]; then
    echo -e "${YELLOW}⚠  SustainBot not running${NC}"
else
    HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)
    if [ "$HTTP_STATUS" == "200" ]; then
        echo -e "${GREEN}✓ Successfully authenticated (200 OK)${NC}"
        BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS/d')
        echo "   Response: $BODY"
    else
        echo -e "${RED}✗ Expected 200, got $HTTP_STATUS${NC}"
    fi
fi
echo ""

echo "🛡️  Step 4: Test Input Validation (Path Traversal Prevention)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Request: POST /workflows/../etc/passwd/execute (malicious path)"
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
    -X POST \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"test": "data"}' \
    http://localhost:5000/workflows/../etc/passwd/execute 2>/dev/null || echo "Connection refused")
if [[ "$RESPONSE" == *"Connection refused"* ]]; then
    echo -e "${YELLOW}⚠  SustainBot not running${NC}"
else
    HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)
    if [ "$HTTP_STATUS" == "400" ] || [ "$HTTP_STATUS" == "404" ]; then
        echo -e "${GREEN}✓ Path traversal blocked (${HTTP_STATUS})${NC}"
        BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS/d')
        echo "   Response: $BODY"
    else
        echo -e "${RED}✗ Path traversal not blocked! Got $HTTP_STATUS${NC}"
    fi
fi
echo ""

echo "📊 Step 5: Test Health Check (No Auth Required)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Request: GET /health"
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
    http://localhost:5000/health 2>/dev/null || echo "Connection refused")
if [[ "$RESPONSE" == *"Connection refused"* ]]; then
    echo -e "${YELLOW}⚠  SustainBot not running${NC}"
else
    HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)
    if [ "$HTTP_STATUS" == "200" ]; then
        echo -e "${GREEN}✓ Health check accessible without auth (200 OK)${NC}"
        BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS/d')
        echo "   Status: $(echo $BODY | jq -r '.status' 2>/dev/null || echo 'healthy')"
    else
        echo -e "${RED}✗ Expected 200, got $HTTP_STATUS${NC}"
    fi
fi
echo ""

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║             Phase 1 Security Features Summary               ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "✅ JWT Authentication: Implemented"
echo "✅ Input Validation: Path traversal prevention"
echo "✅ Slack Verification: HMAC signature verification ready"
echo "✅ Error Handling: Custom exceptions with error codes"
echo "✅ Global Error Handlers: 404/500 errors"
echo ""
echo "📋 Next Steps:"
echo "   1. Start SustainBot: cd sustainbot && python3 main.py --init"
echo "   2. Test with: export SUSTAINBOT_TOKEN=\$(generate_token)"
echo "   3. Make requests: curl -H \"Authorization: Bearer \$SUSTAINBOT_TOKEN\" ..."
echo ""
echo "🔗 Related Files:"
echo "   - sustainbot/main.py (JWT auth, validation, error handling)"
echo "   - terraform/main.tf (SSH restriction)"
echo "   - terraform/variables.tf (developer_ips variable)"
echo "   - .env.example (JWT_SECRET, SLACK_SIGNING_SECRET)"
echo ""
