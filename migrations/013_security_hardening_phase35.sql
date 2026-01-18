-- Migration 013: Security Hardening (Phase 3.5)
-- Tables for audit logging and security event monitoring

-- ==========================================
-- Security Events Table
-- ==========================================

CREATE TABLE IF NOT EXISTS tool_security_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT NOT NULL CHECK (event_type IN (
        'validation_failure',
        'sandbox_violation',
        'rate_limit_exceeded',
        'timeout_exceeded',
        'resource_limit_exceeded',
        'suspicious_pattern',
        'compilation_error'
    )),
    tool_id UUID REFERENCES dynamic_tools(id),
    user_id TEXT NOT NULL,
    code_snippet TEXT,  -- Truncated code for analysis
    error_details JSONB,  -- Structured error information
    severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX idx_security_events_user ON tool_security_events(user_id, created_at DESC);
CREATE INDEX idx_security_events_severity ON tool_security_events(severity, created_at DESC);
CREATE INDEX idx_security_events_type ON tool_security_events(event_type, created_at DESC);
CREATE INDEX idx_security_events_tool ON tool_security_events(tool_id, created_at DESC);

COMMENT ON TABLE tool_security_events IS 'Audit log of security events for dynamic tool system';
COMMENT ON COLUMN tool_security_events.event_type IS 'Type of security event detected';
COMMENT ON COLUMN tool_security_events.severity IS 'Severity level: low, medium, high, critical';
COMMENT ON COLUMN tool_security_events.error_details IS 'JSON details about the security event';

-- ==========================================
-- Rate Limiting Table
-- ==========================================

CREATE TABLE IF NOT EXISTS rate_limit_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    action_type TEXT NOT NULL CHECK (action_type IN ('tool_creation', 'tool_execution')),
    action_count INT DEFAULT 1,
    window_start TIMESTAMPTZ NOT NULL,
    window_end TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for rate limit checking
CREATE INDEX idx_rate_limit_user_action ON rate_limit_tracking(
    user_id,
    action_type,
    window_end DESC
);
CREATE INDEX idx_rate_limit_cleanup ON rate_limit_tracking(window_end);

COMMENT ON TABLE rate_limit_tracking IS 'Track rate limits for tool creation and execution';
COMMENT ON COLUMN rate_limit_tracking.action_type IS 'Type of action: tool_creation or tool_execution';
COMMENT ON COLUMN rate_limit_tracking.window_start IS 'Start of rate limit time window';
COMMENT ON COLUMN rate_limit_tracking.window_end IS 'End of rate limit time window';

-- ==========================================
-- Tool Execution Enhancements
-- ==========================================

-- Add security-related columns to existing tool_executions table
ALTER TABLE tool_executions
ADD COLUMN IF NOT EXISTS security_violation BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS timeout_occurred BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS resource_usage JSONB;  -- CPU, memory stats

COMMENT ON COLUMN tool_executions.security_violation IS 'True if execution triggered security violation';
COMMENT ON COLUMN tool_executions.timeout_occurred IS 'True if execution exceeded timeout';
COMMENT ON COLUMN tool_executions.resource_usage IS 'Resource usage statistics (CPU, memory)';

-- ==========================================
-- Tool Metadata Enhancements
-- ==========================================

-- Add security-related metadata to dynamic_tools table
ALTER TABLE dynamic_tools
ADD COLUMN IF NOT EXISTS validation_version TEXT DEFAULT 'legacy',
ADD COLUMN IF NOT EXISTS last_security_scan TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS security_violations_count INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS auto_disabled_reason TEXT;

COMMENT ON COLUMN dynamic_tools.validation_version IS 'Version of security validation used (legacy, phase35, etc)';
COMMENT ON COLUMN dynamic_tools.last_security_scan IS 'Last time tool was scanned for security issues';
COMMENT ON COLUMN dynamic_tools.security_violations_count IS 'Count of security violations during execution';
COMMENT ON COLUMN dynamic_tools.auto_disabled_reason IS 'Reason if tool was automatically disabled for security';

-- ==========================================
-- Cleanup Function (for expired rate limits)
-- ==========================================

CREATE OR REPLACE FUNCTION cleanup_expired_rate_limits()
RETURNS void AS $$
BEGIN
    DELETE FROM rate_limit_tracking
    WHERE window_end < NOW() - INTERVAL '7 days';
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_expired_rate_limits IS 'Remove rate limit records older than 7 days';

-- ==========================================
-- Security Event Aggregation View
-- ==========================================

CREATE OR REPLACE VIEW security_events_summary AS
SELECT
    event_type,
    severity,
    COUNT(*) as event_count,
    COUNT(DISTINCT user_id) as affected_users,
    COUNT(DISTINCT tool_id) as affected_tools,
    DATE_TRUNC('hour', created_at) as hour,
    MIN(created_at) as first_occurrence,
    MAX(created_at) as last_occurrence
FROM tool_security_events
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY event_type, severity, DATE_TRUNC('hour', created_at)
ORDER BY hour DESC, event_count DESC;

COMMENT ON VIEW security_events_summary IS 'Hourly aggregation of security events for monitoring dashboard';

-- ==========================================
-- User Security Risk Score View
-- ==========================================

CREATE OR REPLACE VIEW user_security_risk_scores AS
SELECT
    user_id,
    COUNT(*) as total_events,
    COUNT(*) FILTER (WHERE severity = 'critical') as critical_events,
    COUNT(*) FILTER (WHERE severity = 'high') as high_events,
    COUNT(*) FILTER (WHERE severity = 'medium') as medium_events,
    COUNT(*) FILTER (WHERE severity = 'low') as low_events,
    -- Risk score: critical=10, high=5, medium=2, low=1
    (
        COUNT(*) FILTER (WHERE severity = 'critical') * 10 +
        COUNT(*) FILTER (WHERE severity = 'high') * 5 +
        COUNT(*) FILTER (WHERE severity = 'medium') * 2 +
        COUNT(*) FILTER (WHERE severity = 'low') * 1
    ) as risk_score,
    MAX(created_at) as last_event
FROM tool_security_events
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY user_id
ORDER BY risk_score DESC;

COMMENT ON VIEW user_security_risk_scores IS 'Calculate security risk scores per user based on recent events';

-- ==========================================
-- Grant Permissions (adjust as needed)
-- ==========================================

-- Grant read access to app user
-- GRANT SELECT ON tool_security_events TO app_user;
-- GRANT SELECT, INSERT ON tool_security_events TO app_user;
-- GRANT SELECT, INSERT, UPDATE ON rate_limit_tracking TO app_user;
-- GRANT SELECT ON security_events_summary TO app_user;
-- GRANT SELECT ON user_security_risk_scores TO app_user;
