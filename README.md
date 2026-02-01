# AIWF - AI Workflow Automation

Complete automation platform built on GCP, OpenClaw, SustainBot, Slack, and free LLM models.

## 📁 Project Structure

```
.github/workflows/         # GitHub Actions for deployment
terraform/                 # Infrastructure as Code
openclaw/                  # OpenClaw configuration
slack/                     # Slack bot integration
sustainbot/                # SustainBot automation engine
scripts/                   # Utility scripts
docs/                      # Documentation
```

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/Honey-Badger-Labs/AIWF.git
cd AIWF
```

### 2. Set GitHub Secrets

Add to your GitHub repository:
- `GCP_PROJECT_ID`
- `GCP_SERVICE_ACCOUNT_KEY` (base64)
- `GCP_ZONE`
- `SLACK_WEBHOOK_URL`
- `SLACK_BOT_TOKEN`
- `SLACK_CHANNEL_ID`

### 3. Trigger Deployment
```bash
git push origin main
```

## 📚 Documentation

- [Setup Guide](./docs/SETUP.md) - Complete setup instructions
- [GCP Configuration](./docs/GCP-GUIDE.md) - Resource setup
- [OpenClaw Deployment](./docs/OPENCLAW-GUIDE.md) - Workflow engine
- [Slack Integration](./docs/SLACK-GUIDE.md) - Bot configuration

## ✨ Features

✅ Infrastructure as Code (Terraform) for GCP  
✅ Automated Linux VM provisioning (e2-micro free tier)  
✅ OpenClaw workflow engine deployment  
✅ Slack bot command integration  
✅ Free LLM models (Ollama + LLaMA 2)  
✅ SustainBot process automation  
✅ GitHub Actions CI/CD workflows  

## 💰 Cost Optimization

Uses only GCP free tier:
- 1x e2-micro VM (730 hours/month)
- 30GB storage
- 1TB inbound bandwidth
- Free LLM models (no API costs)
