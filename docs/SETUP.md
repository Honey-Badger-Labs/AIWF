# AIWF Setup Guide

## Quick Start

### 1. Prerequisites

- GitHub account with organization access
- GCP account (free tier eligible)
- Slack workspace admin access
- gcloud CLI installed
- Terraform installed (1.7.0+)

### 2. GitHub Secrets Setup

Add the following secrets to your GitHub repository:

```bash
# GCP Authentication
GCP_PROJECT_ID
GCP_SERVICE_ACCOUNT_KEY  # (base64 encoded JSON)
GCP_ZONE                 # e.g., us-central1-a

# Slack Integration
SLACK_WEBHOOK_URL
SLACK_BOT_TOKEN
SLACK_CHANNEL_ID
```

### 3. GCP Service Account Setup

```bash
# Generate service account key
gcloud iam service-accounts keys create sa-key.json \
  --iam-account=aiwf-sa@YOUR_PROJECT.iam.gserviceaccount.com

# Base64 encode for GitHub secret
base64 -w 0 sa-key.json
```

### 4. Trigger Deployment

```bash
git push origin main
```

Or manually trigger via GitHub Actions:

```bash
gh workflow run deploy-infrastructure.yml
```

## Environment Variables

Create a `.env` file in the root directory:

```bash
# GCP
GCP_PROJECT_ID=your-project-id
GCP_REGION=us-central1
GCP_ZONE=us-central1-a
GCP_MACHINE_TYPE=e2-micro

# OpenClaw
OPENCLAW_URL=http://localhost:8080
OPENCLAW_ADMIN_USER=admin
OPENCLAW_ADMIN_PASSWORD=changeme

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C...

# LLM
LLM_MODEL=llama2
LLM_HOST=localhost
LLM_PORT=11434

# SustainBot
WORKFLOWS_DIR=./workflows
```

## Workflow Execution

### List Available Workflows

```bash
gcloud compute ssh aiwf-compute-1 --zone=us-central1-a \
  --command='curl http://localhost:5000/workflows'
```

### Run a Workflow

```bash
gcloud compute ssh aiwf-compute-1 --zone=us-central1-a \
  --command='curl -X POST http://localhost:5000/workflows/my-workflow/execute'
```

### Check System Status

```bash
gcloud compute ssh aiwf-compute-1 --zone=us-central1-a \
  --command='curl http://localhost:5000/health'
```

## Troubleshooting

### GCP Authentication Failed

```bash
# Re-encode service account key
base64 -w 0 sa-key.json > /tmp/sa.b64
# Copy to GitHub secrets as GCP_SERVICE_ACCOUNT_KEY
```

### OpenClaw Not Starting

```bash
# SSH to instance
gcloud compute ssh aiwf-compute-1 --zone=us-central1-a

# Check Docker
sudo systemctl status docker

# Check OpenClaw logs
docker logs openclaw

# Verify port 8080 is open
curl -s http://localhost:8080/health
```

### SustainBot Not Responding

```bash
# Check if service is running
curl http://localhost:5000/health

# Check logs
tail -f /var/log/aiwf-init.log
```

## Cost Monitoring

GCP Free Tier includes:
- 1 x e2-micro VM (730 hours/month)
- 30GB storage
- 1TB inbound traffic
- 1GB outbound traffic/month

Monitor usage:

```bash
gcloud compute instances list --filter="name:aiwf-*"
gcloud compute resource-settings describe
```
