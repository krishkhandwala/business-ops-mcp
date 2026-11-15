import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_uuid() -> str:
    return str(uuid.uuid4())


# ==============================================================================
# 1. ORGANIZATION & ACCESS CONTROL MODELS
# ==============================================================================


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True, default=new_uuid)
    name = Column(String(255), nullable=False)
    slug = Column(String(120), nullable=False, unique=True, index=True)
    domain = Column(String(255), nullable=True)
    plan_tier = Column(String(50), nullable=False, default="enterprise")
    approval_policy = Column(
        JSON,
        nullable=False,
        default=lambda: {
            "require_approval_for_high_risk": True,
            "require_approval_for_low_risk": False,
            "allowed_approver_roles": ["OWNER", "ADMIN", "OPERATOR"],
            "max_auto_tool_calls": 10,
        },
    )
    settings_json = Column(JSON, nullable=False, default=dict)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    members = relationship(
        "OrganizationMember", back_populates="organization", cascade="all, delete-orphan"
    )


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=new_uuid)
    email = Column(String(255), nullable=False, unique=True, index=True)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    avatar_url = Column(String(512), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    refresh_token_jti = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    memberships = relationship(
        "OrganizationMember", back_populates="user", cascade="all, delete-orphan"
    )


class Role(Base):
    __tablename__ = "roles"

    id = Column(String(36), primary_key=True, default=new_uuid)
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = Column(String(64), nullable=False)  # OWNER, ADMIN, OPERATOR, VIEWER
    description = Column(String(512), nullable=True)
    is_system = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_org_role_name"),
    )


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(String(36), primary_key=True, default=new_uuid)
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_name = Column(String(64), nullable=False, index=True)
    resource = Column(String(120), nullable=False)  # mcp_servers, tools, workflows, approvals, analytics, org
    action = Column(String(64), nullable=False)  # read, write, execute, approve, manage
    allowed = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class OrganizationMember(Base):
    __tablename__ = "organization_members"

    id = Column(String(36), primary_key=True, default=new_uuid)
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role = Column(String(64), nullable=False, default="OPERATOR")  # OWNER, ADMIN, OPERATOR, VIEWER
    status = Column(String(32), nullable=False, default="active")  # active, invited, suspended
    invited_by_email = Column(String(255), nullable=True)
    joined_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    organization = relationship("Organization", back_populates="members")
    user = relationship("User", back_populates="memberships")

    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_org_user_member"),
    )


# ==============================================================================
# 2. MCP INFRASTRUCTURE & TOOL REGISTRY MODELS
# ==============================================================================


class MCPServerModel(Base):
    __tablename__ = "mcp_servers"

    id = Column(String(36), primary_key=True, default=new_uuid)
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = Column(String(150), nullable=False)
    slug = Column(String(150), nullable=False, index=True)
    domain = Column(String(80), nullable=False)  # recruitment, employee, finance, analytics, custom
    description = Column(Text, nullable=True)
    transport_type = Column(String(40), nullable=False, default="stdio")  # stdio, streamable_http, in_process
    endpoint = Column(String(512), nullable=False)
    auth_method = Column(String(50), nullable=False, default="internal_token")  # none, bearer, api_key, internal_token
    encrypted_credentials = Column(Text, nullable=True)  # Encrypted via Fernet
    status = Column(String(40), nullable=False, default="connected")  # connected, disconnected, error
    health_status = Column(String(40), nullable=False, default="healthy")  # healthy, degraded, unreachable
    last_connected_at = Column(DateTime(timezone=True), default=utcnow, nullable=True)
    last_error = Column(Text, nullable=True)
    is_enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    tools = relationship(
        "MCPToolModel", back_populates="server", cascade="all, delete-orphan"
    )
    connections = relationship(
        "MCPConnection", back_populates="server", cascade="all, delete-orphan"
    )


class MCPConnection(Base):
    __tablename__ = "mcp_connections"

    id = Column(String(36), primary_key=True, default=new_uuid)
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mcp_server_id = Column(
        String(36), ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id = Column(String(120), nullable=False)
    transport_type = Column(String(40), nullable=False)
    status = Column(String(40), nullable=False, default="active")
    latency_ms = Column(Float, nullable=True, default=4.2)
    protocol_version = Column(String(40), nullable=False, default="2025-11-25")
    connected_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    disconnected_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)

    server = relationship("MCPServerModel", back_populates="connections")


class MCPToolModel(Base):
    __tablename__ = "mcp_tools"

    id = Column(String(36), primary_key=True, default=new_uuid)
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mcp_server_id = Column(
        String(36), ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tool_name = Column(String(150), nullable=False, index=True)
    display_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    input_schema = Column(JSON, nullable=False, default=dict)
    output_schema = Column(JSON, nullable=False, default=dict)
    risk_classification = Column(
        String(40), nullable=False, default="READ"
    )  # READ, LOW_RISK_WRITE, HIGH_RISK_WRITE
    required_roles = Column(
        JSON, nullable=False, default=lambda: ["OWNER", "ADMIN", "OPERATOR", "VIEWER"]
    )
    requires_approval = Column(Boolean, default=False, nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)
    invocation_count = Column(Integer, default=0, nullable=False)
    last_invoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    server = relationship("MCPServerModel", back_populates="tools")

    __table_args__ = (
        UniqueConstraint(
            "organization_id", "mcp_server_id", "tool_name", name="uq_org_server_tool"
        ),
    )


# ==============================================================================
# 3. INTEGRATIONS MARKETPLACE MODELS
# ==============================================================================


class Integration(Base):
    __tablename__ = "integrations"

    id = Column(String(36), primary_key=True, default=new_uuid)
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider_key = Column(String(80), nullable=False, index=True)  # postgresql, custom_rest, slack, gmail, google_sheets, notion, mysql, fastapi_internal
    name = Column(String(150), nullable=False)
    category = Column(String(80), nullable=False)  # Databases, Custom APIs, Communication, HRMS, Recruitment, Finance, CRM, Project Management, Developer Tools
    description = Column(Text, nullable=False)
    status = Column(String(40), nullable=False, default="disconnected")  # connected, disconnected, error
    config_schema = Column(JSON, nullable=False, default=dict)
    public_config = Column(JSON, nullable=False, default=dict)
    available_tools = Column(JSON, nullable=False, default=list)
    permissions_scope = Column(JSON, nullable=False, default=list)
    linked_mcp_server_id = Column(String(36), nullable=True)
    connected_by_user_id = Column(String(36), nullable=True)
    last_tested_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    credentials = relationship(
        "IntegrationCredential",
        back_populates="integration",
        cascade="all, delete-orphan",
    )


class IntegrationCredential(Base):
    __tablename__ = "integration_credentials"

    id = Column(String(36), primary_key=True, default=new_uuid)
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    integration_id = Column(
        String(36), ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    auth_type = Column(String(50), nullable=False, default="connection_string")  # connection_string, api_key, oauth2, bearer
    encrypted_payload = Column(Text, nullable=False)  # Fernet ciphertext only
    key_hint = Column(String(32), nullable=True)  # e.g., "...5432/nexus"
    rotated_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    integration = relationship("Integration", back_populates="credentials")


# ==============================================================================
# 4. CONVERSATIONS, AGENTS, EXECUTIONS & HUMAN APPROVAL MODELS
# ==============================================================================


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=new_uuid)
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title = Column(String(255), nullable=False, default="New Operations Session")
    status = Column(String(40), nullable=False, default="active")  # active, archived
    context_metadata = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=new_uuid)
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conversation_id = Column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role = Column(String(32), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    structured_data = Column(JSON, nullable=True)  # tables, cards, charts, execution summary
    agent_execution_id = Column(String(36), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    conversation = relationship("Conversation", back_populates="messages")


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String(36), primary_key=True, default=new_uuid)
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = Column(String(150), nullable=False)
    role_description = Column(Text, nullable=False)
    llm_model = Column(String(100), nullable=False, default="gpt-4o-mini")
    allowed_domains = Column(JSON, nullable=False, default=list)
    max_steps = Column(Integer, nullable=False, default=10)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class AgentExecution(Base):
    __tablename__ = "agent_executions"

    id = Column(String(36), primary_key=True, default=new_uuid)
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conversation_id = Column(
        String(36), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    agent_id = Column(String(36), nullable=True)
    user_prompt = Column(Text, nullable=False)
    intent = Column(String(120), nullable=False, default="general_operation")
    status = Column(
        String(40), nullable=False, default="running", index=True
    )  # running, awaiting_approval, completed, failed, rejected, cancelled
    execution_plan = Column(JSON, nullable=False, default=list)
    checkpoint_state = Column(JSON, nullable=False, default=dict)
    final_summary = Column(Text, nullable=True)
    structured_result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    idempotency_key = Column(String(120), nullable=True, index=True)
    duration_ms = Column(Float, nullable=True, default=0.0)
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    estimated_cost_usd = Column(Float, nullable=False, default=0.0)
    started_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    steps = relationship(
        "ExecutionStep", back_populates="execution", cascade="all, delete-orphan"
    )
    tool_invocations = relationship(
        "ToolInvocation", back_populates="execution", cascade="all, delete-orphan"
    )
    approvals = relationship(
        "ApprovalRequest", back_populates="execution", cascade="all, delete-orphan"
    )


class ExecutionStep(Base):
    __tablename__ = "execution_steps"

    id = Column(String(36), primary_key=True, default=new_uuid)
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_execution_id = Column(
        String(36), ForeignKey("agent_executions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_number = Column(Integer, nullable=False)
    node_name = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    status = Column(String(40), nullable=False, default="completed")  # running, completed, awaiting_approval, failed
    details = Column(JSON, nullable=True, default=dict)
    duration_ms = Column(Float, nullable=True, default=0.0)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    execution = relationship("AgentExecution", back_populates="steps")


class ToolInvocation(Base):
    __tablename__ = "tool_invocations"

    id = Column(String(36), primary_key=True, default=new_uuid)
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_execution_id = Column(
        String(36), ForeignKey("agent_executions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mcp_server_id = Column(String(36), nullable=True, index=True)
    server_name = Column(String(150), nullable=False)
    tool_name = Column(String(150), nullable=False, index=True)
    risk_classification = Column(String(40), nullable=False, default="READ")
    arguments_json = Column(JSON, nullable=False, default=dict)
    output_json = Column(JSON, nullable=True)
    status = Column(
        String(40), nullable=False, default="completed", index=True
    )  # pending_approval, completed, failed, rejected
    error_message = Column(Text, nullable=True)
    duration_ms = Column(Float, nullable=True, default=0.0)
    invoked_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    execution = relationship("AgentExecution", back_populates="tool_invocations")


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id = Column(String(36), primary_key=True, default=new_uuid)
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_execution_id = Column(
        String(36), ForeignKey("agent_executions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conversation_id = Column(String(36), nullable=True, index=True)
    requested_by_user_id = Column(String(36), nullable=False, index=True)
    reviewed_by_user_id = Column(String(36), nullable=True)
    tool_name = Column(String(150), nullable=False)
    server_name = Column(String(150), nullable=False)
    risk_classification = Column(String(40), nullable=False, default="HIGH_RISK_WRITE")
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    proposed_arguments = Column(JSON, nullable=False, default=dict)
    batch_operations = Column(JSON, nullable=False, default=list)
    status = Column(
        String(40), nullable=False, default="pending", index=True
    )  # pending, approved, rejected
    reviewer_comment = Column(Text, nullable=True)
    execution_result = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    execution = relationship("AgentExecution", back_populates="approvals")


# ==============================================================================
# 5. WORKFLOW TEMPLATES, AUDIT LOGS & USAGE ANALYTICS MODELS
# ==============================================================================


class WorkflowTemplate(Base):
    __tablename__ = "workflow_templates"

    id = Column(String(36), primary_key=True, default=new_uuid)
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(80), nullable=False)  # Recruitment, HRMS, Finance, Executive BI
    prompt_template = Column(Text, nullable=False)
    steps_definition = Column(JSON, nullable=False, default=list)
    required_DOMAINS = Column(JSON, nullable=False, default=list)
    risk_level = Column(String(40), nullable=False, default="READ")
    is_active = Column(Boolean, default=True, nullable=False)
    run_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"

    id = Column(String(36), primary_key=True, default=new_uuid)
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workflow_template_id = Column(
        String(36), ForeignKey("workflow_templates.id", ondelete="SET NULL"), nullable=True, index=True
    )
    agent_execution_id = Column(
        String(36), ForeignKey("agent_executions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    triggered_by_user_id = Column(String(36), nullable=True)
    status = Column(String(40), nullable=False, default="completed")
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=new_uuid)
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_user_id = Column(String(36), nullable=True, index=True)
    actor_email = Column(String(255), nullable=True)
    actor_role = Column(String(64), nullable=True)
    action = Column(String(120), nullable=False, index=True)
    resource_type = Column(String(80), nullable=False, index=True)
    resource_id = Column(String(120), nullable=True)
    status = Column(String(40), nullable=False, default="success")
    ip_address = Column(String(64), nullable=True)
    metadata_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class UsageRecord(Base):
    __tablename__ = "usage_records"

    id = Column(String(36), primary_key=True, default=new_uuid)
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(String(36), nullable=True, index=True)
    agent_execution_id = Column(String(36), nullable=True, index=True)
    llm_model = Column(String(100), nullable=False, default="gpt-4o-mini")
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    tool_calls_count = Column(Integer, nullable=False, default=0)
    cost_usd = Column(Float, nullable=False, default=0.0)
    recorded_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


# ==============================================================================
# 6. ENTERPRISE BUSINESS DOMAIN MODELS (ACCESSED VIA REAL MCP SERVERS)
# ==============================================================================


class Department(Base):
    __tablename__ = "departments"

    id = Column(String(36), primary_key=True, default=new_uuid)
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = Column(String(120), nullable=False)
    code = Column(String(32), nullable=False)
    head_name = Column(String(150), nullable=True)
    annual_budget_inr = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class Employee(Base):
    __tablename__ = "employees"

    id = Column(String(36), primary_key=True, default=new_uuid)
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_code = Column(String(32), nullable=False, index=True)
    full_name = Column(String(150), nullable=False)
    email = Column(String(255), nullable=False)
    department_id = Column(
        String(36), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )
    department_name = Column(String(120), nullable=False)
    designation = Column(String(150), nullable=False)
    manager_id = Column(String(36), nullable=True)
    manager_name = Column(String(150), nullable=True)
    manager_email = Column(String(255), nullable=True)
    salary_lpa = Column(Float, nullable=False, default=12.0)
    status = Column(String(40), nullable=False, default="active")
    joined_date = Column(String(32), nullable=False)
    document_type = Column(String(80), nullable=True, default="Work Visa / Passport")
    document_expiry_date = Column(String(32), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class JobOpening(Base):
    __tablename__ = "job_openings"

    id = Column(String(36), primary_key=True, default=new_uuid)
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_code = Column(String(40), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    department_name = Column(String(120), nullable=False)
    location = Column(String(120), nullable=False, default="Bengaluru / Hybrid")
    employment_type = Column(String(50), nullable=False, default="Full-Time")
    salary_range = Column(String(80), nullable=False)
    status = Column(String(40), nullable=False, default="open")  # open, paused, closed
    hiring_manager = Column(String(150), nullable=False, default="Vikram Mehta")
    openings_count = Column(Integer, nullable=False, default=2)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(String(36), primary_key=True, default=new_uuid)
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    full_name = Column(String(150), nullable=False, index=True)
    email = Column(String(255), nullable=False)
    phone = Column(String(40), nullable=True)
    position_applied = Column(String(200), nullable=False)
    job_opening_id = Column(
        String(36), ForeignKey("job_openings.id", ondelete="SET NULL"), nullable=True
    )
    stage = Column(
        String(60), nullable=False, default="applied", index=True
    )  # applied, screening, technical_passed, interview_pending, shortlisted, offer_extended, hired, rejected
    interview_status = Column(
        String(60), nullable=False, default="waiting_for_interview"
    )  # waiting_for_interview, technical_passed, scheduled, completed
    days_waiting = Column(Integer, nullable=False, default=0)
    days_since_contact = Column(Integer, nullable=False, default=0)
    interview_date = Column(String(32), nullable=True)
    last_communication_date = Column(String(32), nullable=False)
    recruiter = Column(String(150), nullable=False, default="Ananya Sharma")
    experience_years = Column(Float, nullable=False, default=4.0)
    technical_score = Column(Float, nullable=True, default=85.0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class Application(Base):
    __tablename__ = "applications"

    id = Column(String(36), primary_key=True, default=new_uuid)
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_id = Column(
        String(36), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_opening_id = Column(
        String(36), ForeignKey("job_openings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status = Column(String(50), nullable=False, default="pending")  # pending, shortlisted, offered, rejected
    applied_date = Column(String(32), nullable=False)
    last_contacted_date = Column(String(32), nullable=False)
    days_since_contact = Column(Integer, nullable=False, default=0)
    assigned_recruiter = Column(String(150), nullable=False)
    source = Column(String(60), nullable=False, default="LinkedIn")
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id = Column(String(36), primary_key=True, default=new_uuid)
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_id = Column(
        String(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_name = Column(String(150), nullable=False)
    department_name = Column(String(120), nullable=False)
    manager_name = Column(String(150), nullable=False)
    manager_email = Column(String(255), nullable=False)
    date = Column(String(32), nullable=False)
    status = Column(String(40), nullable=False)  # present, missing, on_leave
    missing_days_streak = Column(Integer, nullable=False, default=0)
    check_in_time = Column(String(32), nullable=True)
    hours_logged = Column(Float, nullable=False, default=0.0)


class LeaveRecord(Base):
    __tablename__ = "leave_records"

    id = Column(String(36), primary_key=True, default=new_uuid)
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_id = Column(
        String(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_name = Column(String(150), nullable=False)
    leave_type = Column(String(60), nullable=False)  # Annual, Sick, Casual
    start_date = Column(String(32), nullable=False)
    end_date = Column(String(32), nullable=False)
    days_count = Column(Integer, nullable=False, default=1)
    status = Column(String(40), nullable=False, default="approved")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String(36), primary_key=True, default=new_uuid)
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    invoice_number = Column(String(50), nullable=False, index=True)
    client_name = Column(String(200), nullable=False)
    client_email = Column(String(255), nullable=False)
    amount_inr = Column(Float, nullable=False)
    status = Column(String(40), nullable=False, index=True)  # paid, unpaid, overdue
    issue_date = Column(String(32), nullable=False)
    due_date = Column(String(32), nullable=False)
    days_overdue = Column(Integer, nullable=False, default=0)
    last_reminder_sent_at = Column(String(64), nullable=True)


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(String(36), primary_key=True, default=new_uuid)
    organization_id = Column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category = Column(String(100), nullable=False, index=True)  # Cloud Infrastructure, Payroll, AI/LLM Compute, Recruitment & Marketing, SaaS Licenses
    month = Column(String(20), nullable=False, index=True)  # e.g., "2026-10", "2026-11"
    amount_inr = Column(Float, nullable=False)
    vendor = Column(String(150), nullable=False)
    description = Column(String(255), nullable=False)
    approved_by = Column(String(150), nullable=False)


Index("ix_agent_executions_org_status", AgentExecution.organization_id, AgentExecution.status)
Index("ix_tool_invocations_org_tool", ToolInvocation.organization_id, ToolInvocation.tool_name)
Index("ix_candidates_org_stage", Candidate.organization_id, Candidate.stage)

