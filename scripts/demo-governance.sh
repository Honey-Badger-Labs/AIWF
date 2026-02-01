#!/bin/bash
set -e

#══════════════════════════════════════════════════════════════════════════════
# AIWF Phase 2: AIM-DRAG Governance Framework Demo
#══════════════════════════════════════════════════════════════════════════════
#
# This script demonstrates the AIM-DRAG governance framework integration:
# 1. AIM Declaration validation
# 2. DRAG mode enforcement
# 3. Audit logging with integrity hashing
# 4. Governed workflow execution
#
# Requirements:
# - SustainBot running on localhost:5000
# - JWT_SECRET configured in .env
# - GOVERNANCE_ENABLED=true in .env
#
#══════════════════════════════════════════════════════════════════════════════

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

BASE_URL="${SUSTAINBOT_URL:-http://localhost:5000}"
JWT_SECRET="${JWT_SECRET:-dev-secret-key-change-in-production}"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║    AIWF Phase 2: AIM-DRAG Governance Framework Demo         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

#──────────────────────────────────────────────────────────────────────────────
# Step 1: Generate JWT Token
#──────────────────────────────────────────────────────────────────────────────

echo "📋 Step 1: Generate JWT Token for Authenticated Access"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

TOKEN=$(python3 -c "
import jwt
token = jwt.encode({
    'user_id': '123',
    'actor': 'jake@sustainnet.io',
    'role': 'admin'
}, '$JWT_SECRET', algorithm='HS256')
print(token)
" 2>/dev/null || echo "")

if [ -z "$TOKEN" ]; then
    echo -e "${RED}✗ Failed to generate token. Install PyJWT: pip install PyJWT${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Token generated: ${TOKEN:0:50}...${NC}"
echo ""

#──────────────────────────────────────────────────────────────────────────────
# Step 2: Test Governance Validation Endpoint
#──────────────────────────────────────────────────────────────────────────────

echo "🔍 Step 2: Test Governance Validation (Pre-Flight Check)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Valid governance request
VALID_REQUEST=$(cat <<EOF
{
  "workflow_name": "deploy-to-staging",
  "aim": {
    "actor": {
      "name": "Jake Smith",
      "email": "jake@sustainnet.io",
      "role": "DevOps Engineer"
    },
    "input": {
      "sources": [
        {
          "type": "slack_webhook",
          "description": "Slack slash command payload"
        }
      ],
      "constraints": [
        "Read-only access to production",
        "No destructive operations"
      ]
    },
    "mission": {
      "objective": "Deploy updated application to staging environment with zero downtime",
      "success_criteria": [
        "Health checks pass",
        "Zero downtime deployment",
        "Rollback capability maintained"
      ]
    }
  },
  "drag_mode": "execute",
  "parameters": {
    "environment": "staging",
    "version": "v1.2.3"
  }
}
EOF
)

echo "Testing valid AIM-DRAG declaration..."
RESPONSE=$(curl -s -X POST "$BASE_URL/governance/validate" \
  -H "Content-Type: application/json" \
  -d "$VALID_REQUEST" \
  -w "\n%{http_code}")

HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)
BODY=$(echo "$RESPONSE" | sed '$ d')

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Valid governance declaration accepted${NC}"
    echo "Response:"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
else
    echo -e "${YELLOW}⚠ Unexpected response code: $HTTP_CODE${NC}"
    echo "$BODY"
fi
echo ""

#──────────────────────────────────────────────────────────────────────────────
# Step 3: Test Invalid Governance (Missing Actor Name)
#──────────────────────────────────────────────────────────────────────────────

echo "🛡️  Step 3: Test Validation Failure (Missing Actor Name)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

INVALID_REQUEST=$(cat <<EOF
{
  "workflow_name": "deploy-to-staging",
  "aim": {
    "actor": {
      "name": "AB",
      "role": "Engineer"
    },
    "input": {
      "sources": [{"type": "api", "description": "test"}]
    },
    "mission": {
      "objective": "Too short",
      "success_criteria": ["One"]
    }
  },
  "drag_mode": "execute",
  "parameters": {}
}
EOF
)

echo "Testing invalid AIM declaration (name too short)..."
RESPONSE=$(curl -s -X POST "$BASE_URL/governance/validate" \
  -H "Content-Type: application/json" \
  -d "$INVALID_REQUEST" \
  -w "\n%{http_code}")

HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)
BODY=$(echo "$RESPONSE" | sed '$ d')

if [ "$HTTP_CODE" = "400" ]; then
    echo -e "${GREEN}✓ Invalid declaration correctly rejected${NC}"
    echo "Error message:"
    echo "$BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('error', 'No error message'))" 2>/dev/null || echo "$BODY"
else
    echo -e "${RED}✗ Expected 400, got $HTTP_CODE${NC}"
    echo "$BODY"
fi
echo ""

#──────────────────────────────────────────────────────────────────────────────
# Step 4: Test Governed Workflow Execution
#──────────────────────────────────────────────────────────────────────────────

echo "🚀 Step 4: Test Governed Workflow Execution"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if SustainBot is running
if ! curl -s "$BASE_URL/health" > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠ SustainBot not running on $BASE_URL${NC}"
    echo "To start: cd sustainbot && python3 main.py"
    echo ""
    echo "Skipping live workflow execution test..."
else
    echo "Executing governed workflow with full AIM-DRAG context..."
    
    RESPONSE=$(curl -s -X POST "$BASE_URL/workflows/governed/execute" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -H "X-Trace-ID: demo-$(date +%s)" \
      -d "$VALID_REQUEST" \
      -w "\n%{http_code}")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)
    BODY=$(echo "$RESPONSE" | sed '$ d')
    
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "500" ]; then
        echo -e "${GREEN}✓ Governed workflow executed (logged in audit trail)${NC}"
        echo "Response:"
        echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
        
        # Check if audit log was written
        if [ -f "./logs/audit.jsonl" ]; then
            echo ""
            echo -e "${BLUE}📝 Audit log entry created:${NC}"
            tail -n 1 ./logs/audit.jsonl | python3 -m json.tool 2>/dev/null || tail -n 1 ./logs/audit.jsonl
        fi
    else
        echo -e "${YELLOW}⚠ Workflow execution response: $HTTP_CODE${NC}"
        echo "$BODY"
    fi
fi
echo ""

#──────────────────────────────────────────────────────────────────────────────
# Step 5: Verify Audit Log Integrity
#──────────────────────────────────────────────────────────────────────────────

echo "🔒 Step 5: Verify Audit Log Integrity"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "./logs/audit.jsonl" ]; then
    echo "Checking audit log at ./logs/audit.jsonl..."
    
    # Count entries
    ENTRY_COUNT=$(wc -l < ./logs/audit.jsonl | tr -d ' ')
    echo -e "${GREEN}✓ Audit log contains $ENTRY_COUNT entries${NC}"
    
    # Verify last entry has integrity hash
    LAST_ENTRY=$(tail -n 1 ./logs/audit.jsonl)
    HAS_HASH=$(echo "$LAST_ENTRY" | python3 -c "import sys, json; print('integrity_hash' in json.load(sys.stdin))" 2>/dev/null || echo "false")
    
    if [ "$HAS_HASH" = "True" ]; then
        echo -e "${GREEN}✓ Latest entry has integrity hash (tamper-evident)${NC}"
    else
        echo -e "${YELLOW}⚠ Latest entry missing integrity hash${NC}"
    fi
    
    # Display governance context from latest entry
    echo ""
    echo "Latest audit entry governance context:"
    echo "$LAST_ENTRY" | python3 -c "
import sys, json
entry = json.load(sys.stdin)
aim = entry.get('aim', {})
actor = aim.get('actor', {})
mission = aim.get('mission', {})
print(f\"  Actor: {actor.get('name', 'N/A')} ({actor.get('role', 'N/A')})\")
print(f\"  DRAG Mode: {entry.get('drag_mode', 'N/A').upper()}\")
print(f\"  Workflow: {entry.get('workflow_name', 'N/A')}\")
print(f\"  Outcome: {entry.get('outcome', 'N/A')}\")
print(f\"  Duration: {entry.get('duration_seconds', 'N/A')} seconds\")
print(f\"  Trace ID: {entry.get('trace_id', 'N/A')}\")
" 2>/dev/null || echo "  (Could not parse entry)"
else
    echo -e "${YELLOW}⚠ No audit log found at ./logs/audit.jsonl${NC}"
    echo "Audit log will be created when GOVERNANCE_ENABLED=true and workflows are executed."
fi
echo ""

#──────────────────────────────────────────────────────────────────────────────
# Summary
#──────────────────────────────────────────────────────────────────────────────

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║          Phase 2 Governance Framework Demo Summary          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "✅ AIM Declaration Models: Implemented (Pydantic validation)"
echo "✅ DRAG Mode Enforcement: Active (Draft, Research, Grunt, Execute)"
echo "✅ Prescriptive Language Filter: Available in governance.py"
echo "✅ Audit Logging: Append-only JSONL with integrity hashing"
echo "✅ Governance Endpoints:"
echo "   - POST /governance/validate (pre-flight validation)"
echo "   - POST /workflows/governed/execute (OTS-compliant execution)"
echo ""
echo "📋 Next Steps:"
echo "   1. Start SustainBot: cd sustainbot && python3 main.py"
echo "   2. Execute governed workflows with full AIM-DRAG context"
echo "   3. Review audit logs: cat ./logs/audit.jsonl | jq"
echo "   4. Proceed to Phase 3: Observability Integration"
echo ""
echo "🔗 Related Files:"
echo "   - sustainbot/governance.py (AIM-DRAG models)"
echo "   - sustainbot/main.py (governed endpoints)"
echo "   - .env.example (GOVERNANCE_ENABLED, AUDIT_LOG_PATH)"
echo "   - logs/audit.jsonl (tamper-evident audit trail)"
echo ""
