#!/usr/bin/env python3
"""
SustainBot - Automation engine for sustainability workflows
Powered by OpenClaw orchestration and free LLM models (Ollama + LLaMA 2)
"""

import os
import sys
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import argparse

import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

from models import LLMInterface
from processes import WorkflowEngine

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False


class SustainBot:
    """Main SustainBot class for managing automation workflows"""

    def __init__(self):
        self.llm_model = os.getenv('LLM_MODEL', 'llama2')
        self.llm_host = os.getenv('LLM_HOST', 'localhost')
        self.llm_port = int(os.getenv('LLM_PORT', '11434'))
        self.openclaw_url = os.getenv('OPENCLAW_URL', 'http://localhost:8080')
        self.slack_webhook = os.getenv('SLACK_WEBHOOK_URL', '')
        self.workflows_dir = os.getenv('WORKFLOWS_DIR', './workflows')

        self.llm = LLMInterface(self.llm_model, self.llm_host, self.llm_port)
        self.workflow_engine = WorkflowEngine(self.openclaw_url, self.workflows_dir)

    def initialize(self) -> bool:
        """Initialize SustainBot and all dependencies"""
        logger.info("Initializing SustainBot...")

        # Check LLM connectivity
        if not self.llm.health_check():
            logger.error(f"LLM service not available at {self.llm_host}:{self.llm_port}")
            logger.info("Note: Ensure Ollama is running. Try: ollama serve")
            return False

        logger.info(f"✓ LLM Service: {self.llm_model} available")

        # Check OpenClaw connectivity
        if not self.workflow_engine.health_check():
            logger.warning(f"OpenClaw not available at {self.openclaw_url}")
            logger.info("Note: OpenClaw will be required for workflow execution")

        # Load workflows
        if not self.workflow_engine.load_workflows():
            logger.warning("No workflows loaded")

        logger.info("✓ SustainBot initialized successfully")
        return True

    def get_status(self) -> Dict[str, Any]:
        """Get current system status"""
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "llm": {
                    "model": self.llm_model,
                    "healthy": self.llm.health_check(),
                    "endpoint": f"http://{self.llm_host}:{self.llm_port}"
                },
                "workflows": {
                    "healthy": self.workflow_engine.health_check(),
                    "count": len(self.workflow_engine.workflows),
                    "endpoint": self.openclaw_url
                }
            }
        }

    def run_workflow(self, workflow_name: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a workflow with given parameters"""
        logger.info(f"Running workflow: {workflow_name}")

        if not self.workflow_engine.has_workflow(workflow_name):
            return {"success": False, "error": f"Workflow not found: {workflow_name}"}

        try:
            result = self.workflow_engine.execute(workflow_name, params or {})
            
            # Notify Slack if configured
            if self.slack_webhook:
                self._notify_slack(f"Workflow '{workflow_name}' completed", result)
            
            return result
        except Exception as e:
            logger.error(f"Error running workflow: {e}")
            return {"success": False, "error": str(e)}

    def _notify_slack(self, title: str, data: Dict[str, Any]) -> bool:
        """Send notification to Slack"""
        try:
            payload = {
                "text": title,
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*{title}*\n```{json.dumps(data, indent=2)}```"
                        }
                    }
                ]
            }
            response = requests.post(self.slack_webhook, json=payload)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error notifying Slack: {e}")
            return False


# Initialize SustainBot instance
bot = SustainBot()


# Flask Routes

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    status = bot.get_status()
    return jsonify(status)


@app.route('/workflows', methods=['GET'])
def list_workflows():
    """List all available workflows"""
    return jsonify({
        "workflows": bot.workflow_engine.list_workflows(),
        "count": len(bot.workflow_engine.workflows)
    })


@app.route('/workflows/<workflow_name>/execute', methods=['POST'])
def execute_workflow(workflow_name: str):
    """Execute a specific workflow"""
    try:
        params = request.get_json() or {}
        result = bot.run_workflow(workflow_name, params)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        logger.error(f"Error executing workflow: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/status', methods=['GET'])
def status():
    """Get detailed system status"""
    return jsonify(bot.get_status())


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='SustainBot Automation Engine')
    parser.add_argument('--init', action='store_true', help='Initialize SustainBot')
    parser.add_argument('--run', type=str, help='Run a specific workflow')
    parser.add_argument('--host', default='0.0.0.0', help='Server host')
    parser.add_argument('--port', type=int, default=5000, help='Server port')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    
    args = parser.parse_args()

    if args.init:
        logger.info("Initializing SustainBot...")
        if bot.initialize():
            logger.info("✓ Initialization complete")
            sys.exit(0)
        else:
            logger.error("✗ Initialization failed")
            sys.exit(1)
    
    if args.run:
        logger.info(f"Running workflow: {args.run}")
        result = bot.run_workflow(args.run)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result.get('success') else 1)
    
    # Initialize before starting server
    if not bot.initialize():
        logger.error("Failed to initialize SustainBot")
        sys.exit(1)
    
    # Start Flask server
    logger.info(f"Starting SustainBot server on {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
