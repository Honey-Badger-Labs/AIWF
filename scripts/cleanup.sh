#!/bin/bash
# Cleanup AIWF resources

set -e

echo "🧹 Cleaning up AIWF Resources"
echo "============================="

read -p "This will delete all AIWF resources. Continue? (y/N) " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Destroying Terraform resources..."
    cd terraform
    terraform destroy -auto-approve
    cd ..
    
    echo ""
    echo "✅ Cleanup complete!"
    echo ""
    echo "Note: Some resources (like firewall rules) may remain. Clean them up manually if needed."
else
    echo "Cleanup cancelled."
fi
