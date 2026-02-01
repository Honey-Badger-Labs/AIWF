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
from functools import wraps
import argparse

import jwt
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

# JWT Configuration
JWT_SECRET = os.getenv('JWT_SECRET', 'dev-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'

# Flask app
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================

class SustainBotError(Exception):
    """Base exception for SustainBot"""
    def __init__(self, message, code="INTERNAL_ERROR", http_status=500):
        self.message = message
        self.code = code
        self.http_status = http_status
        super().__init__(self.message)


class AuthenticationError(SustainBotError):
    """Authentication failed"""
    def __init__(self, message="Authentication required"):
        super().__init__(message, code="AUTH_REQUIRED", http_status=401)


class ValidationError(SustainBotError):
    """Input validation failed"""
    def __init__(self, message):
        super().__init__(message, code="VALIDATION_ERROR", http_status=400)


class WorkflowNotFoundError(SustainBotError):
    """Workflow not found"""
    def __init__(self, workflow_name):
        super().__init__(
            f"Workflow '{workflow_name}' not found",
            code="WORKFLOW_NOT_FOUND",
            http_status=404
        )


class WorkflowExecutionError(SustainBotError):
    """Workflow execution failed"""
    def __init__(self, workflow_name, reason):
        super().__init__(
            f"Failed to execute '{workflow_name}': {reason}",
            code="EXECUTION_FAILED",
            http_status=500
        )


# ============================================================================
# AUTHENTICATION DECORATOR
# ============================================================================

def require_auth(f):
    """Decorator to require JWT authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            logger.warning(f"Request to {request.path} without authorization")
            return {
                "error": "Authorization header required",
                "code": "AUTH_REQUIRED"
            }, 401
        
        try:
            # Remove "Bearer " prefix if present
            token = token.replace('Bearer ', '').strip()
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            request.user_id = payload.get('user_id')
            request.actor = payload.get('actor')
            request.role = payload.get('role', 'user')
            logger.info(f"Authenticated request from {request.actor}")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {str(e)}")
            return {
                "error": "Invalid or expired token",
                "code": "INVALID_TOKEN"
            }, 401
        
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# INPUT VALIDATION
# ============================================================================

import re
from pathlib import Path

WORKFLOW_NAMES_REGEX = re.compile(r'^[a-zA-Z0-9_-]+$')
WORKFLOW_DIR = Path(os.getenv('WORKFLOWS_DIR', './workflows'))


def validate_workflow_name(name: str) -> Path:
    """Validate workflow name to prevent path traversal attacks"""
    if not WORKFLOW_NAMES_REGEX.match(name):
        raise ValidationError(f"Invalid workflow name: {name}. Must contain only alphanumerics, hyphens, and underscores.")
    
    # Check path doesn't escape workflow directory
    workflow_path = (WORKFLOW_DIR / name).resolve()
    if not str(workflow_path).startswith(str(WORKFLOW_DIR.resolve())):
        raise ValidationError("Path traversal detected")
    
    return workflow_path


def validate_request_body(data: Any) -> None:
    """Validate request body"""
    if data is None:
        raise ValidationError("Empty request body")
    
    if not isinstance(data, dict):
        raise ValidationError("Request body must be JSON object")
    
    # Limit input size (1MB max)
    if len(json.dumps(data)) > 1_000_000:
        raise ValidationError("Request body too large (max 1MB)")


# ============================================================================
# SLACK WEBHOOK VERIFICATION
# ============================================================================

import hashlib
import hmac
import time

SLACK_SIGNING_SECRET = os.getenv('SLACK_SIGNING_SECRET', '')


def verify_slack_signature(req_body: bytes, req_headers: Dict[str, str]) -> bool:
    """Verify Slack webhook request signature"""
    if not SLACK_SIGNING_SECRET:
        logger.warning("SLACK_SIGNING_SECRET not configured - skipping verification")
        return True
    
    timestamp = req_headers.get('X-Slack-Request-Timestamp', '')
    signature = req_headers.get('X-Slack-Signature', '')
    
    # Prevent replay attacks (5 minute window)
    try:
        req_timestamp = int(timestamp)
        if abs(int(time.time()) - req_timestamp) > 300:
            logger.warning("Request timestamp too old - possible replay attack")
            return False
    except (ValueError, TypeError):
        return False
    
    # Verify signature
    basestring = f"v0:{timestamp}:{req_body.decode()}"
    my_signature = f"v0={hmac.new(
        SLACK_SIGNING_SECRET.encode(),
        basestring.encode(),
        hashlib.sha256
    ).hexdigest()}"
    
    if not hmac.compare_digest(my_signature, signature):
        logger.warning("Invalid Slack signature")
        return False
    
    return True


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
    try:
        status = bot.get_status()
        return jsonify(status), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "error": "Health check failed",
            "code": "INTERNAL_ERROR"
        }, 500


@app.route('/workflows', methods=['GET'])
@require_auth
def list_workflows():
    """List all available workflows"""
    try:
        workflows = bot.workflow_engine.list_workflows()
        return jsonify({
            "workflows": workflows,
            "count": len(workflows)
        }), 200
    except Exception as e:
        logger.error(f"Error listing workflows: {e}")
        return {
            "error": "Failed to list workflows",
            "code": "INTERNAL_ERROR"
        }, 500


@app.route('/workflows/<workflow_name>/execute', methods=['POST'])
@require_auth
def execute_workflow(workflow_name: str):
    """Execute a specific workflow"""
    try:
        # Validate workflow name
        workflow_path = validate_workflow_name(workflow_name)
        
        # Validate request body
        data = request.get_json() or {}
        validate_request_body(data)
        
        logger.info(f"Executing workflow {workflow_name} by {request.actor}")
        
        # Execute workflow
        result = bot.run_workflow(workflow_name, data)
        
        if result.get('success'):
            return jsonify(result), 200
        else:
            raise WorkflowExecutionError(workflow_name, result.get('error', 'Unknown error'))
    
    except ValidationError as e:
        logger.warning(f"Validation error in {workflow_name}: {e.message}")
        return {
            "error": e.message,
            "code": e.code,
            "trace_id": request.headers.get('X-Trace-ID', 'unknown')
        }, e.http_status
    
    except WorkflowNotFoundError as e:
        logger.warning(f"Workflow not found: {workflow_name}")
        return {
            "error": e.message,
            "code": e.code,
            "trace_id": request.headers.get('X-Trace-ID', 'unknown')
        }, e.http_status
    
    except SustainBotError as e:
        logger.error(f"Workflow error in {workflow_name}: {e.message}")
        return {
            "error": e.message,
            "code": e.code,
            "trace_id": request.headers.get('X-Trace-ID', 'unknown')
        }, e.http_status
    
    except Exception as e:
        logger.error(f"Unexpected error executing {workflow_name}: {str(e)}", exc_info=True)
        return {
            "error": "Internal server error",
            "code": "INTERNAL_ERROR",
            "trace_id": request.headers.get('X-Trace-ID', 'unknown')
        }, 500


@app.route('/status', methods=['GET'])
def status():
    """Get detailed system status"""
    try:
        return jsonify(bot.get_status()), 200
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return {
            "error": "Failed to get status",
            "code": "INTERNAL_ERROR"
        }, 500


# ============================================================================
# GLOBAL ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return {
        "error": "Endpoint not found",
        "code": "NOT_FOUND"
    }, 404


@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors"""
    logger.error(f"Server error: {error}", exc_info=True)
    return {
        "error": "Internal server error",
        "code": "INTERNAL_ERROR"
    }, 500


# ============================================================================
# SLACK EVENT HANDLING
# ============================================================================

@app.route('/slack/events', methods=['POST'])
def slack_events():
    """Handle Slack webhook events"""
    try:
        # Verify Slack signature
        req_body = request.get_data()
        if not verify_slack_signature(req_body, request.headers):
            logger.warning("Invalid Slack signature")
            return {"error": "Invalid signature"}, 401
        
        event = request.get_json()
        
        # Handle URL verification challenge
        if event.get('type') == 'url_verification':
            logger.info("Slack URL verification received")
            return event.get('challenge')
        
        # Handle actual events
        if event.get('type') == 'event_callback':
            event_data = event.get('event', {})
            logger.info(f"Slack event received: {event_data.get('type')}")
            
            # Handle slash commands
            if event_data.get('type') == 'slash_commands':
                return handle_slack_command(event_data)
            
            return {"ok": True}
        
        return {"ok": True}, 200
    
    except Exception as e:
        logger.error(f"Error handling Slack event: {e}", exc_info=True)
        return {"error": "Internal error"}, 500


def handle_slack_command(command_data: Dict[str, Any]) -> tuple:
    """Handle Slack slash commands"""
    try:
        command = command_data.get('text', '').strip()
        response_url = command_data.get('response_url')
        user_id = command_data.get('user_id')
        
        logger.info(f"Slack command from {user_id}: {command}")
        
        # Parse command
        if command.startswith('status'):
            status = bot.get_status()
            message = f"SustainBot Status:\n```{json.dumps(status, indent=2)}```"
        elif command.startswith('list'):
            workflows = bot.workflow_engine.list_workflows()
            message = f"Available Workflows:\n{json.dumps(workflows, indent=2)}"
        else:
            message = "Unknown command. Try: status, list"
        
        # Send response
        if response_url:
            requests.post(response_url, json={"text": message})
        
        return {"ok": True}, 200
    
    except Exception as e:
        logger.error(f"Error handling Slack command: {e}")
        return {"error": "Failed to process command"}, 500


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
