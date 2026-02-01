# GCP Configuration Guide

## Free Tier Resources

AIWF uses only GCP free tier resources:

- **Compute Engine**: 1 x e2-micro VM (1 vCPU, 1GB RAM)
- **Storage**: 30GB monthly storage free
- **Networking**: Free tier includes:
  - 1 TB inbound data
  - 1 GB outbound data per month

## Setup Steps

### 1. Create GCP Project

```bash
gcloud projects create aiwf-project --name="AIWF"
gcloud config set project aiwf-project
```

### 2. Enable APIs

```bash
gcloud services enable compute.googleapis.com
gcloud services enable iam.googleapis.com
```

### 3. Create Service Account

```bash
gcloud iam service-accounts create aiwf-service-account \
  --display-name="AIWF Service Account"

gcloud projects add-iam-policy-binding aiwf-project \
  --member="serviceAccount:aiwf-service-account@aiwf-project.iam.gserviceaccount.com" \
  --role="roles/compute.admin"
```

### 4. Export Credentials

```bash
gcloud iam service-accounts keys create sa-key.json \
  --iam-account=aiwf-service-account@aiwf-project.iam.gserviceaccount.com

# Base64 encode for GitHub
base64 -w 0 sa-key.json > sa-key.b64
```

## Cost Monitoring

Check your usage:

```bash
gcloud compute instances list --filter="name:aiwf-*"
gcloud compute resource-settings describe
```

## Firewall Rules

Allowed ports:
- SSH (22)
- OpenClaw (8080)
- SustainBot (5000)

Access is open by default but can be restricted by source IP in production.
