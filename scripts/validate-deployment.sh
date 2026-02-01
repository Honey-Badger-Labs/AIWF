#!/bin/bash
# Validate AIWF deployment

set -e

echo "🔍 Validating AIWF Deployment"
echo "=============================="

# Get instance IP
INSTANCE_IP=$(gcloud compute instances list --filter="name:aiwf-*" --format="value(EXTERNAL_IP)" | head -1)

if [ -z "$INSTANCE_IP" ]; then
    echo "❌ No AIWF compute instance found"
    exit 1
fi

echo "Instance IP: $INSTANCE_IP"
echo ""

# Check OpenClaw
echo "Checking OpenClaw..."
if curl -s "http://$INSTANCE_IP:8080/health" > /dev/null; then
    echo "✅ OpenClaw: Running"
else
    echo "⚠️  OpenClaw: Not responding (may still be starting)"
fi

# Check SustainBot
echo "Checking SustainBot..."
if curl -s "http://$INSTANCE_IP:5000/health" > /dev/null; then
    echo "✅ SustainBot: Running"
else
    echo "⚠️  SustainBot: Not responding"
fi

# Check SSH access
echo ""
echo "Testing SSH access..."
if gcloud compute ssh aiwf-compute-1 --command='echo OK' > /dev/null 2>&1; then
    echo "✅ SSH: Accessible"
else
    echo "❌ SSH: Not accessible"
fi

echo ""
echo "✅ Validation complete!"
echo ""
echo "Access URLs:"
echo "  OpenClaw: http://$INSTANCE_IP:8080"
echo "  SustainBot: http://$INSTANCE_IP:5000"
