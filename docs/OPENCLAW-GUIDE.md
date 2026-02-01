# OpenClaw Deployment Guide

## Overview

OpenClaw is deployed as a Docker container on the GCP VM.

Repository: https://github.com/openclaw/openclaw

## Automatic Deployment

OpenClaw is automatically deployed via GitHub Actions when infrastructure is provisioned.

## Manual Deployment

SSH to instance:

```bash
gcloud compute ssh aiwf-compute-1 --zone=us-central1-a
```

Clone and deploy:

```bash
git clone https://github.com/openclaw/openclaw.git
cd openclaw
docker-compose up -d
```

## Access Dashboard

```
http://<INSTANCE_IP>:8080
```

Default credentials (change immediately):
- Username: admin
- Password: admin

## Workflow Definitions

Place workflow JSON files in: `/home/USER/openclaw/workflows/`

Example workflow:

```json
{
  "name": "example-workflow",
  "steps": [
    {"type": "task", "name": "step1"},
    {"type": "task", "name": "step2"}
  ]
}
```

## Monitoring

```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f openclaw

# Health check
curl http://localhost:8080/health
```

## API Endpoints

- `GET /health` - Health check
- `POST /api/workflows/execute` - Submit workflow
- `GET /api/workflows` - List workflows
- `GET /api/executions/{id}` - Get execution status
