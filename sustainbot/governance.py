"""
AIM-DRAG Framework Implementation for AIWF SustainBot

This module implements the AIM-DRAG governance framework from SustainNet's
Open Trust Spec (OTS) v0.1.0-alpha for accountable AI usage.

AIM (Intent Lock):
- Actor: Named human accountable for the decision
- Input: Real-world data sources and constraints
- Mission: What decision or outcome must improve

DRAG (Decision Responsibilities):
- Draft: AI generates first versions
- Research: AI surfaces unknowns and risks
- Analysis: HUMAN-ONLY - evaluates trade-offs
- Grunt: AI handles mechanical, repetitive tasks

Reference: sustainnet-vision/GOVERNANCE/AIM-DRAG-FRAMEWORK.md
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime
import hashlib
import json
import re


# ============================================================================
# DRAG MODE ENUMERATION
# ============================================================================

class DRAGMode(str, Enum):
    """
    DRAG Decision Responsibilities
    
    - DRAFT: Generate initial versions (AI allowed)
    - RESEARCH: Surface unknowns, risks, options (AI allowed)
    - GRUNT: Mechanical, repetitive tasks (AI allowed)
    - EXECUTE: Execute approved workflow (AI allowed with human oversight)
    
    Note: ANALYSIS mode is intentionally omitted - reserved for humans only.
    AI must NOT make decisions, only provide options.
    """
    DRAFT = "draft"
    RESEARCH = "research"
    GRUNT = "grunt"
    EXECUTE = "execute"  # For workflow execution with governance


# ============================================================================
# AIM DECLARATION MODELS
# ============================================================================

class Actor(BaseModel):
    """
    Named human accountable for AI interaction.
    
    The Actor is the person who:
    - Takes responsibility for the workflow execution
    - Will be held accountable for outcomes
    - Has authority to approve/reject AI recommendations
    """
    name: str = Field(..., min_length=1, description="Full name of accountable person")
    email: Optional[str] = Field(None, description="Contact email for accountability")
    role: str = Field(..., min_length=1, description="Role/title (e.g., 'DevOps Engineer', 'Product Lead')")
    
    @validator('email')
    def validate_email(cls, v):
        if v and '@' not in v:
            raise ValueError("Invalid email format")
        return v


class InputSource(BaseModel):
    """
    Real-world data source constraining AI behavior.
    
    Examples:
    - {"type": "api_endpoint", "description": "Slack webhook payload"}
    - {"type": "configuration", "description": "terraform.tfvars"}
    - {"type": "external_system", "description": "GitHub Actions workflow file"}
    """
    type: str = Field(..., description="Type of input (e.g., 'file', 'api', 'database', 'configuration')")
    description: str = Field(..., description="Human-readable description of the input")
    location: Optional[str] = Field(None, description="Path, URL, or identifier")


class Input(BaseModel):
    """
    Constraints on AI behavior from real-world data.
    
    - sources: What data is AI allowed to use?
    - constraints: What rules must AI follow?
    """
    sources: List[InputSource] = Field(..., min_items=1, description="Data sources AI can access")
    constraints: List[str] = Field(default_factory=list, description="Rules AI must follow (e.g., 'Read-only', 'No destructive ops')")


class Mission(BaseModel):
    """
    What decision or outcome must improve.
    
    The Mission defines:
    - objective: What are we trying to achieve?
    - success_criteria: How do we know it worked?
    """
    objective: str = Field(..., min_length=10, description="Clear statement of what must improve")
    success_criteria: List[str] = Field(..., min_items=1, description="Measurable success indicators")


class AIMDeclaration(BaseModel):
    """
    Complete AIM (Intent Lock) declaration.
    
    Required before any AI workflow execution to ensure accountability.
    
    Example:
        aim = AIMDeclaration(
            actor=Actor(
                name="Jake Smith",
                email="jake@sustainnet.io",
                role="Product Lead"
            ),
            input=Input(
                sources=[
                    InputSource(type="slack_webhook", description="Slash command payload")
                ],
                constraints=["Read-only access", "No infrastructure changes"]
            ),
            mission=Mission(
                objective="Deploy updated application to staging environment",
                success_criteria=["Zero downtime", "Health checks pass", "Rollback on failure"]
            )
        )
    """
    actor: Actor
    input: Input
    mission: Mission
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging"""
        return {
            "actor": self.actor.dict(),
            "input": self.input.dict(),
            "mission": self.mission.dict()
        }


# ============================================================================
# GOVERNANCE REQUEST MODEL
# ============================================================================

class GovernanceRequest(BaseModel):
    """
    Complete governance-aware workflow execution request.
    
    Combines workflow parameters with AIM-DRAG governance context.
    
    Example:
        request = GovernanceRequest(
            workflow_name="deploy-to-staging",
            aim=aim_declaration,
            drag_mode=DRAGMode.EXECUTE,
            parameters={"environment": "staging", "version": "v1.2.3"}
        )
    """
    workflow_name: str = Field(..., description="Name of workflow to execute")
    aim: AIMDeclaration = Field(..., description="Complete AIM declaration")
    drag_mode: DRAGMode = Field(..., description="DRAG responsibility mode")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Workflow-specific parameters")
    trace_id: Optional[str] = Field(None, description="Trace ID for request tracking")
    
    @validator('drag_mode')
    def validate_drag_mode(cls, v):
        """Ensure only AI-allowed DRAG modes are used"""
        if v not in [DRAGMode.DRAFT, DRAGMode.RESEARCH, DRAGMode.GRUNT, DRAGMode.EXECUTE]:
            raise ValueError(f"Invalid DRAG mode: {v}. Analysis is human-only.")
        return v


# ============================================================================
# PRESCRIPTIVE LANGUAGE FILTER
# ============================================================================

FORBIDDEN_PHRASES = [
    "you should",
    "you must",
    "the best option is",
    "this is the right choice",
    "definitely do",
    "always use",
    "never use",
    "i recommend",
    "my recommendation is",
]

ALLOWED_PHRASES = [
    "options include",
    "trade-offs are",
    "considerations include",
    "alternatives are",
    "one approach is",
    "another option is",
    "unknowns are",
    "risks include",
]


def filter_prescriptive_language(output: str, drag_mode: DRAGMode) -> tuple[bool, Optional[str]]:
    """
    Detect prescriptive language in AI output for Research/Draft modes.
    
    In RESEARCH and DRAFT modes, AI should present options, not decisions.
    EXECUTE and GRUNT modes allow more directive language.
    
    Args:
        output: AI-generated text to check
        drag_mode: Current DRAG responsibility mode
        
    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if output is acceptable
        - (False, "error message") if prescriptive language detected
    """
    if drag_mode in [DRAGMode.EXECUTE, DRAGMode.GRUNT]:
        # More permissive for execution modes
        return True, None
    
    output_lower = output.lower()
    
    # Check for forbidden phrases
    for phrase in FORBIDDEN_PHRASES:
        if phrase in output_lower:
            return False, (
                f"Prescriptive language detected in {drag_mode.value} mode: '{phrase}'. "
                f"Use neutral phrasing like: {', '.join(ALLOWED_PHRASES[:3])}"
            )
    
    return True, None


# ============================================================================
# AUDIT LOG ENTRY
# ============================================================================

class AuditLogEntry(BaseModel):
    """
    Tamper-evident audit log entry for governance compliance.
    
    Each workflow execution is logged with:
    - Complete AIM-DRAG context
    - Timestamp and trace ID
    - Workflow outcome
    - Integrity hash for tamper detection
    
    Logs are append-only and retained for 90 days minimum per OTS spec.
    """
    trace_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    aim: Dict[str, Any]
    drag_mode: str
    workflow_name: str
    parameters: Dict[str, Any]
    outcome: str  # "success", "failure", "rejected"
    error: Optional[str] = None
    duration_seconds: Optional[float] = None
    integrity_hash: Optional[str] = None
    
    def compute_integrity_hash(self) -> str:
        """
        Generate SHA-256 hash of log entry for tamper detection.
        
        Hash includes all fields except integrity_hash itself.
        """
        log_data = self.dict(exclude={'integrity_hash'})
        log_json = json.dumps(log_data, sort_keys=True, default=str)
        return hashlib.sha256(log_json.encode()).hexdigest()
    
    def finalize(self):
        """Compute and set integrity hash"""
        self.integrity_hash = self.compute_integrity_hash()
    
    def verify_integrity(self) -> bool:
        """Verify log entry has not been tampered with"""
        if not self.integrity_hash:
            return False
        expected_hash = self.compute_integrity_hash()
        return expected_hash == self.integrity_hash
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============================================================================
# GOVERNANCE VALIDATION
# ============================================================================

def validate_governance_request(request: GovernanceRequest) -> tuple[bool, Optional[str]]:
    """
    Validate complete governance request before workflow execution.
    
    Checks:
    1. AIM declaration is complete
    2. Actor is named and accountable
    3. Input sources are specified
    4. Mission has success criteria
    5. DRAG mode is appropriate
    
    Args:
        request: GovernanceRequest to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Pydantic will validate structure, but we add business rules
        
        # Check actor accountability
        if not request.aim.actor.name or len(request.aim.actor.name.strip()) < 3:
            return False, "Actor name must be at least 3 characters (real person required)"
        
        # Check input sources
        if not request.aim.input.sources:
            return False, "At least one input source required to constrain AI behavior"
        
        # Check mission clarity
        if len(request.aim.mission.objective) < 10:
            return False, "Mission objective too vague (minimum 10 characters)"
        
        if not request.aim.mission.success_criteria:
            return False, "Mission must have at least one success criterion"
        
        # DRAG mode check (already validated by pydantic, but double-check)
        if request.drag_mode not in [DRAGMode.DRAFT, DRAGMode.RESEARCH, DRAGMode.GRUNT, DRAGMode.EXECUTE]:
            return False, "Invalid DRAG mode. Analysis is human-only."
        
        return True, None
        
    except Exception as e:
        return False, f"Validation error: {str(e)}"


# ============================================================================
# GOVERNANCE SUMMARY
# ============================================================================

def generate_governance_summary(request: GovernanceRequest) -> str:
    """
    Generate human-readable governance summary for logging/display.
    
    Example output:
        Governance Context:
        - Actor: Jake Smith (Product Lead)
        - Mission: Deploy updated application to staging
        - DRAG Mode: EXECUTE
        - Input Sources: 1 (slack_webhook)
        - Success Criteria: 3
    """
    return f"""Governance Context:
- Actor: {request.aim.actor.name} ({request.aim.actor.role})
- Mission: {request.aim.mission.objective[:80]}{'...' if len(request.aim.mission.objective) > 80 else ''}
- DRAG Mode: {request.drag_mode.value.upper()}
- Input Sources: {len(request.aim.input.sources)} ({', '.join(s.type for s in request.aim.input.sources[:3])})
- Success Criteria: {len(request.aim.mission.success_criteria)}
- Constraints: {len(request.aim.input.constraints)}"""
