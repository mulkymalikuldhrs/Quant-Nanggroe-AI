-- =============================================================================
-- Agentic AI System - Database Initialization Script
-- PostgreSQL schema for the multi-agent intelligence platform
-- Loaded automatically via /docker-entrypoint-initdb.d/ on first container start
-- Made with love by Mulky Malikul Dhaher in Indonesia
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- Core Application Tables
-- =============================================================================

-- Agent configurations and registry
CREATE TABLE IF NOT EXISTS agents_config (
    id              SERIAL PRIMARY KEY,
    agent_id        VARCHAR(100) NOT NULL,
    name            VARCHAR(200) NOT NULL,
    capabilities_json  JSONB DEFAULT '[]'::jsonb,
    status          VARCHAR(50) DEFAULT 'ready',
    config_json     JSONB DEFAULT '{}'::jsonb,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT uq_agents_config_agent_id UNIQUE (agent_id),
    CONSTRAINT ck_agents_config_status CHECK (
        status IN ('ready', 'busy', 'error', 'offline', 'maintenance', 'deprecated')
    )
);

-- Workflow definitions
CREATE TABLE IF NOT EXISTS workflows (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,
    description     TEXT,
    steps_json      JSONB DEFAULT '[]'::jsonb,
    status          VARCHAR(50) DEFAULT 'draft',
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT ck_workflows_status CHECK (
        status IN ('draft', 'active', 'paused', 'archived', 'error')
    )
);

-- Workflow execution tracking
CREATE TABLE IF NOT EXISTS workflow_executions (
    id              SERIAL PRIMARY KEY,
    workflow_id     INTEGER NOT NULL,
    status          VARCHAR(50) DEFAULT 'pending',
    current_step    INTEGER DEFAULT 0,
    results_json    JSONB DEFAULT '{}'::jsonb,
    started_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at    TIMESTAMP WITH TIME ZONE,

    CONSTRAINT fk_workflow_executions_workflow
        FOREIGN KEY (workflow_id) REFERENCES workflows(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT ck_workflow_executions_status CHECK (
        status IN ('pending', 'running', 'completed', 'failed', 'cancelled', 'timed_out')
    )
);

-- API key management (encrypted storage)
CREATE TABLE IF NOT EXISTS api_keys (
    id              SERIAL PRIMARY KEY,
    provider        VARCHAR(100) NOT NULL,
    key_encrypted   TEXT NOT NULL,
    model           VARCHAR(200),
    status          VARCHAR(50) DEFAULT 'active',
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT ck_api_keys_status CHECK (
        status IN ('active', 'revoked', 'expired', 'rotated')
    )
);

-- Audit log for security and compliance
CREATE TABLE IF NOT EXISTS audit_log (
    id              SERIAL PRIMARY KEY,
    action          VARCHAR(200) NOT NULL,
    agent_id        VARCHAR(100),
    details_json    JSONB DEFAULT '{}'::jsonb,
    timestamp       TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    user_id         VARCHAR(100),

    CONSTRAINT ck_audit_log_action CHECK (action <> '')
);

-- System-wide settings (key-value store)
CREATE TABLE IF NOT EXISTS system_settings (
    key             VARCHAR(200) PRIMARY KEY,
    value           TEXT NOT NULL,
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================================================
-- Extended Application Tables (aligned with SQLAlchemy models)
-- =============================================================================

-- Agent registry (mirrors SQLAlchemy Agent model)
CREATE TABLE IF NOT EXISTS agents (
    id              SERIAL PRIMARY KEY,
    agent_id        VARCHAR(100) NOT NULL,
    name            VARCHAR(200) NOT NULL,
    status          VARCHAR(50) DEFAULT 'ready',
    capabilities    JSONB DEFAULT '[]'::jsonb,
    config          JSONB DEFAULT '{}'::jsonb,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT uq_agents_agent_id UNIQUE (agent_id),
    CONSTRAINT ck_agents_status CHECK (
        status IN ('ready', 'busy', 'error', 'offline', 'maintenance')
    )
);

-- Task tracking
CREATE TABLE IF NOT EXISTS tasks (
    id              SERIAL PRIMARY KEY,
    task_id         VARCHAR(100) NOT NULL,
    agent_id        VARCHAR(100) NOT NULL,
    status          VARCHAR(50) DEFAULT 'pending',
    priority        VARCHAR(20) DEFAULT 'medium',
    request         TEXT NOT NULL,
    context         JSONB DEFAULT '{}'::jsonb,
    result          JSONB DEFAULT '{}'::jsonb,
    error_message   TEXT,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at      TIMESTAMP WITH TIME ZONE,
    completed_at    TIMESTAMP WITH TIME ZONE,

    CONSTRAINT uq_tasks_task_id UNIQUE (task_id),
    CONSTRAINT fk_tasks_agent
        FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT ck_tasks_status CHECK (
        status IN ('pending', 'running', 'completed', 'failed', 'cancelled')
    ),
    CONSTRAINT ck_tasks_priority CHECK (
        priority IN ('low', 'medium', 'high', 'urgent')
    )
);

-- Agent memories and experiences
CREATE TABLE IF NOT EXISTS memories (
    id              SERIAL PRIMARY KEY,
    memory_id       VARCHAR(100) NOT NULL,
    agent_id        VARCHAR(100) NOT NULL,
    type            VARCHAR(50) NOT NULL,
    content         JSONB NOT NULL,
    metadata        JSONB DEFAULT '{}'::jsonb,
    importance      REAL DEFAULT 0.5,
    accessed_count  INTEGER DEFAULT 0,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_accessed   TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT uq_memories_memory_id UNIQUE (memory_id),
    CONSTRAINT fk_memories_agent
        FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT ck_memories_type CHECK (
        type IN ('task', 'interaction', 'learning', 'system', 'error')
    )
);

-- Workflow definitions (extended with workflow_id)
CREATE TABLE IF NOT EXISTS workflow_definitions (
    id              SERIAL PRIMARY KEY,
    workflow_id     VARCHAR(100) NOT NULL,
    name            VARCHAR(200) NOT NULL,
    description     TEXT,
    definition      JSONB NOT NULL,
    status          VARCHAR(50) DEFAULT 'draft',
    created_by      VARCHAR(100),
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT uq_workflow_definitions_workflow_id UNIQUE (workflow_id),
    CONSTRAINT ck_workflow_definitions_status CHECK (
        status IN ('draft', 'active', 'paused', 'archived')
    )
);

-- Workflow execution details
CREATE TABLE IF NOT EXISTS workflow_execution_details (
    id              SERIAL PRIMARY KEY,
    execution_id    VARCHAR(100) NOT NULL,
    workflow_id     VARCHAR(100) NOT NULL,
    status          VARCHAR(50) DEFAULT 'running',
    input_data      JSONB DEFAULT '{}'::jsonb,
    output_data     JSONB DEFAULT '{}'::jsonb,
    current_step    INTEGER DEFAULT 0,
    total_steps     INTEGER DEFAULT 0,
    error_message   TEXT,
    started_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at    TIMESTAMP WITH TIME ZONE,

    CONSTRAINT uq_workflow_execution_details_execution_id UNIQUE (execution_id),
    CONSTRAINT fk_workflow_execution_details_workflow
        FOREIGN KEY (workflow_id) REFERENCES workflow_definitions(workflow_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT ck_workflow_execution_details_status CHECK (
        status IN ('running', 'completed', 'failed', 'cancelled')
    )
);

-- Individual workflow step tracking
CREATE TABLE IF NOT EXISTS workflow_steps (
    id              SERIAL PRIMARY KEY,
    step_id         VARCHAR(100) NOT NULL,
    execution_id    VARCHAR(100) NOT NULL,
    agent_id        VARCHAR(100) NOT NULL,
    step_number     INTEGER NOT NULL,
    status          VARCHAR(50) DEFAULT 'pending',
    input_data      JSONB DEFAULT '{}'::jsonb,
    output_data     JSONB DEFAULT '{}'::jsonb,
    error_message   TEXT,
    started_at      TIMESTAMP WITH TIME ZONE,
    completed_at    TIMESTAMP WITH TIME ZONE,

    CONSTRAINT fk_workflow_steps_execution
        FOREIGN KEY (execution_id) REFERENCES workflow_execution_details(execution_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT ck_workflow_steps_status CHECK (
        status IN ('pending', 'running', 'completed', 'failed', 'skipped')
    )
);

-- Deployment tracking
CREATE TABLE IF NOT EXISTS deployments (
    id              SERIAL PRIMARY KEY,
    deployment_id   VARCHAR(100) NOT NULL,
    platform        VARCHAR(50) NOT NULL,
    app_name        VARCHAR(200) NOT NULL,
    environment     VARCHAR(50) DEFAULT 'production',
    status          VARCHAR(50) DEFAULT 'deploying',
    url             VARCHAR(500),
    config          JSONB DEFAULT '{}'::jsonb,
    logs            JSONB DEFAULT '[]'::jsonb,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at    TIMESTAMP WITH TIME ZONE,

    CONSTRAINT uq_deployments_deployment_id UNIQUE (deployment_id),
    CONSTRAINT ck_deployments_platform CHECK (
        platform IN ('netlify', 'vercel', 'railway', 'docker', 'aws', 'gcp', 'heroku')
    ),
    CONSTRAINT ck_deployments_status CHECK (
        status IN ('deploying', 'deployed', 'failed', 'destroyed')
    )
);

-- System metrics for monitoring
CREATE TABLE IF NOT EXISTS system_metrics (
    id              SERIAL PRIMARY KEY,
    metric_type     VARCHAR(50) NOT NULL,
    component       VARCHAR(100) NOT NULL,
    value           DOUBLE PRECISION NOT NULL,
    unit            VARCHAR(20),
    metadata        JSONB DEFAULT '{}'::jsonb,
    timestamp       TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT ck_system_metrics_metric_type CHECK (metric_type <> '')
);

-- Knowledge base for RAG and context injection
CREATE TABLE IF NOT EXISTS knowledge_entries (
    id              SERIAL PRIMARY KEY,
    entry_id        VARCHAR(100) NOT NULL,
    title           VARCHAR(500) NOT NULL,
    content         TEXT NOT NULL,
    category        VARCHAR(100) NOT NULL,
    tags            JSONB DEFAULT '[]'::jsonb,
    embedding       JSONB,
    source          VARCHAR(500),
    relevance_score REAL DEFAULT 0.0,
    access_count    INTEGER DEFAULT 0,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT uq_knowledge_entries_entry_id UNIQUE (entry_id)
);

-- User session management
CREATE TABLE IF NOT EXISTS user_sessions (
    id              SERIAL PRIMARY KEY,
    session_id      VARCHAR(100) NOT NULL,
    user_id         VARCHAR(100),
    ip_address      VARCHAR(45),
    user_agent      VARCHAR(500),
    data            JSONB DEFAULT '{}'::jsonb,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity   TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at      TIMESTAMP WITH TIME ZONE,

    CONSTRAINT uq_user_sessions_session_id UNIQUE (session_id)
);

-- API request logging
CREATE TABLE IF NOT EXISTS api_logs (
    id              SERIAL PRIMARY KEY,
    request_id      VARCHAR(100) NOT NULL,
    endpoint        VARCHAR(200) NOT NULL,
    method          VARCHAR(10) NOT NULL,
    status_code     INTEGER NOT NULL,
    response_time   DOUBLE PRECISION NOT NULL,
    user_agent      VARCHAR(500),
    ip_address      VARCHAR(45),
    request_data    JSONB DEFAULT '{}'::jsonb,
    response_data   JSONB DEFAULT '{}'::jsonb,
    timestamp       TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT uq_api_logs_request_id UNIQUE (request_id),
    CONSTRAINT ck_api_logs_method CHECK (
        method IN ('GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS')
    )
);

-- =============================================================================
-- Indexes for Performance
-- =============================================================================

-- agents_config indexes
CREATE INDEX IF NOT EXISTS idx_agents_config_agent_id ON agents_config(agent_id);
CREATE INDEX IF NOT EXISTS idx_agents_config_status ON agents_config(status);
CREATE INDEX IF NOT EXISTS idx_agents_config_name ON agents_config(name);

-- workflows indexes
CREATE INDEX IF NOT EXISTS idx_workflows_status ON workflows(status);
CREATE INDEX IF NOT EXISTS idx_workflows_name ON workflows(name);

-- workflow_executions indexes
CREATE INDEX IF NOT EXISTS idx_workflow_executions_workflow_id ON workflow_executions(workflow_id);
CREATE INDEX IF NOT EXISTS idx_workflow_executions_status ON workflow_executions(status);
CREATE INDEX IF NOT EXISTS idx_workflow_executions_started_at ON workflow_executions(started_at);

-- api_keys indexes
CREATE INDEX IF NOT EXISTS idx_api_keys_provider ON api_keys(provider);
CREATE INDEX IF NOT EXISTS idx_api_keys_status ON api_keys(status);

-- audit_log indexes
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_log_agent_id ON audit_log(agent_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log(user_id);

-- system_settings indexes (primary key on `key` serves as index)

-- agents indexes
CREATE INDEX IF NOT EXISTS idx_agents_agent_id ON agents(agent_id);
CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);

-- tasks indexes
CREATE INDEX IF NOT EXISTS idx_tasks_task_id ON tasks(task_id);
CREATE INDEX IF NOT EXISTS idx_tasks_agent_id ON tasks(agent_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at);

-- memories indexes
CREATE INDEX IF NOT EXISTS idx_memories_memory_id ON memories(memory_id);
CREATE INDEX IF NOT EXISTS idx_memories_agent_id ON memories(agent_id);
CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type);
CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance);

-- workflow_definitions indexes
CREATE INDEX IF NOT EXISTS idx_workflow_definitions_workflow_id ON workflow_definitions(workflow_id);
CREATE INDEX IF NOT EXISTS idx_workflow_definitions_status ON workflow_definitions(status);

-- workflow_execution_details indexes
CREATE INDEX IF NOT EXISTS idx_workflow_execution_details_execution_id ON workflow_execution_details(execution_id);
CREATE INDEX IF NOT EXISTS idx_workflow_execution_details_workflow_id ON workflow_execution_details(workflow_id);
CREATE INDEX IF NOT EXISTS idx_workflow_execution_details_status ON workflow_execution_details(status);

-- workflow_steps indexes
CREATE INDEX IF NOT EXISTS idx_workflow_steps_execution_id ON workflow_steps(execution_id);
CREATE INDEX IF NOT EXISTS idx_workflow_steps_status ON workflow_steps(status);

-- deployments indexes
CREATE INDEX IF NOT EXISTS idx_deployments_deployment_id ON deployments(deployment_id);
CREATE INDEX IF NOT EXISTS idx_deployments_platform ON deployments(platform);
CREATE INDEX IF NOT EXISTS idx_deployments_status ON deployments(status);

-- system_metrics indexes
CREATE INDEX IF NOT EXISTS idx_system_metrics_metric_type ON system_metrics(metric_type);
CREATE INDEX IF NOT EXISTS idx_system_metrics_component ON system_metrics(component);
CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics(timestamp);

-- knowledge_entries indexes
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_entry_id ON knowledge_entries(entry_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_category ON knowledge_entries(category);
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_source ON knowledge_entries(source);
-- GIN index for fast JSON tag lookups
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_tags ON knowledge_entries USING GIN (tags);

-- user_sessions indexes
CREATE INDEX IF NOT EXISTS idx_user_sessions_session_id ON user_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at ON user_sessions(expires_at);

-- api_logs indexes
CREATE INDEX IF NOT EXISTS idx_api_logs_request_id ON api_logs(request_id);
CREATE INDEX IF NOT EXISTS idx_api_logs_endpoint ON api_logs(endpoint);
CREATE INDEX IF NOT EXISTS idx_api_logs_method ON api_logs(method);
CREATE INDEX IF NOT EXISTS idx_api_logs_status_code ON api_logs(status_code);
CREATE INDEX IF NOT EXISTS idx_api_logs_timestamp ON api_logs(timestamp);

-- =============================================================================
-- Seed Data: Default System Settings
-- =============================================================================

INSERT INTO system_settings (key, value, updated_at) VALUES
    ('system_name',          '"Agentic AI System"',                        NOW()),
    ('system_version',       '"2.0.0"',                                    NOW()),
    ('max_concurrent_agents', '10',                                         NOW()),
    ('default_llm_provider', '"openrouter"',                               NOW()),
    ('scheduler_enabled',    'true',                                        NOW()),
    ('sync_engine_enabled',  'true',                                        NOW()),
    ('web_interface_enabled','true',                                        NOW()),
    ('websocket_enabled',    'true',                                        NOW()),
    ('rate_limit_per_minute','60',                                          NOW()),
    ('session_timeout_minutes', '30',                                       NOW()),
    ('log_level',            '"INFO"',                                      NOW()),
    ('audit_retention_days', '90',                                          NOW()),
    ('max_workflow_retries',  '3',                                          NOW()),
    ('agent_healthcheck_interval_seconds', '30',                            NOW()),
    ('default_task_timeout_seconds', '300',                                  NOW())
ON CONFLICT (key) DO NOTHING;

-- =============================================================================
-- Updated_at Trigger Function
-- Automatically updates the updated_at column on row modification
-- =============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at triggers to all tables with that column
DO $$
DECLARE
    t TEXT;
BEGIN
    FOR t IN
        SELECT table_name FROM information_schema.columns
        WHERE column_name = 'updated_at'
          AND table_schema = 'public'
          AND table_name IN (
              'agents_config', 'workflows', 'agents', 'workflow_definitions',
              'knowledge_entries'
          )
    LOOP
        EXECUTE format(
            'CREATE TRIGGER set_updated_at
             BEFORE UPDATE ON %I
             FOR EACH ROW
             EXECUTE FUNCTION update_updated_at_column()',
            t
        );
    END LOOP;
END;
$$;

-- =============================================================================
-- Helper Functions
-- =============================================================================

-- Purge expired sessions
CREATE OR REPLACE FUNCTION purge_expired_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM user_sessions
    WHERE expires_at IS NOT NULL AND expires_at < NOW();
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Purge old audit log entries
CREATE OR REPLACE FUNCTION purge_old_audit_logs(retention_days INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM audit_log
    WHERE timestamp < NOW() - (retention_days || ' days')::INTERVAL;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Get system health summary
CREATE OR REPLACE FUNCTION get_system_health_summary()
RETURNS TABLE(
    total_agents       INTEGER,
    active_agents      INTEGER,
    pending_tasks      INTEGER,
    running_workflows  INTEGER,
    total_deployments  INTEGER,
    active_api_keys    INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        (SELECT COUNT(*) FROM agents)::INTEGER,
        (SELECT COUNT(*) FROM agents WHERE status = 'ready')::INTEGER,
        (SELECT COUNT(*) FROM tasks WHERE status = 'pending')::INTEGER,
        (SELECT COUNT(*) FROM workflow_executions WHERE status = 'running')::INTEGER,
        (SELECT COUNT(*) FROM deployments WHERE status = 'deployed')::INTEGER,
        (SELECT COUNT(*) FROM api_keys WHERE status = 'active')::INTEGER;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Completion Marker
-- =============================================================================

-- Insert a marker row to confirm initialization completed
INSERT INTO audit_log (action, agent_id, details_json, user_id)
VALUES (
    'database_initialized',
    'system',
    '{"message": "Database schema initialized successfully", "version": "2.0.0"}'::jsonb,
    'system'
);
