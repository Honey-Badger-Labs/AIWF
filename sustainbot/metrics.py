"""
Observability Module for AIWF SustainBot

Provides Prometheus metrics for governance tracking and operational monitoring.

Integrates with:
- sustainnet-observability repository (centralized dashboards)
- CloudWatch (AWS monitoring)
- Grafana (visualization)

Metrics Categories:
1. Governance Metrics (AIM-DRAG compliance)
2. Workflow Metrics (execution tracking)
3. System Metrics (health, performance)
"""

from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, REGISTRY
from typing import Optional
import time

# ============================================================================
# GOVERNANCE METRICS (AIM-DRAG Compliance)
# ============================================================================

aim_requests_total = Counter(
    'sustainbot_aim_requests_total',
    'Total AIM-declared governance requests',
    ['drag_mode', 'actor_role', 'workflow_name']
)

aim_validation_failures_total = Counter(
    'sustainbot_aim_validation_failures_total',
    'Total AIM validation failures',
    ['failure_reason', 'drag_mode']
)

governed_workflow_duration_seconds = Histogram(
    'sustainbot_governed_workflow_duration_seconds',
    'Governed workflow execution duration',
    ['workflow_name', 'outcome', 'drag_mode'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

audit_log_entries_total = Counter(
    'sustainbot_audit_log_entries_total',
    'Total audit log entries written',
    ['outcome', 'drag_mode']
)

prescriptive_language_detections_total = Counter(
    'sustainbot_prescriptive_language_detections_total',
    'Prescriptive language filter detections',
    ['drag_mode', 'phrase_type']
)

# ============================================================================
# WORKFLOW METRICS (Operational)
# ============================================================================

workflow_executions_total = Counter(
    'sustainbot_workflow_executions_total',
    'Total workflow executions (governed + ungoverned)',
    ['workflow_name', 'outcome']
)

workflow_execution_errors_total = Counter(
    'sustainbot_workflow_execution_errors_total',
    'Workflow execution errors',
    ['workflow_name', 'error_type']
)

slack_events_received_total = Counter(
    'sustainbot_slack_events_received_total',
    'Slack events received',
    ['event_type']
)

slack_signature_verifications_total = Counter(
    'sustainbot_slack_signature_verifications_total',
    'Slack signature verifications',
    ['outcome']
)

# ============================================================================
# AUTHENTICATION METRICS
# ============================================================================

jwt_validations_total = Counter(
    'sustainbot_jwt_validations_total',
    'JWT token validations',
    ['outcome']
)

authentication_failures_total = Counter(
    'sustainbot_authentication_failures_total',
    'Authentication failures',
    ['failure_type']
)

# ============================================================================
# SYSTEM METRICS
# ============================================================================

http_requests_total = Counter(
    'sustainbot_http_requests_total',
    'HTTP requests received',
    ['method', 'endpoint', 'status_code']
)

http_request_duration_seconds = Histogram(
    'sustainbot_http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

active_requests = Gauge(
    'sustainbot_active_requests',
    'Currently active HTTP requests'
)

# ============================================================================
# APPLICATION INFO
# ============================================================================

app_info = Info(
    'sustainbot_application',
    'Application metadata'
)

# Set application metadata
app_info.info({
    'version': '1.0.0',
    'phase': '3',
    'governance_framework': 'AIM-DRAG',
    'compliance_spec': 'OTS-v0.1.0-alpha'
})

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

class MetricsTimer:
    """Context manager for timing operations with automatic metric recording"""
    
    def __init__(self, histogram: Histogram, labels: dict):
        self.histogram = histogram
        self.labels = labels
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        self.histogram.labels(**self.labels).observe(duration)


def record_aim_request(drag_mode: str, actor_role: str, workflow_name: str):
    """Record an AIM-declared governance request"""
    aim_requests_total.labels(
        drag_mode=drag_mode,
        actor_role=actor_role,
        workflow_name=workflow_name
    ).inc()


def record_aim_validation_failure(failure_reason: str, drag_mode: str):
    """Record an AIM validation failure"""
    aim_validation_failures_total.labels(
        failure_reason=failure_reason,
        drag_mode=drag_mode
    ).inc()


def record_workflow_execution(
    workflow_name: str,
    outcome: str,
    duration_seconds: float,
    drag_mode: Optional[str] = None
):
    """Record workflow execution metrics"""
    # Record general workflow execution
    workflow_executions_total.labels(
        workflow_name=workflow_name,
        outcome=outcome
    ).inc()
    
    # Record governed workflow metrics if AIM-DRAG was used
    if drag_mode:
        governed_workflow_duration_seconds.labels(
            workflow_name=workflow_name,
            outcome=outcome,
            drag_mode=drag_mode
        ).observe(duration_seconds)


def record_audit_log_entry(outcome: str, drag_mode: str):
    """Record audit log entry written"""
    audit_log_entries_total.labels(
        outcome=outcome,
        drag_mode=drag_mode
    ).inc()


def record_prescriptive_language_detection(drag_mode: str, phrase_type: str):
    """Record prescriptive language filter detection"""
    prescriptive_language_detections_total.labels(
        drag_mode=drag_mode,
        phrase_type=phrase_type
    ).inc()


def record_slack_event(event_type: str):
    """Record Slack event received"""
    slack_events_received_total.labels(event_type=event_type).inc()


def record_slack_verification(outcome: str):
    """Record Slack signature verification"""
    slack_signature_verifications_total.labels(outcome=outcome).inc()


def record_jwt_validation(outcome: str):
    """Record JWT validation"""
    jwt_validations_total.labels(outcome=outcome).inc()


def record_authentication_failure(failure_type: str):
    """Record authentication failure"""
    authentication_failures_total.labels(failure_type=failure_type).inc()


def record_http_request(method: str, endpoint: str, status_code: int, duration: float):
    """Record HTTP request metrics"""
    http_requests_total.labels(
        method=method,
        endpoint=endpoint,
        status_code=str(status_code)
    ).inc()
    
    http_request_duration_seconds.labels(
        method=method,
        endpoint=endpoint
    ).observe(duration)


def get_metrics_text() -> bytes:
    """Get Prometheus metrics in text format"""
    return generate_latest(REGISTRY)
