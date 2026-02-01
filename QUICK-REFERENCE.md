# AIWF Quick Reference

## 🎯 What You Just Set Up

A complete **AI Workflow Automation** platform that combines:

```
┌─────────────────────────────────────────────────────────────────┐
│         GitHub Actions (CI/CD Trigger Layer)                   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
      ┌────────────────────┼────────────────────┐
      │                    │                    │
      ▼                    ▼                    ▼
┌──────────────┐  ┌─────────────────┐  ┌──────────────────┐
│ GCP Terraform│  │  OpenClaw       │  │  Slack Bot       │
│   (VM/IaC)   │  │  (Workflows)    │  │  (Commands)      │
└──────────────┘  └─────────────────┘  └──────────────────┘
      │                    │                    │
      └────────────────────┼────────────────────┘
                           │
                           ▼
                  ┌─────────────────────┐
                  │   SustainBot        │
                  │  (Process Automation│
                  │   + Free LLMs)      │
                  └─────────────────────┘
```

## 📊 Component Overview

### 1. **Infrastructure (Terraform)**
- **Location**: `terraform/`
- **What it does**: Creates GCP compute resources
- **Key files**:
  - `main.tf` - VPC, firewall, VM instance
  - `variables.tf` - Configuration variables
  - `startup-script.sh` - VM initialization

### 2. **Workflows (GitHub Actions)**
- **Location**: `.github/workflows/`
- **What they do**: Orchestrate deployment pipeline
- **Files**:
  - `deploy-infrastructure.yml` - Provision GCP VM
  - `deploy-openclaw.yml` - Deploy workflow engine
  - `slack-integration.yml` - Setup Slack bot
  - `sustainbot-start.yml` - Launch automation engine

### 3. **OpenClaw Integration**
- **Location**: `openclaw/`
- **What it does**: Process orchestration & workflow execution
- **Reference**: https://github.com/openclaw/openclaw.git
- **Port**: 8080

### 4. **Slack Integration**
- **Location**: `slack/`
- **What it does**: Bot commands & event handlers
- **Available commands**:
  - `/sustainbot help` - Get help
  - `/sustainbot status` - System status
  - `/sustainbot run <workflow>` - Execute workflow

### 5. **SustainBot (Automation Engine)**
- **Location**: `sustainbot/`
- **What it does**: AI-driven process automation
- **Key files**:
  - `main.py` - Flask server & workflow execution
  - `models.py` - LLM interface (Ollama/LLaMA 2)
  - `processes.py` - Workflow orchestration
- **Port**: 5000
- **LLM**: Ollama + LLaMA 2 (free model)

## 🚀 Getting Started

### Step 1: GCP Setup

```bash
bash scripts/setup-gcp.sh
```

This creates:
- GCP Project
- Service Account
- Exports credentials (base64)

### Step 2: GitHub Secrets

Add these secrets to your GitHub repository:
```
GCP_PROJECT_ID
GCP_SERVICE_ACCOUNT_KEY
GCP_ZONE
SLACK_WEBHOOK_URL
SLACK_BOT_TOKEN
SLACK_CHANNEL_ID
```

### Step 3: Trigger Deployment

```bash
git push origin main
```

Or manually:
```bash
gh workflow run deploy-infrastructure.yml
```

Workflows execute in sequence:
1. `deploy-infrastructure.yml` → Creates VM
2. `deploy-openclaw.yml` → Deploys workflow engine
3. `slack-integration.yml` → Configures Slack
4. `sustainbot-start.yml` → Starts automation

## 📝 Environment Variables

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Key variables:
- `GCP_PROJECT_ID` - Your GCP project
- `LLM_MODEL=llama2` - Free LLM model
- `OPENCLAW_URL` - Workflow engine URL
- `SLACK_WEBHOOK_URL` - Slack integration

## 🔗 Access URLs

Once deployed:
```
OpenClaw:  http://<INSTANCE_IP>:8080
SustainBot: http://<INSTANCE_IP>:5000
```

Get instance IP:
```bash
gcloud compute instances list --filter="name:aiwf-*" --format="value(EXTERNAL_IP)"
```

## 🤖 SustainBot API Examples

### Health Check
```bash
curl http://<IP>:5000/health
```

### List Workflows
```bash
curl http://<IP>:5000/workflows
```

### Execute Workflow
```bash
curl -X POST http://<IP>:5000/workflows/my-workflow/execute
```

### System Status
```bash
curl http://<IP>:5000/status
```

## 📚 Full Documentation

- **Setup Guide**: `docs/SETUP.md`
- **GCP Configuration**: `docs/GCP-GUIDE.md`
- **OpenClaw**: `docs/OPENCLAW-GUIDE.md`
- **Slack**: `docs/SLACK-GUIDE.md`

## 💰 Cost

**100% Free Tier:**
- 1x e2-micro VM (730 hrs/month) = $0
- 30GB storage = $0
- 1TB inbound bandwidth = $0
- Ollama + LLaMA 2 (free models) = $0
- GitHub Actions free tier = $0

**Total: $0/month** 🎉

## 🛠️ Utility Scripts

```bash
# Setup GCP
bash scripts/setup-gcp.sh

# Validate deployment
bash scripts/validate-deployment.sh

# Cleanup (destroys resources)
bash scripts/cleanup.sh
```

## 🔧 Troubleshooting

### OpenClaw not starting?
```bash
gcloud compute ssh aiwf-compute-1 --zone=us-central1-a
docker logs openclaw
docker-compose ps
```

### SustainBot not responding?
```bash
curl http://<IP>:5000/health
```

### Check Ollama LLM?
```bash
gcloud compute ssh aiwf-compute-1 --zone=us-central1-a
ollama list
ollama pull llama2
```

## 📋 Next Steps

1. **Configure Slack App**: Follow [SLACK-GUIDE.md](docs/SLACK-GUIDE.md)
2. **Create Workflows**: Add `.json` files to `openclaw/workflows/`
3. **Customize SustainBot**: Edit `sustainbot/` as needed
4. **Monitor Deployments**: Watch GitHub Actions runs
5. **Access Dashboards**: 
   - OpenClaw: http://<IP>:8080
   - SustainBot: http://<IP>:5000

## 🔗 Important Links

- **Repository**: https://github.com/Honey-Badger-Labs/AIWF
- **OpenClaw Repo**: https://github.com/openclaw/openclaw
- **Ollama**: https://ollama.ai
- **GCP Docs**: https://cloud.google.com/docs
- **Terraform GCP**: https://registry.terraform.io/providers/hashicorp/google/latest

---

**Built by Honey Badger Labs** 🦡

Questions? Check the docs or open an issue on GitHub!
