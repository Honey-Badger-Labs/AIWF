"""
Database Models for AIWF SustainBot

SQLAlchemy ORM models for PostgreSQL persistence.

Tables:
- Users: User accounts and authentication
- APIKeys: API key management with scopes
- AuditLogs: Governance audit trail
- WorkflowExecutions: Workflow execution history
- GovernanceMetrics: Historical metrics
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column, String, Boolean, DateTime, Text, Integer, 
    Numeric, ForeignKey, CheckConstraint, Index, ARRAY
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


# ============================================================================
# USER MODEL
# ============================================================================

class User(Base):
    """User account model"""
    __tablename__ = 'users'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default='user', index=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime)
    metadata = Column(JSONB, default=dict)
    
    # Relationships
    api_keys = relationship('APIKey', back_populates='user', cascade='all, delete-orphan')
    audit_logs = relationship('AuditLog', back_populates='user')
    workflow_executions = relationship('WorkflowExecution', back_populates='user')
    
    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'admin', 'sre', 'developer', 'auditor')",
            name='users_role_check'
        ),
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': str(self.id),
            'email': self.email,
            'name': self.name,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None
        }


# ============================================================================
# API KEY MODEL
# ============================================================================

class APIKey(Base):
    """API key for programmatic access"""
    __tablename__ = 'api_keys'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    key_hash = Column(String(128), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    scopes = Column(ARRAY(Text), default=['read'])
    is_active = Column(Boolean, default=True, index=True)
    last_used_at = Column(DateTime)
    expires_at = Column(DateTime, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    revoked_at = Column(DateTime)
    metadata = Column(JSONB, default=dict)
    
    # Relationships
    user = relationship('User', back_populates='api_keys')
    
    __table_args__ = (
        CheckConstraint(
            "scopes <@ ARRAY['read', 'write', 'admin', 'governance', 'workflows']::TEXT[]",
            name='api_keys_scopes_check'
        ),
    )
    
    @staticmethod
    def generate_key() -> str:
        """Generate a secure random API key"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def hash_key(key: str) -> str:
        """Hash API key for storage"""
        return hashlib.sha256(key.encode()).hexdigest()
    
    @classmethod
    def create_api_key(
        cls,
        user_id: uuid.UUID,
        name: str,
        scopes: List[str] = None,
        expires_in_days: int = 90
    ) -> tuple:
        """
        Create a new API key.
        
        Returns:
            (APIKey instance, plain text key)
            Warning: Plain text key is only available at creation!
        """
        plain_key = cls.generate_key()
        key_hash = cls.hash_key(plain_key)
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        api_key = cls(
            user_id=user_id,
            key_hash=key_hash,
            name=name,
            scopes=scopes or ['read'],
            expires_at=expires_at
        )
        
        return api_key, plain_key
    
    def verify_key(self, key: str) -> bool:
        """Verify if provided key matches this API key"""
        return self.key_hash == self.hash_key(key)
    
    def is_valid(self) -> bool:
        """Check if API key is currently valid"""
        if not self.is_active:
            return False
        if self.revoked_at:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True
    
    def __repr__(self):
        return f"<APIKey(id={self.id}, name='{self.name}', user_id={self.user_id})>"


# ============================================================================
# AUDIT LOG MODEL
# ============================================================================

class AuditLog(Base):
    """Governance audit log entry"""
    __tablename__ = 'audit_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), index=True)
    
    # AIM-DRAG Context
    actor_name = Column(String(255), nullable=False, index=True)
    actor_email = Column(String(255))
    actor_role = Column(String(50))
    drag_mode = Column(String(20), nullable=False, index=True)
    
    # Workflow Execution
    workflow_name = Column(String(100), nullable=False, index=True)
    parameters = Column(JSONB, default=dict)
    outcome = Column(String(20), nullable=False, index=True)
    error = Column(Text)
    duration_seconds = Column(Numeric(10, 3))
    
    # Input Constraints
    input_sources = Column(JSONB, default=list)
    input_constraints = Column(JSONB, default=list)
    
    # Mission
    mission_objective = Column(Text)
    mission_success_criteria = Column(JSONB, default=list)
    
    # Integrity & Timestamps
    integrity_hash = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship('User', back_populates='audit_logs')
    
    __table_args__ = (
        CheckConstraint(
            "drag_mode IN ('draft', 'research', 'grunt', 'execute')",
            name='audit_logs_drag_mode_check'
        ),
        CheckConstraint(
            "outcome IN ('success', 'failure', 'rejected')",
            name='audit_logs_outcome_check'
        ),
        Index('idx_audit_logs_created_at_desc', 'created_at', postgresql_using='btree', postgresql_ops={'created_at': 'DESC'}),
    )
    
    def compute_integrity_hash(self) -> str:
        """Compute SHA-256 hash of audit entry for tamper detection"""
        import json
        
        data = {
            'trace_id': str(self.trace_id),
            'actor_name': self.actor_name,
            'actor_email': self.actor_email,
            'actor_role': self.actor_role,
            'drag_mode': self.drag_mode,
            'workflow_name': self.workflow_name,
            'outcome': self.outcome,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        
        data_json = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_json.encode()).hexdigest()
    
    def verify_integrity(self) -> bool:
        """Verify integrity hash matches current data"""
        return self.integrity_hash == self.compute_integrity_hash()
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, workflow='{self.workflow_name}', outcome='{self.outcome}')>"


# ============================================================================
# WORKFLOW EXECUTION MODEL
# ============================================================================

class WorkflowExecution(Base):
    """Workflow execution record"""
    __tablename__ = 'workflow_executions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trace_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), index=True)
    workflow_name = Column(String(100), nullable=False, index=True)
    parameters = Column(JSONB, default=dict)
    
    # Execution Details
    status = Column(String(20), nullable=False, default='running', index=True)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime)
    duration_seconds = Column(Numeric(10, 3))
    
    # Results
    result = Column(JSONB)
    error = Column(Text)
    
    # Governance Link
    audit_log_id = Column(UUID(as_uuid=True), ForeignKey('audit_logs.id', ondelete='SET NULL'))
    
    # Relationships
    user = relationship('User', back_populates='workflow_executions')
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'completed', 'failed', 'cancelled')",
            name='workflow_executions_status_check'
        ),
        Index('idx_workflow_executions_started_at_desc', 'started_at', postgresql_using='btree', postgresql_ops={'started_at': 'DESC'}),
    )
    
    def __repr__(self):
        return f"<WorkflowExecution(id={self.id}, workflow='{self.workflow_name}', status='{self.status}')>"


# ============================================================================
# GOVERNANCE METRICS MODEL
# ============================================================================

class GovernanceMetric(Base):
    """Historical governance metrics"""
    __tablename__ = 'governance_metrics'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metric_name = Column(String(100), nullable=False, index=True)
    metric_value = Column(Numeric(15, 3), nullable=False)
    drag_mode = Column(String(20), index=True)
    actor_role = Column(String(50))
    workflow_name = Column(String(100), index=True)
    outcome = Column(String(20))
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    labels = Column(JSONB, default=dict)
    
    __table_args__ = (
        Index('idx_governance_metrics_timestamp_desc', 'timestamp', postgresql_using='btree', postgresql_ops={'timestamp': 'DESC'}),
    )
    
    def __repr__(self):
        return f"<GovernanceMetric(metric='{self.metric_name}', value={self.metric_value})>"
