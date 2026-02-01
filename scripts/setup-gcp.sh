#!/bin/bash
# Setup script for AIWF

set -e

echo "🚀 AIWF Setup Script"
echo "==================="

# Check prerequisites
echo "Checking prerequisites..."
command -v gcloud >/dev/null 2>&1 || { echo "gcloud CLI not found"; exit 1; }
command -v terraform >/dev/null 2>&1 || { echo "Terraform not found"; exit 1; }

# Create GCP Project
echo ""
echo "Creating GCP project..."
read -p "Enter project ID: " PROJECT_ID
read -p "Enter project name: " PROJECT_NAME

gcloud projects create "$PROJECT_ID" --name="$PROJECT_NAME"
gcloud config set project "$PROJECT_ID"

# Enable APIs
echo ""
echo "Enabling required APIs..."
gcloud services enable compute.googleapis.com
gcloud services enable iam.googleapis.com

# Create Service Account
echo ""
echo "Creating service account..."
gcloud iam service-accounts create aiwf-service-account \
  --display-name="AIWF Service Account"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:aiwf-service-account@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/compute.admin"

# Export Credentials
echo ""
echo "Exporting service account key..."
gcloud iam service-accounts keys create sa-key.json \
  --iam-account="aiwf-service-account@$PROJECT_ID.iam.gserviceaccount.com"

echo ""
echo "✅ GCP Setup Complete!"
echo ""
echo "Next steps:"
echo "1. Base64 encode the service account key:"
echo "   base64 -w 0 sa-key.json"
echo ""
echo "2. Add to GitHub secrets:"
echo "   GCP_PROJECT_ID=$PROJECT_ID"
echo "   GCP_SERVICE_ACCOUNT_KEY=<base64-encoded-key>"
echo "   GCP_ZONE=us-central1-a"
