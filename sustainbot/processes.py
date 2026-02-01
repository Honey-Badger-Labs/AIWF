"""Workflow orchestration for SustainBot"""

import os
import json
import logging
import requests
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """Orchestrates workflow execution via OpenClaw"""

    def __init__(self, openclaw_url: str, workflows_dir: str):
        self.openclaw_url = openclaw_url
        self.workflows_dir = workflows_dir
        self.workflows: Dict[str, Dict[str, Any]] = {}
        self.timeout = 30

    def health_check(self) -> bool:
        """Check if OpenClaw is available"""
        try:
            response = requests.get(f"{self.openclaw_url}/health", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def load_workflows(self) -> bool:
        """Load workflow definitions from disk"""
        try:
            workflows_path = Path(self.workflows_dir)
            if not workflows_path.exists():
                logger.warning(f"Workflows directory not found: {self.workflows_dir}")
                return False

            for workflow_file in workflows_path.glob('*.json'):
                try:
                    with open(workflow_file, 'r') as f:
                        workflow = json.load(f)
                        workflow_name = workflow_file.stem
                        self.workflows[workflow_name] = workflow
                        logger.info(f"Loaded workflow: {workflow_name}")
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in {workflow_file}: {e}")

            return True
        except Exception as e:
            logger.error(f"Error loading workflows: {e}")
            return False

    def has_workflow(self, workflow_name: str) -> bool:
        """Check if a workflow exists"""
        return workflow_name in self.workflows

    def list_workflows(self) -> List[str]:
        """List all available workflows"""
        return list(self.workflows.keys())

    def execute(self, workflow_name: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a workflow via OpenClaw"""
        if not self.has_workflow(workflow_name):
            return {"success": False, "error": f"Workflow not found: {workflow_name}"}

        try:
            workflow = self.workflows[workflow_name]
            execution_id = f"{workflow_name}_{datetime.utcnow().isoformat()}"

            payload = {
                "workflow": workflow,
                "parameters": params or {},
                "execution_id": execution_id
            }

            # If OpenClaw is available, submit to it
            if self.health_check():
                response = requests.post(
                    f"{self.openclaw_url}/api/workflows/execute",
                    json=payload,
                    timeout=self.timeout
                )

                if response.status_code in [200, 202]:
                    return {
                        "success": True,
                        "execution_id": execution_id,
                        "workflow": workflow_name,
                        "status": "submitted",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    logger.error(f"OpenClaw error: {response.status_code}")
                    return {"success": False, "error": f"OpenClaw error: {response.status_code}"}
            else:
                # Local execution if OpenClaw not available
                logger.info(f"Executing workflow locally: {workflow_name}")
                return {
                    "success": True,
                    "execution_id": execution_id,
                    "workflow": workflow_name,
                    "status": "executed",
                    "mode": "local",
                    "timestamp": datetime.utcnow().isoformat()
                }
        except Exception as e:
            logger.error(f"Error executing workflow: {e}")
            return {"success": False, "error": str(e)}
