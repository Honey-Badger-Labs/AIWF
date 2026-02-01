-- ============================================================================
-- AIWF SustainBot Database Schema
-- ============================================================================
--
-- Purpose: PostgreSQL schema for governance, audit, and user management
--
-- Features:
--   - User accounts with API keys
--   - Audit logs with integrity hashing
--   - Workflow execution history
--   - Governance tracking (AIM-DRAG)
--
-- ============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- USERS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'user', -- user, admin, sre, developer
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_login_at TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb,
    
    CONSTRAINT users_email_check CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    CONSTRAINT users_role_check CHECK (role IN ('user', 'admin', 'sre', 'developer', 'auditor'))
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_is_active ON users(is_active);

-- ============================================================================
-- API KEYS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_hash VARCHAR(128) UNIQUE NOT NULL, -- SHA-256 hash of the actual key
    name VARCHAR(100) NOT NULL, -- Human-readable name (e.g., "Production Bot")
    scopes TEXT[] DEFAULT ARRAY['read']::TEXT[], -- Permissions: read, write, admin
    is_active BOOLEAN DEFAULT true,
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    revoked_at TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb,
    
    CONSTRAINT api_keys_scopes_check CHECK (
        scopes <@ ARRAY['read', 'write', 'admin', 'governance', 'workflows']::TEXT[]
    )
);

CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_is_active ON api_keys(is_active);
CREATE INDEX idx_api_keys_expires_at ON api_keys(expires_at);

-- ============================================================================
-- AUDIT LOGS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trace_id UUID NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- AIM-DRAG Governance Context
    actor_name VARCHAR(255) NOT NULL,
    actor_email VARCHAR(255),
    actor_role VARCHAR(50),
    drag_mode VARCHAR(20) NOT NULL, -- draft, research, grunt, execute
    
    -- Workflow Execution
    workflow_name VARCHAR(100) NOT NULL,
    parameters JSONB DEFAULT '{}'::jsonb,
    outcome VARCHAR(20) NOT NULL, -- success, failure, rejected
    error TEXT,
    duration_seconds DECIMAL(10, 3),
    
    -- Input Constraints
    input_sources JSONB DEFAULT '[]'::jsonb,
    input_constraints JSONB DEFAULT '[]'::jsonb,
    
    -- Mission
    mission_objective TEXT,
    mission_success_criteria JSONB DEFAULT '[]'::jsonb,
    
    -- Integrity & Timestamps
    integrity_hash VARCHAR(64) NOT NULL, -- SHA-256 of all fields
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT audit_logs_drag_mode_check CHECK (drag_mode IN ('draft', 'research', 'grunt', 'execute')),
    CONSTRAINT audit_logs_outcome_check CHECK (outcome IN ('success', 'failure', 'rejected'))
);

CREATE INDEX idx_audit_logs_trace_id ON audit_logs(trace_id);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_actor_name ON audit_logs(actor_name);
CREATE INDEX idx_audit_logs_drag_mode ON audit_logs(drag_mode);
CREATE INDEX idx_audit_logs_workflow_name ON audit_logs(workflow_name);
CREATE INDEX idx_audit_logs_outcome ON audit_logs(outcome);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);
CREATE INDEX idx_audit_logs_integrity_hash ON audit_logs(integrity_hash);

-- ============================================================================
-- WORKFLOW EXECUTIONS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS workflow_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trace_id UUID NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    workflow_name VARCHAR(100) NOT NULL,
    parameters JSONB DEFAULT '{}'::jsonb,
    
    -- Execution Details
    status VARCHAR(20) NOT NULL, -- running, completed, failed, cancelled
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    duration_seconds DECIMAL(10, 3),
    
    -- Results
    result JSONB,
    error TEXT,
    
    -- Governance Link
    audit_log_id UUID REFERENCES audit_logs(id) ON DELETE SET NULL,
    
    CONSTRAINT workflow_executions_status_check CHECK (status IN ('running', 'completed', 'failed', 'cancelled'))
);

CREATE INDEX idx_workflow_executions_trace_id ON workflow_executions(trace_id);
CREATE INDEX idx_workflow_executions_user_id ON workflow_executions(user_id);
CREATE INDEX idx_workflow_executions_workflow_name ON workflow_executions(workflow_name);
CREATE INDEX idx_workflow_executions_status ON workflow_executions(status);
CREATE INDEX idx_workflow_executions_started_at ON workflow_executions(started_at DESC);

-- ============================================================================
-- GOVERNANCE METRICS TABLE (Historical)
-- ============================================================================

CREATE TABLE IF NOT EXISTS governance_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(15, 3) NOT NULL,
    drag_mode VARCHAR(20),
    actor_role VARCHAR(50),
    workflow_name VARCHAR(100),
    outcome VARCHAR(20),
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    labels JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_governance_metrics_metric_name ON governance_metrics(metric_name);
CREATE INDEX idx_governance_metrics_timestamp ON governance_metrics(timestamp DESC);
CREATE INDEX idx_governance_metrics_drag_mode ON governance_metrics(drag_mode);
CREATE INDEX idx_governance_metrics_workflow_name ON governance_metrics(workflow_name);

-- ============================================================================
-- VIEWS FOR REPORTING
-- ============================================================================

-- View: Recent Governance Activity
CREATE OR REPLACE VIEW v_recent_governance AS
SELECT 
    al.trace_id,
    al.actor_name,
    al.actor_role,
    al.drag_mode,
    al.workflow_name,
    al.outcome,
    al.duration_seconds,
    al.created_at,
    u.email AS user_email
FROM audit_logs al
LEFT JOIN users u ON al.user_id = u.id
ORDER BY al.created_at DESC
LIMIT 100;

-- View: Workflow Success Rate
CREATE OR REPLACE VIEW v_workflow_success_rate AS
SELECT 
    workflow_name,
    COUNT(*) AS total_executions,
    SUM(CASE WHEN outcome = 'success' THEN 1 ELSE 0 END) AS successful,
    SUM(CASE WHEN outcome = 'failure' THEN 1 ELSE 0 END) AS failed,
    SUM(CASE WHEN outcome = 'rejected' THEN 1 ELSE 0 END) AS rejected,
    ROUND(100.0 * SUM(CASE WHEN outcome = 'success' THEN 1 ELSE 0 END) / COUNT(*), 2) AS success_rate_pct,
    AVG(duration_seconds) AS avg_duration_seconds,
    MAX(created_at) AS last_execution
FROM audit_logs
GROUP BY workflow_name
ORDER BY total_executions DESC;

-- View: DRAG Mode Distribution
CREATE OR REPLACE VIEW v_drag_mode_distribution AS
SELECT 
    drag_mode,
    COUNT(*) AS total_requests,
    COUNT(DISTINCT actor_name) AS unique_actors,
    AVG(duration_seconds) AS avg_duration_seconds,
    SUM(CASE WHEN outcome = 'success' THEN 1 ELSE 0 END) AS successful,
    ROUND(100.0 * SUM(CASE WHEN outcome = 'success' THEN 1 ELSE 0 END) / COUNT(*), 2) AS success_rate_pct
FROM audit_logs
GROUP BY drag_mode
ORDER BY total_requests DESC;

-- View: User Activity Summary
CREATE OR REPLACE VIEW v_user_activity AS
SELECT 
    u.id,
    u.email,
    u.name,
    u.role,
    COUNT(al.id) AS total_workflows,
    MAX(al.created_at) AS last_activity,
    SUM(CASE WHEN al.outcome = 'success' THEN 1 ELSE 0 END) AS successful_workflows,
    SUM(CASE WHEN al.outcome = 'failure' THEN 1 ELSE 0 END) AS failed_workflows
FROM users u
LEFT JOIN audit_logs al ON u.id = al.user_id
GROUP BY u.id, u.email, u.name, u.role
ORDER BY total_workflows DESC;

-- ============================================================================
-- FUNCTIONS FOR INTEGRITY
-- ============================================================================

-- Function: Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: Auto-update users.updated_at
CREATE TRIGGER trigger_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- INITIAL DATA
-- ============================================================================

-- Create default admin user (for bootstrapping)
INSERT INTO users (email, name, role) 
VALUES ('admin@honeybadgerlabs.io', 'System Admin', 'admin')
ON CONFLICT (email) DO NOTHING;

-- ============================================================================
-- PERMISSIONS (Optional - for production deployments)
-- ============================================================================

-- Create read-only user for reporting/analytics
-- CREATE ROLE sustainbot_readonly;
-- GRANT CONNECT ON DATABASE sustainbot TO sustainbot_readonly;
-- GRANT USAGE ON SCHEMA public TO sustainbot_readonly;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO sustainbot_readonly;
-- GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO sustainbot_readonly;

-- Create application user with write access
-- CREATE ROLE sustainbot_app;
-- GRANT CONNECT ON DATABASE sustainbot TO sustainbot_app;
-- GRANT USAGE, CREATE ON SCHEMA public TO sustainbot_app;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO sustainbot_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO sustainbot_app;

-- ============================================================================
-- NOTES
-- ============================================================================

-- Performance Tuning:
--   - Regularly run VACUUM ANALYZE on audit_logs table
--   - Consider partitioning audit_logs by created_at (monthly)
--   - Monitor index usage with pg_stat_user_indexes
--   - Adjust shared_buffers and work_mem for workload

-- Backup Strategy:
--   - Daily pg_dump with compression
--   - Point-in-time recovery with WAL archiving
--   - Audit logs retention: 90 days minimum (compliance)
--   - Automated backups to S3/GCS with encryption

-- Security:
--   - Enable SSL connections in production
--   - Use connection pooling (PgBouncer recommended)
--   - Rotate API keys every 90 days
--   - Audit admin actions separately
