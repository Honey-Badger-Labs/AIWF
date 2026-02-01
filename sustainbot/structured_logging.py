"""
Structured Logging Configuration for AIWF SustainBot

Provides JSON-formatted logs with governance context for:
- ELK Stack (Elasticsearch, Logstash, Kibana)
- CloudWatch Logs
- Splunk
- Any JSON log aggregator

Log Format:
{
  "timestamp": "2026-02-01T14:30:00.000Z",
  "level": "INFO",
  "logger": "sustainbot.main",
  "message": "Workflow executed successfully",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "actor": "Jake Smith",
  "drag_mode": "execute",
  "workflow_name": "deploy_staging",
  "outcome": "success",
  "duration_seconds": 2.34
}
"""

import logging
import json
from datetime import datetime
from typing import Any, Dict
from pythonjsonlogger import jsonlogger


class GovernanceJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with governance context"""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]):
        """Add custom fields to log record"""
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp in ISO format
        log_record['timestamp'] = datetime.utcnow().isoformat() + 'Z'
        
        # Add level name
        log_record['level'] = record.levelname
        
        # Add logger name
        log_record['logger'] = record.name
        
        # Add governance context if available
        if hasattr(record, 'trace_id'):
            log_record['trace_id'] = record.trace_id
        
        if hasattr(record, 'actor'):
            log_record['actor'] = record.actor
        
        if hasattr(record, 'drag_mode'):
            log_record['drag_mode'] = record.drag_mode
        
        if hasattr(record, 'workflow_name'):
            log_record['workflow_name'] = record.workflow_name
        
        if hasattr(record, 'outcome'):
            log_record['outcome'] = record.outcome
        
        if hasattr(record, 'duration_seconds'):
            log_record['duration_seconds'] = record.duration_seconds


def configure_json_logging(log_file: str = './logs/sustainbot.jsonl', level: int = logging.INFO):
    """
    Configure JSON logging for governance-aware structured logs.
    
    Args:
        log_file: Path to JSON log file (append-only)
        level: Logging level (default: INFO)
    """
    # Create logs directory if it doesn't exist
    import os
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Create formatter
    formatter = GovernanceJsonFormatter(
        '%(timestamp)s %(level)s %(logger)s %(message)s'
    )
    
    # File handler for JSON logs
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    
    # Console handler for human-readable logs (keep for development)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    console_handler.setLevel(level)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return root_logger


# Convenience function for governance logging
def log_governance_event(
    logger: logging.Logger,
    level: int,
    message: str,
    trace_id: str = None,
    actor: str = None,
    drag_mode: str = None,
    workflow_name: str = None,
    outcome: str = None,
    duration_seconds: float = None
):
    """
    Log governance event with full context.
    
    Example:
        log_governance_event(
            logger=logger,
            level=logging.INFO,
            message="Workflow executed successfully",
            trace_id="550e8400-...",
            actor="Jake Smith",
            drag_mode="execute",
            workflow_name="deploy_staging",
            outcome="success",
            duration_seconds=2.34
        )
    """
    extra = {}
    if trace_id:
        extra['trace_id'] = trace_id
    if actor:
        extra['actor'] = actor
    if drag_mode:
        extra['drag_mode'] = drag_mode
    if workflow_name:
        extra['workflow_name'] = workflow_name
    if outcome:
        extra['outcome'] = outcome
    if duration_seconds is not None:
        extra['duration_seconds'] = duration_seconds
    
    logger.log(level, message, extra=extra)
