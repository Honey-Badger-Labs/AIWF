# Slack Integration Guide

## Create Slack App

1. Go to https://api.slack.com/apps
2. Click \"Create New App\"
3. Choose \"From scratch\"
4. Name: \"SustainBot\"
5. Select your workspace

## Configure Bot

### OAuth Scopes

Add scopes:
- `chat:write`
- `chat:write.public`
- `commands`
- `app_mentions:read`
- `channels:history`
- `channels:read`
- `users:read`

### Install App

1. Go to \"Install App\"
2. Click \"Install to Workspace\"
3. Copy Bot Token: `xoxb-...`
4. Copy Signing Secret

## Create Slash Commands

In Slack App settings:

1. \"Slash Commands\" → \"Create New Command\"
   - Command: `/sustainbot`
   - Request URL: `https://your-domain.com/slack/commands`
   - Short Description: \"Interact with SustainBot\"

2. Repeat for additional commands:
   - `/sustainbot-workflows`
   - `/sustainbot-status`
   - `/sustainbot-logs`

## Incoming Webhooks

1. \"Incoming Webhooks\" → \"Add New\"
2. Select channel: #sustainbot
3. Copy Webhook URL: `https://hooks.slack.com/services/...`

## GitHub Secrets

Add to GitHub:

```
SLACK_WEBHOOK_URL=<webhook_url>
SLACK_BOT_TOKEN=<xoxb-token>
SLACK_CHANNEL_ID=C...
```

## Testing

```bash
curl -X POST -H 'Content-type: application/json' \
  --data '{\"text\":\"Test message\"}' \
  $SLACK_WEBHOOK_URL
```

## Available Commands

- `/sustainbot help` - Get help
- `/sustainbot status` - Check system status
- `/sustainbot run <workflow>` - Execute workflow
- `/sustainbot-workflows` - List workflows
- `/sustainbot-logs <id>` - View logs
