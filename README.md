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

## 📊 Production Readiness Assessment

**Status: 62/100 - Staging Ready (Not Production-Ready)**

Before deploying, read these assessment documents:

1. **[ASSESSMENT-SUMMARY.md](./ASSESSMENT-SUMMARY.md)** ⭐ START HERE
   - Answers your 3 key questions
   - Deployment decision tree
   - Timeline to production

2. **[PRODUCTION-READINESS-ASSESSMENT.md](./PRODUCTION-READINESS-ASSESSMENT.md)**
   - Comprehensive analysis (80+ criteria)
   - Security assessment (45/100)
   - Governance gaps (AIM-DRAG framework missing)
   - Implementation roadmap (6 phases, 21 days)

3. **[SECURITY-FIXES-REQUIRED.md](./SECURITY-FIXES-REQUIRED.md)** 🚨 CRITICAL
   - 5 security issues (SSH, auth, validation, Slack, errors)
   - Before/after code examples
   - Testing procedures
   - ~5 hours to fix all

### Quick Assessment Summary

| Category | Score | Status |
|----------|-------|--------|
| **Architecture** | 70/100 | ✅ Good |
| **Security** | 45/100 | 🚨 Critical gaps |
| **Governance** | 35/100 | ❌ Missing AIM-DRAG |
| **SustainNet Alignment** | 50/100 | ⚠️ Generic |
| **Documentation** | 65/100 | ✅ Good |
| **Overall** | **62/100** | **🟡 Staging Ready** |

### Can We Deploy Right Now?

```
To Staging (internal)?    ✅ YES (after 1-day security fixes)
To Production (external)? ❌ NO (need 3-4 weeks)
As SustainNet Product?    ❌ NO (need domain integration)
```

### Next Steps

1. **Today:** Read [ASSESSMENT-SUMMARY.md](./ASSESSMENT-SUMMARY.md)
2. **This Week:** Choose deployment path (A/B/C)
3. **Next Week:** Apply security fixes from [SECURITY-FIXES-REQUIRED.md](./SECURITY-FIXES-REQUIRED.md)
4. **Then:** Deploy to staging for testing
