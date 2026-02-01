#!/bin/bash

# ============================================================================
# AIWF Phase 3: Observability Demo Script
# ============================================================================
#
# Demonstrates governance observability features:
# 1. Prometheus metrics exposure
# 2. Structured JSON logging
# 3. CloudWatch integration (optional)
# 4. Grafana dashboard preview
#
# Prerequisites:
#   - SustainBot running (python3 sustainbot/main.py)
#   - Valid JWT token
#
# Usage:
#   ./scripts/demo-observability.sh
#
# ============================================================================

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SUSTAINBOT_URL="http://localhost:5000"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║    AIWF Phase 3: Observability Integration Demo             ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================================
# Step 1: Check Prometheus Metrics Endpoint
# ============================================================================

echo -e "${GREEN}📊 Step 1: Prometheus Metrics Endpoint${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "Fetching Prometheus metrics from /metrics endpoint..."
echo ""

METRICS=$(curl -s "$SUSTAINBOT_URL/metrics" 2>&1 || true)

if echo "$METRICS" | grep -q "sustainbot_"; then
    echo -e "${GREEN}✓ Metrics endpoint responding${NC}"
    echo ""
    echo -e "${YELLOW}Sample Metrics:${NC}"
    echo "$METRICS" | grep "sustainbot_" | head -15
    echo "..."
    echo ""
    
    # Count metrics
    METRIC_COUNT=$(echo "$METRICS" | grep "^sustainbot_" | wc -l | tr -d ' ')
    echo -e "${GREEN}Total governance metrics: $METRIC_COUNT${NC}"
else
    echo -e "${RED}✗ Failed to fetch metrics${NC}"
    echo -e "${YELLOW}Response: $METRICS${NC}"
fi

echo ""

# ============================================================================
# Step 2: Generate JWT Token
# ============================================================================

echo -e "${GREEN}🔑 Step 2: Generate JWT Token for Authenticated Access${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

JWT_TOKEN=$(python3 << 'EOF'
import jwt
import os
from datetime import datetime, timedelta

secret = os.getenv('JWT_SECRET', 'dev-secret-key-change-in-production')
payload = {
    'user_id': 'demo-user',
    'actor': 'Demo User',
    'role': 'admin',
    'exp': datetime.utcnow() + timedelta(hours=1)
}
token = jwt.encode(payload, secret, algorithm='HS256')
print(token)
EOF
)

echo -e "${GREEN}✓ Token generated: ${JWT_TOKEN:0:50}...${NC}"
echo ""

# ============================================================================
# Step 3: Execute Governed Workflow (Generate Metrics)
# ============================================================================

echo -e "${GREEN}🚀 Step 3: Execute Governed Workflow (Generate Metrics)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "Executing workflow with full AIM-DRAG context..."
echo ""

WORKFLOW_RESPONSE=$(curl -s -X POST "$SUSTAINBOT_URL/workflows/governed/execute" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Trace-ID: demo-$(date +%s)" \
  -d '{
    "workflow_name": "demo_observability",
    "aim": {
      "actor": {
        "name": "Demo User",
        "email": "demo@example.com",
        "role": "SRE"
      },
      "input": {
        "sources": [
          {"type": "manual", "description": "Observability demo execution"}
        ],
        "constraints": ["Demo only", "No production impact"]
      },
      "mission": {
        "objective": "Demonstrate observability features",
        "success_criteria": ["Metrics generated", "Logs captured", "Audit trail created"]
      }
    },
    "drag_mode": "execute",
    "parameters": {
      "demo": true
    }
  }' 2>&1 || true)

if echo "$WORKFLOW_RESPONSE" | grep -q "trace_id"; then
    echo -e "${GREEN}✓ Workflow executed${NC}"
    echo ""
    echo -e "${YELLOW}Response:${NC}"
    echo "$WORKFLOW_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$WORKFLOW_RESPONSE"
else
    echo -e "${YELLOW}⚠ Response: $WORKFLOW_RESPONSE${NC}"
    echo -e "${YELLOW}(This is expected if SustainBot is not running)${NC}"
fi

echo ""

# ============================================================================
# Step 4: Check Updated Metrics
# ============================================================================

echo -e "${GREEN}📈 Step 4: Verify Metrics Updated${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "Checking specific governance metrics..."
echo ""

METRICS_AFTER=$(curl -s "$SUSTAINBOT_URL/metrics" 2>&1 || true)

echo -e "${YELLOW}AIM Governance Requests:${NC}"
echo "$METRICS_AFTER" | grep "sustainbot_aim_requests_total" | head -5 || echo "No data yet"
echo ""

echo -e "${YELLOW}Workflow Executions:${NC}"
echo "$METRICS_AFTER" | grep "sustainbot_workflow_executions_total" | head -5 || echo "No data yet"
echo ""

echo -e "${YELLOW}JWT Validations:${NC}"
echo "$METRICS_AFTER" | grep "sustainbot_jwt_validations_total" || echo "No data yet"
echo ""

# ============================================================================
# Step 5: Check Structured Logs
# ============================================================================

echo -e "${GREEN}📝 Step 5: Structured JSON Logs${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ -f "./logs/sustainbot.jsonl" ]; then
    echo -e "${GREEN}✓ JSON log file found${NC}"
    echo ""
    echo -e "${YELLOW}Latest log entries:${NC}"
    tail -3 ./logs/sustainbot.jsonl | while read line; do
        echo "$line" | python3 -m json.tool 2>/dev/null || echo "$line"
        echo "---"
    done
else
    echo -e "${YELLOW}⚠ JSON log file not found at ./logs/sustainbot.jsonl${NC}"
    echo "Log file will be created when JSON_LOGGING_ENABLED=true"
fi

echo ""

# ============================================================================
# Step 6: Check Audit Logs
# ============================================================================

echo -e "${GREEN}🔒 Step 6: Audit Log Entries${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ -f "./logs/audit.jsonl" ]; then
    AUDIT_COUNT=$(wc -l < ./logs/audit.jsonl | tr -d ' ')
    echo -e "${GREEN}✓ Audit log: $AUDIT_COUNT entries${NC}"
    echo ""
    
    if [ "$AUDIT_COUNT" -gt 0 ]; then
        echo -e "${YELLOW}Latest audit entry:${NC}"
        tail -1 ./logs/audit.jsonl | python3 -m json.tool 2>/dev/null
    fi
else
    echo -e "${YELLOW}⚠ No audit log found${NC}"
    echo "Audit log will be created when GOVERNANCE_ENABLED=true and workflows are executed."
fi

echo ""

# ============================================================================
# Step 7: Grafana Dashboard Preview
# ============================================================================

echo -e "${GREEN}📊 Step 7: Grafana Dashboard${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ -f "./dashboards/governance-observability.json" ]; then
    echo -e "${GREEN}✓ Dashboard definition found${NC}"
    echo ""
    echo -e "${YELLOW}Dashboard Features:${NC}"
    echo "  • AIM Governance Requests (by DRAG Mode)"
    echo "  • AIM Validation Failures (with alerts)"
    echo "  • Workflow Execution Duration (p50, p95, p99)"
    echo "  • Workflow Outcomes (Success vs Failure)"
    echo "  • Audit Log Entries"
    echo "  • JWT Authentication Metrics"
    echo "  • Active HTTP Requests Gauge"
    echo "  • DRAG Mode Distribution Table"
    echo "  • HTTP Request Rate by Endpoint"
    echo "  • Prescriptive Language Detections (with alerts)"
    echo ""
    echo -e "${BLUE}Import into Grafana:${NC}"
    echo "  1. Open Grafana → Dashboards → Import"
    echo "  2. Upload: ./dashboards/governance-observability.json"
    echo "  3. Select Prometheus datasource"
    echo "  4. Click Import"
else
    echo -e "${RED}✗ Dashboard file not found${NC}"
fi

echo ""

# ============================================================================
# Step 8: CloudWatch Integration (Optional)
# ============================================================================

echo -e "${GREEN}☁️  Step 8: CloudWatch Integration${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ -f "./sustainbot/cloudwatch.py" ]; then
    echo -e "${GREEN}✓ CloudWatch module available${NC}"
    echo ""
    echo -e "${YELLOW}To enable CloudWatch:${NC}"
    echo "  1. Set CLOUDWATCH_ENABLED=true in .env"
    echo "  2. Configure AWS credentials (aws configure)"
    echo "  3. Set CLOUDWATCH_NAMESPACE and CLOUDWATCH_REGION"
    echo "  4. Restart SustainBot"
    echo ""
    echo -e "${BLUE}Metrics will be published to:${NC}"
    echo "  Namespace: AIWF/SustainBot"
    echo "  Region: eu-west-1 (configurable)"
    echo "  Dimensions: DRAGMode, ActorRole, WorkflowName, Outcome"
else
    echo -e "${RED}✗ CloudWatch module not found${NC}"
fi

echo ""

# ============================================================================
# Summary
# ============================================================================

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          Phase 3 Observability Integration Summary          ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${GREEN}✅ Prometheus Metrics:${NC} Exposed at /metrics endpoint"
echo -e "${GREEN}✅ Structured Logging:${NC} JSON logs with governance context"
echo -e "${GREEN}✅ Audit Trail:${NC} Tamper-evident JSONL audit log"
echo -e "${GREEN}✅ Grafana Dashboard:${NC} 10 panels with governance insights"
echo -e "${GREEN}✅ CloudWatch Ready:${NC} Optional AWS integration available"
echo ""

echo -e "${BLUE}📋 Next Steps:${NC}"
echo "   1. Start SustainBot: cd sustainbot && python3 main.py"
echo "   2. Execute governed workflows to generate metrics"
echo "   3. Import Grafana dashboard for visualization"
echo "   4. Enable CloudWatch for centralized monitoring"
echo "   5. Proceed to Phase 4: Database Persistence"
echo ""

echo -e "${BLUE}🔗 Related Files:${NC}"
echo "   - sustainbot/metrics.py (Prometheus metrics)"
echo "   - sustainbot/structured_logging.py (JSON logging)"
echo "   - sustainbot/cloudwatch.py (AWS integration)"
echo "   - dashboards/governance-observability.json (Grafana)"
echo "   - .env.example (configuration)"
echo ""
