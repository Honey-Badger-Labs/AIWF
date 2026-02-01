"""
CloudWatch Integration for AIWF SustainBot

Pushes governance metrics and logs to AWS CloudWatch for:
- Centralized monitoring
- Alerting on governance violations
- Long-term metric retention
- Integration with sustainnet-observability

Metrics Published:
- AIM requests (by DRAG mode, actor role)
- Validation failures
- Workflow execution metrics
- Audit log entries
"""

import os
import logging
from typing import Optional, Dict, List
from datetime import datetime

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class CloudWatchPublisher:
    """Publish metrics and logs to AWS CloudWatch"""
    
    def __init__(
        self,
        namespace: str = 'AIWF/SustainBot',
        region: str = 'eu-west-1',
        enabled: bool = True
    ):
        """
        Initialize CloudWatch publisher.
        
        Args:
            namespace: CloudWatch namespace for metrics
            region: AWS region
            enabled: Enable/disable CloudWatch publishing
        """
        self.namespace = namespace
        self.region = region
        self.enabled = enabled
        
        if self.enabled:
            try:
                self.cloudwatch = boto3.client('cloudwatch', region_name=region)
                self.logs = boto3.client('logs', region_name=region)
                logger.info(f"CloudWatch integration enabled (namespace: {namespace}, region: {region})")
            except Exception as e:
                logger.warning(f"CloudWatch client initialization failed: {e}")
                self.enabled = False
        else:
            logger.info("CloudWatch integration disabled")
    
    def put_metric(
        self,
        metric_name: str,
        value: float,
        unit: str = 'Count',
        dimensions: Optional[List[Dict[str, str]]] = None
    ):
        """
        Put a single metric to CloudWatch.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Metric unit (Count, Seconds, etc.)
            dimensions: List of dimension dicts [{"Name": "...", "Value": "..."}]
        """
        if not self.enabled:
            return
        
        try:
            metric_data = {
                'MetricName': metric_name,
                'Value': value,
                'Unit': unit,
                'Timestamp': datetime.utcnow()
            }
            
            if dimensions:
                metric_data['Dimensions'] = dimensions
            
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[metric_data]
            )
        except ClientError as e:
            logger.error(f"Failed to put metric {metric_name}: {e}")
    
    def put_governance_metric(
        self,
        metric_name: str,
        value: float,
        drag_mode: str,
        actor_role: str = None,
        workflow_name: str = None
    ):
        """
        Put governance-related metric with standard dimensions.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            drag_mode: DRAG mode (draft, research, grunt, execute)
            actor_role: Actor's role (optional)
            workflow_name: Workflow name (optional)
        """
        dimensions = [
            {'Name': 'DRAGMode', 'Value': drag_mode}
        ]
        
        if actor_role:
            dimensions.append({'Name': 'ActorRole', 'Value': actor_role})
        
        if workflow_name:
            dimensions.append({'Name': 'WorkflowName', 'Value': workflow_name})
        
        self.put_metric(metric_name, value, unit='Count', dimensions=dimensions)
    
    def record_aim_request(self, drag_mode: str, actor_role: str, workflow_name: str):
        """Record AIM-declared governance request"""
        self.put_governance_metric(
            metric_name='AIMRequests',
            value=1.0,
            drag_mode=drag_mode,
            actor_role=actor_role,
            workflow_name=workflow_name
        )
    
    def record_aim_validation_failure(self, failure_reason: str, drag_mode: str):
        """Record AIM validation failure"""
        self.put_metric(
            metric_name='AIMValidationFailures',
            value=1.0,
            unit='Count',
            dimensions=[
                {'Name': 'FailureReason', 'Value': failure_reason[:50]},
                {'Name': 'DRAGMode', 'Value': drag_mode}
            ]
        )
    
    def record_workflow_execution(
        self,
        workflow_name: str,
        outcome: str,
        duration_seconds: float,
        drag_mode: str = None
    ):
        """Record workflow execution"""
        dimensions = [
            {'Name': 'WorkflowName', 'Value': workflow_name},
            {'Name': 'Outcome', 'Value': outcome}
        ]
        
        if drag_mode:
            dimensions.append({'Name': 'DRAGMode', 'Value': drag_mode})
        
        # Count metric
        self.put_metric(
            metric_name='WorkflowExecutions',
            value=1.0,
            unit='Count',
            dimensions=dimensions
        )
        
        # Duration metric
        self.put_metric(
            metric_name='WorkflowDuration',
            value=duration_seconds,
            unit='Seconds',
            dimensions=dimensions
        )
    
    def record_audit_log_entry(self, outcome: str, drag_mode: str):
        """Record audit log entry written"""
        self.put_metric(
            metric_name='AuditLogEntries',
            value=1.0,
            unit='Count',
            dimensions=[
                {'Name': 'Outcome', 'Value': outcome},
                {'Name': 'DRAGMode', 'Value': drag_mode}
            ]
        )
    
    def put_log_event(
        self,
        log_group: str,
        log_stream: str,
        message: str,
        timestamp: Optional[datetime] = None
    ):
        """
        Put log event to CloudWatch Logs.
        
        Args:
            log_group: CloudWatch log group name
            log_stream: CloudWatch log stream name
            message: Log message
            timestamp: Event timestamp (default: now)
        """
        if not self.enabled:
            return
        
        try:
            # Ensure log group exists
            try:
                self.logs.create_log_group(logGroupName=log_group)
            except self.logs.exceptions.ResourceAlreadyExistsException:
                pass
            
            # Ensure log stream exists
            try:
                self.logs.create_log_stream(
                    logGroupName=log_group,
                    logStreamName=log_stream
                )
            except self.logs.exceptions.ResourceAlreadyExistsException:
                pass
            
            # Put log event
            timestamp_ms = int((timestamp or datetime.utcnow()).timestamp() * 1000)
            
            self.logs.put_log_events(
                logGroupName=log_group,
                logStreamName=log_stream,
                logEvents=[
                    {
                        'timestamp': timestamp_ms,
                        'message': message
                    }
                ]
            )
        except ClientError as e:
            logger.error(f"Failed to put log event: {e}")


# Singleton instance
_cloudwatch_publisher: Optional[CloudWatchPublisher] = None


def get_cloudwatch_publisher() -> CloudWatchPublisher:
    """Get CloudWatch publisher singleton"""
    global _cloudwatch_publisher
    
    if _cloudwatch_publisher is None:
        namespace = os.getenv('CLOUDWATCH_NAMESPACE', 'AIWF/SustainBot')
        region = os.getenv('CLOUDWATCH_REGION', 'eu-west-1')
        enabled = os.getenv('CLOUDWATCH_ENABLED', 'false').lower() == 'true'
        
        _cloudwatch_publisher = CloudWatchPublisher(
            namespace=namespace,
            region=region,
            enabled=enabled
        )
    
    return _cloudwatch_publisher
