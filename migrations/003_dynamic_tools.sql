-- Dynamic Tools Migration
-- Enables self-extending AI agent capabilities
-- Allows agent to create, persist, and manage its own tools at runtime

-- ==========================================
-- Core Dynamic Tools Table
-- ==========================================

CREATE TABLE IF NOT EXISTS dynamic_tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_name VARCHAR(100) UNIQUE NOT NULL,
    tool_type VARCHAR(20) NOT NULL,           -- 'read' or 'write'
    description TEXT NOT NULL,
    parameters_schema JSONB NOT NULL,         -- JSON Schema for parameters
    return_schema JSONB NOT NULL,             -- Expected return type schema
    function_code TEXT NOT NULL,              -- Python function code
    enabled BOOLEAN DEFAULT true,
    version INTEGER DEFAULT 1,
    created_by VARCHAR(50) DEFAULT 'system',  -- 'system' or 'user_id'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,
    usage_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0
);

COMMENT ON TABLE dynamic_tools IS 'Stores dynamically created agent tools with versioning and usage tracking';
COMMENT ON COLUMN dynamic_tools.tool_type IS 'Classification: read (queries) or write (mutations)';
COMMENT ON COLUMN dynamic_tools.function_code IS 'Python async function code as string';


-- ==========================================
-- Tool Version History (Rollback Support)
-- ==========================================

CREATE TABLE IF NOT EXISTS dynamic_tool_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_id UUID NOT NULL REFERENCES dynamic_tools(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    function_code TEXT NOT NULL,
    change_summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tool_id, version)
);

COMMENT ON TABLE dynamic_tool_versions IS 'Version history for tool rollback capability';


-- ==========================================
-- Tool Execution Audit Trail
-- ==========================================

CREATE TABLE IF NOT EXISTS dynamic_tool_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_id UUID NOT NULL REFERENCES dynamic_tools(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    execution_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    parameters JSONB,
    result JSONB,
    success BOOLEAN,
    error_message TEXT,
    execution_time_ms INTEGER
);

COMMENT ON TABLE dynamic_tool_executions IS 'Audit log of all tool executions with timing and results';


-- ==========================================
-- Tool Approval Workflow (Write Operations)
-- ==========================================

CREATE TABLE IF NOT EXISTS dynamic_tool_approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_id UUID NOT NULL REFERENCES dynamic_tools(id) ON DELETE CASCADE,
    requested_by VARCHAR(255) NOT NULL,
    request_message TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',     -- 'pending', 'approved', 'rejected'
    admin_user_id VARCHAR(255),
    admin_response_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE dynamic_tool_approvals IS 'Approval workflow for write/destructive operations';


-- ==========================================
-- Performance Indexes
-- ==========================================

-- Tool lookups by status
CREATE INDEX IF NOT EXISTS idx_dynamic_tools_enabled
    ON dynamic_tools(enabled);

-- Tool filtering by type
CREATE INDEX IF NOT EXISTS idx_dynamic_tools_type
    ON dynamic_tools(tool_type);

-- User execution history
CREATE INDEX IF NOT EXISTS idx_dynamic_tool_executions_user
    ON dynamic_tool_executions(user_id, execution_timestamp DESC);

-- Pending approvals
CREATE INDEX IF NOT EXISTS idx_dynamic_tool_approvals_status
    ON dynamic_tool_approvals(status, created_at DESC);

-- Tool version lookups
CREATE INDEX IF NOT EXISTS idx_dynamic_tool_versions_tool
    ON dynamic_tool_versions(tool_id, version DESC);


-- ==========================================
-- Triggers for Timestamp Management
-- ==========================================

-- Update timestamp trigger for dynamic_tools
CREATE TRIGGER update_dynamic_tools_updated_at
    BEFORE UPDATE ON dynamic_tools
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ==========================================
-- Initial Data / Examples
-- ==========================================

-- No initial data - tools will be created dynamically by the agent
