#!/bin/bash
set -e

# Update system
apt-get update
apt-get upgrade -y

# Install required packages
apt-get install -y \
    curl \
    wget \
    git \
    python3-pip \
    python3-venv \
    nodejs \
    npm

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
usermod -aG docker $USER

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Create application directories
mkdir -p /home/$USER/{openclaw,sustainbot,logs}
cd /home/$USER

# Install Ollama for free LLM support
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama service
systemctl enable ollama
systemctl start ollama

# Pull LLaMA 2 model (free, 7B parameters)
ollama pull llama2

# Create systemd service for SustainBot
tee /etc/systemd/system/sustainbot.service > /dev/null <<EOF
[Unit]
Description=SustainBot Automation
After=network.target docker.service
Wants=docker.service

[Service]
Type=simple
User=$USER
WorkingDirectory=/home/$USER/sustainbot
ExecStart=/usr/bin/python3 main.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload

# Log completion
echo "AIWF VM initialization completed at $(date)" | tee /var/log/aiwf-init.log
