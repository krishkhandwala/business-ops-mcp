import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_current_context, require_roles
from app.core.database import engine, get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    encrypt_secret,
    hash_password,
    redact_sensitive_data,
    verify_password,
)
from app.models.entities import (
    AgentExecution,
    ApprovalRequest,
    AuditLog,
    Candidate,
    Conversation,
    ExecutionStep,
    Integration,
    IntegrationCredential,
    MCPServerModel,
    MCPToolModel,
    Message,
    Organization,
    OrganizationMember,
    Permission,
    Role,
    ToolInvocation,
    UsageRecord,
    User,
    WorkflowExecution,
    WorkflowTemplate,
)
from app.services.mcp_client import mcp_client_manager
from app.services.workflow_engine import (
    NexusWorkflowEngine,
    process_approval_decision,
)

router = APIRouter()


# ==============================================================================
# REQUEST / RESPONSE SCHEMAS
# ==============================================================================


class LoginRequest(BaseModel):
    email: str = "arjun.mehta@nexus.io"
    password: str = "Nexus@2026!"


class RegisterRequest(BaseModel):
    email: str
    full_name: str
    password: str
    organization_name: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class SwitchRoleRequest(BaseModel):
    role: str = Field(..., description="OWNER, ADMIN, OPERATOR, or VIEWER")


class CommandExecuteRequest(BaseModel):
    prompt: str
    conversation_id: Optional[str] = None
    idempotency_key: Optional[str] = None


class CreateMCPServerRequest(BaseModel):
    name: str
    domain: str = "custom"
    description: str = ""
    transport_type: str = "streamable_http"
    endpoint: str
    auth_method: str = "bearer"
    credentials: Optional[Dict[str, Any]] = None


class UpdateToolRequest(BaseModel):
    is_enabled: Optional[bool] = None
    risk_classification: Optional[str] = None
    requires_approval: Optional[bool] = None


class TestToolRequest(BaseModel):
    arguments: Dict[str, Any] = Field(default_factory=dict)


class ConnectIntegrationRequest(BaseModel):
    public_config: Dict[str, Any] = Field(default_factory=dict)
    secret_credentials: Dict[str, Any] = Field(default_factory=dict)


class ApprovalDecisionRequest(BaseModel):
    decision: str = Field(..., description="'approve' or 'reject'")
    comment: Optional[str] = None


class InviteMemberRequest(BaseModel):
    email: str
    full_name: str
    role: str = "OPERATOR"


class UpdateMemberRoleRequest(BaseModel):
    role: str


class UpdateOrgSettingsRequest(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    approval_policy: Optional[Dict[str, Any]] = None
    settings_json: Optional[Dict[str, Any]] = None


class CreateWorkflowTemplateRequest(BaseModel):
    name: str
    description: str
    category: str = "Operations"
    prompt_template: str
    steps_definition: List[str] = Field(default_factory=list)
    risk_level: str = "READ"


# ==============================================================================
# 1. AUTHENTICATION & SESSION ENDPOINTS
# ==============================================================================


@router.post("/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    user = (
        db.query(User)
        .filter(User.email == payload.email.strip().lower())
        .first()
    )
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    membership = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.user_id == user.id,
            OrganizationMember.status == "active",
        )
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User has no active organization membership.",
        )

    org = (
        db.query(Organization)
        .filter(Organization.id == membership.organization_id)
        .first()
    )
    access_token = create_access_token(
        subject=user.id, organization_id=org.id, role=membership.role
    )
    refresh_token = create_refresh_token(
        subject=user.id, organization_id=org.id, role=membership.role
    )
    decoded_ref = decode_token(refresh_token)
    user.refresh_token_jti = decoded_ref.get("jti")
    user.last_login_at = datetime.now(timezone.utc)

    db.add(
        AuditLog(
            organization_id=org.id,
            actor_user_id=user.id,
            actor_email=user.email,
            actor_role=membership.role,
            action="user_login",
            resource_type="session",
            resource_id=user.id,
            status="success",
        )
    )
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": membership.role,
        },
        "organization": {
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
            "domain": org.domain,
            "plan_tier": org.plan_tier,
            "approval_policy": org.approval_policy,
        },
    }


@router.post("/auth/register", status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    existing = (
        db.query(User)
        .filter(User.email == payload.email.strip().lower())
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is already registered.",
        )

    slug_base = re.sub(r"[^a-z0-9]+", "-", payload.organization_name.lower()).strip("-")
    slug = f"{slug_base}-{ int(datetime.now(timezone.utc).timestamp()) % 10000 }"
    org = Organization(
        name=payload.organization_name,
        slug=slug,
        plan_tier="enterprise",
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    user = User(
        email=payload.email.strip().lower(),
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        last_login_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    member = OrganizationMember(
        organization_id=org.id,
        user_id=user.id,
        role="OWNER",
        status="active",
    )
    db.add(member)
    db.commit()

    access_token = create_access_token(
        subject=user.id, organization_id=org.id, role="OWNER"
    )
    refresh_token = create_refresh_token(
        subject=user.id, organization_id=org.id, role="OWNER"
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": "OWNER",
        },
        "organization": {
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
            "plan_tier": org.plan_tier,
        },
    }


@router.post("/auth/refresh")
def refresh_access_token(
    payload: RefreshTokenRequest, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    try:
        decoded = decode_token(payload.refresh_token)
        if decoded.get("type") != "refresh":
            raise ValueError("Not a refresh token")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {exc}",
        )

    user = db.query(User).filter(User.id == decoded.get("sub")).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive."
        )
    if user.refresh_token_jti and user.refresh_token_jti != decoded.get("jti"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has already been rotated.",
        )

    org_id = decoded.get("org_id")
    role = decoded.get("role", "OPERATOR")
    new_access = create_access_token(
        subject=user.id, organization_id=org_id, role=role
    )
    new_refresh = create_refresh_token(
        subject=user.id, organization_id=org_id, role=role
    )
    user.refresh_token_jti = decode_token(new_refresh).get("jti")
    db.commit()
    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer",
    }


@router.get("/auth/me")
def get_me(ctx: AuthContext = Depends(get_current_context)) -> Dict[str, Any]:
    return {
        "user": {
            "id": ctx.user.id,
            "email": ctx.user.email,
            "full_name": ctx.user.full_name,
            "role": ctx.role,
        },
        "organization": {
            "id": ctx.organization.id,
            "name": ctx.organization.name,
            "slug": ctx.organization.slug,
            "domain": ctx.organization.domain,
            "plan_tier": ctx.organization.plan_tier,
            "approval_policy": ctx.organization.approval_policy,
        },
    }


@router.post("/auth/switch-demo-user")
def switch_demo_user(
    payload: SwitchRoleRequest, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Convenience endpoint for switching between seeded RBAC personas (OWNER, ADMIN, OPERATOR, VIEWER)."""
    role_to_email = {
        "OWNER": "arjun.mehta@nexus.io",
        "ADMIN": "priya.nair@nexus.io",
        "OPERATOR": "ananya.sharma@nexus.io",
        "VIEWER": "rohit.verma@nexus.io",
    }
    target_role = payload.role.upper()
    email = role_to_email.get(target_role, "arjun.mehta@nexus.io")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Seeded user not found.")
    membership = (
        db.query(OrganizationMember)
        .filter(OrganizationMember.user_id == user.id)
        .first()
    )
    org = (
        db.query(Organization)
        .filter(Organization.id == membership.organization_id)
        .first()
    )
    access_token = create_access_token(
        subject=user.id, organization_id=org.id, role=membership.role
    )
    refresh_token = create_refresh_token(
        subject=user.id, organization_id=org.id, role=membership.role
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": membership.role,
        },
        "organization": {
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
            "domain": org.domain,
            "plan_tier": org.plan_tier,
            "approval_policy": org.approval_policy,
        },
    }


# ==============================================================================
# 2. MODULE A: AI COMMAND CENTER & CONVERSATIONS
# ==============================================================================


@router.post("/command/execute")
async def execute_ai_command(
    payload: CommandExecuteRequest,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    engine_instance = NexusWorkflowEngine(db)
    result = await engine_instance.execute_command(
        organization_id=ctx.organization.id,
        user_id=ctx.user.id,
        user_email=ctx.user.email,
        user_role=ctx.role,
        prompt=payload.prompt,
        conversation_id=payload.conversation_id,
        idempotency_key=payload.idempotency_key,
    )
    return result


@router.post("/command/stream")
async def stream_ai_command(
    payload: CommandExecuteRequest,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    engine_instance = NexusWorkflowEngine(db)
    result = await engine_instance.execute_command(
        organization_id=ctx.organization.id,
        user_id=ctx.user.id,
        user_email=ctx.user.email,
        user_role=ctx.role,
        prompt=payload.prompt,
        conversation_id=payload.conversation_id,
        idempotency_key=payload.idempotency_key,
    )

    async def event_generator():
        for step in result.get("steps", []):
            yield f"data: {json.dumps({'type': 'step', 'step': step})}\n\n"
        yield f"data: {json.dumps({'type': 'complete', 'result': result})}\n\n"

    return StreamingResponse(
        event_generator(), media_type="text/event-stream"
    )


@router.get("/conversations")
def list_conversations(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    convs = (
        db.query(Conversation)
        .filter(Conversation.organization_id == ctx.organization.id)
        .order_by(Conversation.updated_at.desc())
        .limit(50)
        .all()
    )
    return {
        "conversations": [
            {
                "id": c.id,
                "title": c.title,
                "status": c.status,
                "message_count": len(c.messages),
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat(),
            }
            for c in convs
        ]
    }


@router.get("/conversations/{conversation_id}")
def get_conversation_detail(
    conversation_id: str,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    conv = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.organization_id == ctx.organization.id,
        )
        .first()
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    msgs = (
        db.query(Message)
        .filter(
            Message.conversation_id == conv.id,
            Message.organization_id == ctx.organization.id,
        )
        .order_by(Message.created_at.asc())
        .all()
    )
    return {
        "id": conv.id,
        "title": conv.title,
        "status": conv.status,
        "created_at": conv.created_at.isoformat(),
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "structured_data": m.structured_data,
                "agent_execution_id": m.agent_execution_id,
                "created_at": m.created_at.isoformat(),
            }
            for m in msgs
        ],
    }


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: str,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    conv = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.organization_id == ctx.organization.id,
        )
        .first()
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    db.delete(conv)
    db.commit()
    return {"status": "deleted", "conversation_id": conversation_id}


# ==============================================================================
# 3. MODULE B: MCP SERVER MANAGEMENT
# ==============================================================================


@router.get("/mcp/servers")
def list_mcp_servers(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    servers = (
        db.query(MCPServerModel)
        .filter(MCPServerModel.organization_id == ctx.organization.id)
        .order_by(MCPServerModel.created_at.asc())
        .all()
    )
    items = []
    for s in servers:
        items.append(
            {
                "id": s.id,
                "name": s.name,
                "slug": s.slug,
                "domain": s.domain,
                "description": s.description,
                "transport_type": s.transport_type,
                "endpoint": s.endpoint,
                "auth_method": s.auth_method,
                "has_encrypted_credentials": bool(s.encrypted_credentials),
                "status": s.status,
                "health_status": s.health_status,
                "is_enabled": s.is_enabled,
                "last_connected_at": (
                    s.last_connected_at.isoformat() if s.last_connected_at else None
                ),
                "last_error": s.last_error,
                "tools_count": len(s.tools),
                "tools": [
                    {
                        "id": t.id,
                        "tool_name": t.tool_name,
                        "display_name": t.display_name,
                        "description": t.description,
                        "risk_classification": t.risk_classification,
                        "requires_approval": t.requires_approval,
                        "is_enabled": t.is_enabled,
                        "invocation_count": t.invocation_count,
                    }
                    for t in s.tools
                ],
            }
        )
    return {"servers": items}


@router.post("/mcp/servers", status_code=status.HTTP_201_CREATED)
async def create_mcp_server(
    payload: CreateMCPServerRequest,
    ctx: AuthContext = Depends(require_roles("OWNER", "ADMIN")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    slug = re.sub(r"[^a-z0-9]+", "-", payload.name.lower()).strip("-")
    enc_creds = (
        encrypt_secret(payload.credentials) if payload.credentials else None
    )
    srv = MCPServerModel(
        organization_id=ctx.organization.id,
        name=payload.name,
        slug=slug,
        domain=payload.domain,
        description=payload.description,
        transport_type=payload.transport_type,
        endpoint=payload.endpoint,
        auth_method=payload.auth_method,
        encrypted_credentials=enc_creds,
        status="connected",
        health_status="healthy",
        is_enabled=True,
    )
    db.add(srv)
    db.commit()
    db.refresh(srv)

    discovered = []
    try:
        discovered = await mcp_client_manager.discover_and_sync_tools(db, srv)
    except Exception as exc:
        srv.status = "error"
        srv.health_status = "unreachable"
        srv.last_error = str(exc)
        db.commit()

    db.add(
        AuditLog(
            organization_id=ctx.organization.id,
            actor_user_id=ctx.user.id,
            actor_email=ctx.user.email,
            actor_role=ctx.role,
            action="mcp_server_registered",
            resource_type="mcp_server",
            resource_id=srv.id,
            status=srv.status,
            metadata_json={
                "name": srv.name,
                "transport_type": srv.transport_type,
                "discovered_tools": len(discovered),
            },
        )
    )
    db.commit()

    return {
        "id": srv.id,
        "name": srv.name,
        "status": srv.status,
        "health_status": srv.health_status,
        "discovered_tools_count": len(discovered),
        "last_error": srv.last_error,
    }


@router.post("/mcp/servers/{server_id}/sync")
async def sync_mcp_server_tools(
    server_id: str,
    ctx: AuthContext = Depends(require_roles("OWNER", "ADMIN", "OPERATOR")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    srv = (
        db.query(MCPServerModel)
        .filter(
            MCPServerModel.id == server_id,
            MCPServerModel.organization_id == ctx.organization.id,
        )
        .first()
    )
    if not srv:
        raise HTTPException(status_code=404, detail="MCP Server not found.")

    tools = await mcp_client_manager.discover_and_sync_tools(db, srv)
    return {
        "server_id": srv.id,
        "status": srv.status,
        "health_status": srv.health_status,
        "discovered_tools_count": len(tools),
    }


@router.post("/mcp/servers/{server_id}/toggle")
def toggle_mcp_server(
    server_id: str,
    ctx: AuthContext = Depends(require_roles("OWNER", "ADMIN")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    srv = (
        db.query(MCPServerModel)
        .filter(
            MCPServerModel.id == server_id,
            MCPServerModel.organization_id == ctx.organization.id,
        )
        .first()
    )
    if not srv:
        raise HTTPException(status_code=404, detail="MCP Server not found.")

    if srv.status == "connected":
        srv.status = "disconnected"
        srv.health_status = "offline"
        srv.is_enabled = False
    else:
        srv.status = "connected"
        srv.health_status = "healthy"
        srv.is_enabled = True
        srv.last_connected_at = datetime.now(timezone.utc)

    db.commit()
    return {
        "id": srv.id,
        "name": srv.name,
        "status": srv.status,
        "health_status": srv.health_status,
        "is_enabled": srv.is_enabled,
    }


# ==============================================================================
# 4. MODULE C: CENTRALIZED TOOL REGISTRY
# ==============================================================================


@router.get("/mcp/tools")
def list_mcp_tools(
    domain: Optional[str] = Query(default=None),
    risk: Optional[str] = Query(default=None),
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    q = (
        db.query(MCPToolModel, MCPServerModel)
        .join(MCPServerModel, MCPToolModel.mcp_server_id == MCPServerModel.id)
        .filter(MCPToolModel.organization_id == ctx.organization.id)
    )
    if domain:
        q = q.filter(MCPServerModel.domain == domain)
    if risk:
        q = q.filter(MCPToolModel.risk_classification == risk)

    rows = q.order_by(MCPServerModel.name.asc(), MCPToolModel.tool_name.asc()).all()
    return {
        "tools": [
            {
                "id": tool.id,
                "tool_name": tool.tool_name,
                "display_name": tool.display_name,
                "description": tool.description,
                "input_schema": tool.input_schema,
                "output_schema": tool.output_schema,
                "mcp_server_id": srv.id,
                "mcp_server_name": srv.name,
                "domain": srv.domain,
                "risk_classification": tool.risk_classification,
                "required_roles": tool.required_roles,
                "requires_approval": tool.requires_approval,
                "is_enabled": tool.is_enabled,
                "invocation_count": tool.invocation_count,
                "last_invoked_at": (
                    tool.last_invoked_at.isoformat() if tool.last_invoked_at else None
                ),
            }
            for tool, srv in rows
        ]
    }


@router.patch("/mcp/tools/{tool_id}")
def update_mcp_tool(
    tool_id: str,
    payload: UpdateToolRequest,
    ctx: AuthContext = Depends(require_roles("OWNER", "ADMIN")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    tool = (
        db.query(MCPToolModel)
        .filter(
            MCPToolModel.id == tool_id,
            MCPToolModel.organization_id == ctx.organization.id,
        )
        .first()
    )
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found.")

    if payload.is_enabled is not None:
        tool.is_enabled = payload.is_enabled
    if payload.risk_classification is not None:
        tool.risk_classification = payload.risk_classification
    if payload.requires_approval is not None:
        tool.requires_approval = payload.requires_approval

    db.add(
        AuditLog(
            organization_id=ctx.organization.id,
            actor_user_id=ctx.user.id,
            actor_email=ctx.user.email,
            actor_role=ctx.role,
            action="mcp_tool_updated",
            resource_type="mcp_tool",
            resource_id=tool.id,
            status="success",
            metadata_json={
                "tool_name": tool.tool_name,
                "is_enabled": tool.is_enabled,
                "risk_classification": tool.risk_classification,
                "requires_approval": tool.requires_approval,
            },
        )
    )
    db.commit()
    return {
        "id": tool.id,
        "tool_name": tool.tool_name,
        "is_enabled": tool.is_enabled,
        "risk_classification": tool.risk_classification,
        "requires_approval": tool.requires_approval,
    }


@router.post("/mcp/tools/{tool_id}/test")
async def test_mcp_tool_execution(
    tool_id: str,
    payload: TestToolRequest,
    ctx: AuthContext = Depends(require_roles("OWNER", "ADMIN", "OPERATOR")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    tool = (
        db.query(MCPToolModel)
        .filter(
            MCPToolModel.id == tool_id,
            MCPToolModel.organization_id == ctx.organization.id,
        )
        .first()
    )
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found.")

    try:
        res = await mcp_client_manager.invoke_tool(
            db=db,
            organization_id=ctx.organization.id,
            user_role=ctx.role,
            tool_name=tool.tool_name,
            arguments=payload.arguments,
            bypass_approval_gate=False,
        )
        return {"status": "success", "result": res}
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# ==============================================================================
# 5. MODULE D: INTEGRATIONS MARKETPLACE
# ==============================================================================


@router.get("/integrations")
def list_integrations(
    category: Optional[str] = Query(default=None),
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    q = db.query(Integration).filter(
        Integration.organization_id == ctx.organization.id
    )
    if category and category != "All":
        q = q.filter(Integration.category == category)
    rows = q.order_by(Integration.status.asc(), Integration.name.asc()).all()
    return {
        "integrations": [
            {
                "id": i.id,
                "provider_key": i.provider_key,
                "name": i.name,
                "category": i.category,
                "description": i.description,
                "status": i.status,
                "public_config": i.public_config,
                "available_tools": i.available_tools,
                "permissions_scope": i.permissions_scope,
                "linked_mcp_server_id": i.linked_mcp_server_id,
                "last_tested_at": (
                    i.last_tested_at.isoformat() if i.last_tested_at else None
                ),
            }
            for i in rows
        ]
    }


@router.post("/integrations/{integration_id}/connect")
async def connect_integration(
    integration_id: str,
    payload: ConnectIntegrationRequest,
    ctx: AuthContext = Depends(require_roles("OWNER", "ADMIN")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    integ = (
        db.query(Integration)
        .filter(
            Integration.id == integration_id,
            Integration.organization_id == ctx.organization.id,
        )
        .first()
    )
    if not integ:
        raise HTTPException(status_code=404, detail="Integration not found.")

    # Perform real connectivity validation before marking connected
    if integ.provider_key == "postgresql":
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    elif integ.provider_key == "custom_rest":
        base_url = (payload.public_config or {}).get("base_url", "")
        if base_url and base_url.startswith("http"):
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.get(base_url)

    integ.public_config = redact_sensitive_data(payload.public_config or integ.public_config)
    integ.status = "connected"
    integ.connected_by_user_id = ctx.user.id
    integ.last_tested_at = datetime.now(timezone.utc)

    if payload.secret_credentials:
        db.add(
            IntegrationCredential(
                organization_id=ctx.organization.id,
                integration_id=integ.id,
                auth_type="encrypted_secret",
                encrypted_payload=encrypt_secret(payload.secret_credentials),
                key_hint="***encrypted***",
            )
        )

    db.add(
        AuditLog(
            organization_id=ctx.organization.id,
            actor_user_id=ctx.user.id,
            actor_email=ctx.user.email,
            actor_role=ctx.role,
            action="integration_connected",
            resource_type="integration",
            resource_id=integ.id,
            status="success",
            metadata_json={"provider_key": integ.provider_key, "name": integ.name},
        )
    )
    db.commit()
    return {
        "id": integ.id,
        "name": integ.name,
        "status": integ.status,
        "last_tested_at": integ.last_tested_at.isoformat(),
    }


@router.post("/integrations/{integration_id}/test")
def test_integration_connection(
    integration_id: str,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    integ = (
        db.query(Integration)
        .filter(
            Integration.id == integration_id,
            Integration.organization_id == ctx.organization.id,
        )
        .first()
    )
    if not integ:
        raise HTTPException(status_code=404, detail="Integration not found.")

    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    integ.last_tested_at = datetime.now(timezone.utc)
    db.commit()
    return {
        "id": integ.id,
        "provider_key": integ.provider_key,
        "status": integ.status,
        "connection_healthy": integ.status == "connected",
        "tested_at": integ.last_tested_at.isoformat(),
    }


@router.post("/integrations/{integration_id}/disconnect")
def disconnect_integration(
    integration_id: str,
    ctx: AuthContext = Depends(require_roles("OWNER", "ADMIN")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    integ = (
        db.query(Integration)
        .filter(
            Integration.id == integration_id,
            Integration.organization_id == ctx.organization.id,
        )
        .first()
    )
    if not integ:
        raise HTTPException(status_code=404, detail="Integration not found.")

    integ.status = "disconnected"
    db.query(IntegrationCredential).filter(
        IntegrationCredential.integration_id == integ.id
    ).delete()
    db.commit()
    return {"id": integ.id, "name": integ.name, "status": integ.status}


# ==============================================================================
# 6. MODULE E: WORKFLOW TEMPLATES
# ==============================================================================


@router.get("/workflows/templates")
def list_workflow_templates(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    rows = (
        db.query(WorkflowTemplate)
        .filter(WorkflowTemplate.organization_id == ctx.organization.id)
        .order_by(WorkflowTemplate.created_at.asc())
        .all()
    )
    return {
        "templates": [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "prompt_template": t.prompt_template,
                "steps_definition": t.steps_definition,
                "risk_level": t.risk_level,
                "run_count": t.run_count,
                "is_active": t.is_active,
            }
            for t in rows
        ]
    }


@router.post("/workflows/templates", status_code=status.HTTP_201_CREATED)
def create_workflow_template(
    payload: CreateWorkflowTemplateRequest,
    ctx: AuthContext = Depends(require_roles("OWNER", "ADMIN", "OPERATOR")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    tpl = WorkflowTemplate(
        organization_id=ctx.organization.id,
        name=payload.name,
        description=payload.description,
        category=payload.category,
        prompt_template=payload.prompt_template,
        steps_definition=payload.steps_definition,
        risk_level=payload.risk_level,
        is_active=True,
    )
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return {"id": tpl.id, "name": tpl.name, "category": tpl.category}


@router.post("/workflows/templates/{template_id}/run")
async def run_workflow_template(
    template_id: str,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    tpl = (
        db.query(WorkflowTemplate)
        .filter(
            WorkflowTemplate.id == template_id,
            WorkflowTemplate.organization_id == ctx.organization.id,
        )
        .first()
    )
    if not tpl:
        raise HTTPException(status_code=404, detail="Workflow template not found.")

    tpl.run_count = (tpl.run_count or 0) + 1
    engine_instance = NexusWorkflowEngine(db)
    res = await engine_instance.execute_command(
        organization_id=ctx.organization.id,
        user_id=ctx.user.id,
        user_email=ctx.user.email,
        user_role=ctx.role,
        prompt=tpl.prompt_template,
    )
    wf_exec = WorkflowExecution(
        organization_id=ctx.organization.id,
        workflow_template_id=tpl.id,
        agent_execution_id=res["execution_id"],
        triggered_by_user_id=ctx.user.id,
        status=res["status"],
        completed_at=datetime.now(timezone.utc),
    )
    db.add(wf_exec)
    db.commit()
    return res


# ==============================================================================
# 7. MODULE F: HUMAN APPROVAL ENGINE
# ==============================================================================


@router.get("/approvals")
def list_approvals(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    q = db.query(ApprovalRequest).filter(
        ApprovalRequest.organization_id == ctx.organization.id
    )
    if status_filter and status_filter != "all":
        q = q.filter(ApprovalRequest.status == status_filter)
    rows = q.order_by(ApprovalRequest.created_at.desc()).all()
    return {
        "approvals": [
            {
                "id": a.id,
                "agent_execution_id": a.agent_execution_id,
                "conversation_id": a.conversation_id,
                "tool_name": a.tool_name,
                "server_name": a.server_name,
                "risk_classification": a.risk_classification,
                "title": a.title,
                "description": a.description,
                "proposed_arguments": a.proposed_arguments,
                "status": a.status,
                "reviewer_comment": a.reviewer_comment,
                "execution_result": a.execution_result,
                "created_at": a.created_at.isoformat(),
                "reviewed_at": a.reviewed_at.isoformat() if a.reviewed_at else None,
            }
            for a in rows
        ]
    }


@router.post("/approvals/{approval_id}/decide")
async def decide_approval(
    approval_id: str,
    payload: ApprovalDecisionRequest,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    try:
        return await process_approval_decision(
            db=db,
            organization_id=ctx.organization.id,
            approval_id=approval_id,
            reviewer_user_id=ctx.user.id,
            reviewer_email=ctx.user.email,
            reviewer_role=ctx.role,
            decision=payload.decision,
            reviewer_comment=payload.comment,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# ==============================================================================
# 8. MODULE G: ANALYTICS & EXECUTION HISTORY
# ==============================================================================


@router.get("/executions")
def list_executions(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    tool_filter: Optional[str] = Query(default=None, alias="tool"),
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    q = db.query(AgentExecution).filter(
        AgentExecution.organization_id == ctx.organization.id
    )
    if status_filter and status_filter != "all":
        q = q.filter(AgentExecution.status == status_filter)
    rows = q.order_by(AgentExecution.started_at.desc()).limit(100).all()

    items = []
    for ex in rows:
        tool_names = [ti.tool_name for ti in ex.tool_invocations]
        if tool_filter and tool_filter not in tool_names:
            continue
        items.append(
            {
                "id": ex.id,
                "conversation_id": ex.conversation_id,
                "user_prompt": ex.user_prompt,
                "intent": ex.intent,
                "status": ex.status,
                "duration_ms": ex.duration_ms,
                "tools_invoked": tool_names,
                "steps_count": len(ex.steps),
                "approvals_count": len(ex.approvals),
                "prompt_tokens": ex.prompt_tokens,
                "completion_tokens": ex.completion_tokens,
                "estimated_cost_usd": ex.estimated_cost_usd,
                "started_at": ex.started_at.isoformat(),
                "completed_at": (
                    ex.completed_at.isoformat() if ex.completed_at else None
                ),
            }
        )
    return {"executions": items}


@router.get("/executions/{execution_id}")
def get_execution_trace(
    execution_id: str,
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    ex = (
        db.query(AgentExecution)
        .filter(
            AgentExecution.id == execution_id,
            AgentExecution.organization_id == ctx.organization.id,
        )
        .first()
    )
    if not ex:
        raise HTTPException(status_code=404, detail="Execution record not found.")

    return {
        "id": ex.id,
        "user_prompt": ex.user_prompt,
        "intent": ex.intent,
        "status": ex.status,
        "execution_plan": redact_sensitive_data(ex.execution_plan),
        "final_summary": ex.final_summary,
        "error_message": ex.error_message,
        "duration_ms": ex.duration_ms,
        "prompt_tokens": ex.prompt_tokens,
        "completion_tokens": ex.completion_tokens,
        "estimated_cost_usd": ex.estimated_cost_usd,
        "started_at": ex.started_at.isoformat(),
        "completed_at": ex.completed_at.isoformat() if ex.completed_at else None,
        "steps": [
            {
                "step_number": s.step_number,
                "node_name": s.node_name,
                "title": s.title,
                "status": s.status,
                "details": redact_sensitive_data(s.details),
                "duration_ms": s.duration_ms,
            }
            for s in sorted(ex.steps, key=lambda x: x.step_number)
        ],
        "tool_invocations": [
            {
                "id": ti.id,
                "server_name": ti.server_name,
                "tool_name": ti.tool_name,
                "risk_classification": ti.risk_classification,
                "arguments": redact_sensitive_data(ti.arguments_json),
                "output": redact_sensitive_data(ti.output_json),
                "status": ti.status,
                "error_message": ti.error_message,
                "duration_ms": ti.duration_ms,
                "invoked_at": ti.invoked_at.isoformat(),
            }
            for ti in ex.tool_invocations
        ],
        "approvals": [
            {
                "id": ap.id,
                "tool_name": ap.tool_name,
                "risk_classification": ap.risk_classification,
                "status": ap.status,
                "proposed_arguments": redact_sensitive_data(ap.proposed_arguments),
                "reviewer_comment": ap.reviewer_comment,
                "created_at": ap.created_at.isoformat(),
                "reviewed_at": ap.reviewed_at.isoformat() if ap.reviewed_at else None,
            }
            for ap in ex.approvals
        ],
    }


@router.get("/analytics/summary")
def get_analytics_summary(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    org_id = ctx.organization.id
    executions = (
        db.query(AgentExecution)
        .filter(AgentExecution.organization_id == org_id)
        .all()
    )
    total_tasks = len(executions)
    successful_tasks = sum(1 for e in executions if e.status == "completed")
    failed_tasks = sum(1 for e in executions if e.status in ("failed", "rejected"))
    awaiting_tasks = sum(1 for e in executions if e.status == "awaiting_approval")
    avg_duration_ms = (
        round(
            sum((e.duration_ms or 0.0) for e in executions) / max(total_tasks, 1), 2
        )
        if total_tasks
        else 0.0
    )

    tools = (
        db.query(MCPToolModel)
        .filter(MCPToolModel.organization_id == org_id)
        .order_by(MCPToolModel.invocation_count.desc())
        .all()
    )
    total_tool_invocations = sum(t.invocation_count or 0 for t in tools)
    top_tools = [
        {
            "tool_name": t.tool_name,
            "display_name": t.display_name,
            "invocations": t.invocation_count or 0,
            "risk": t.risk_classification,
        }
        for t in tools[:8]
    ]

    connected_integrations = (
        db.query(Integration)
        .filter(
            Integration.organization_id == org_id,
            Integration.status == "connected",
        )
        .count()
    )
    connected_mcp_servers = (
        db.query(MCPServerModel)
        .filter(
            MCPServerModel.organization_id == org_id,
            MCPServerModel.status == "connected",
        )
        .count()
    )
    pending_approvals = (
        db.query(ApprovalRequest)
        .filter(
            ApprovalRequest.organization_id == org_id,
            ApprovalRequest.status == "pending",
        )
        .count()
    )

    total_tokens = sum(
        (e.prompt_tokens or 0) + (e.completion_tokens or 0) for e in executions
    )
    total_cost_usd = round(
        sum((e.estimated_cost_usd or 0.0) for e in executions), 5
    )

    return {
        "total_ai_tasks_executed": total_tasks,
        "successful_executions": successful_tasks,
        "failed_executions": failed_tasks,
        "awaiting_approval_executions": awaiting_tasks,
        "average_execution_duration_ms": avg_duration_ms,
        "mcp_tool_invocation_count": total_tool_invocations,
        "connected_integrations": connected_integrations,
        "connected_mcp_servers": connected_mcp_servers,
        "pending_approvals": pending_approvals,
        "token_consumption": total_tokens,
        "estimated_ai_usage_cost_usd": total_cost_usd,
        "most_frequently_used_tools": top_tools,
    }


# ==============================================================================
# 9. MODULE H: ORGANIZATION, TEAM MEMBERS, PERMISSIONS & AUDIT LOGS
# ==============================================================================


@router.get("/organization")
def get_organization_details(
    ctx: AuthContext = Depends(get_current_context),
) -> Dict[str, Any]:
    org = ctx.organization
    return {
        "id": org.id,
        "name": org.name,
        "slug": org.slug,
        "domain": org.domain,
        "plan_tier": org.plan_tier,
        "approval_policy": org.approval_policy,
        "settings_json": org.settings_json,
        "created_at": org.created_at.isoformat(),
    }


@router.patch("/organization/settings")
def update_organization_settings(
    payload: UpdateOrgSettingsRequest,
    ctx: AuthContext = Depends(require_roles("OWNER", "ADMIN")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    org = ctx.organization
    if payload.name is not None:
        org.name = payload.name
    if payload.domain is not None:
        org.domain = payload.domain
    if payload.approval_policy is not None:
        org.approval_policy = payload.approval_policy
    if payload.settings_json is not None:
        org.settings_json = payload.settings_json

    db.add(
        AuditLog(
            organization_id=org.id,
            actor_user_id=ctx.user.id,
            actor_email=ctx.user.email,
            actor_role=ctx.role,
            action="organization_settings_updated",
            resource_type="organization",
            resource_id=org.id,
            status="success",
        )
    )
    db.commit()
    return {
        "id": org.id,
        "name": org.name,
        "domain": org.domain,
        "approval_policy": org.approval_policy,
        "settings_json": org.settings_json,
    }


@router.get("/organization/members")
def list_organization_members(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    rows = (
        db.query(OrganizationMember, User)
        .join(User, OrganizationMember.user_id == User.id)
        .filter(OrganizationMember.organization_id == ctx.organization.id)
        .order_by(OrganizationMember.joined_at.asc())
        .all()
    )
    return {
        "members": [
            {
                "member_id": m.id,
                "user_id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "role": m.role,
                "status": m.status,
                "joined_at": m.joined_at.isoformat(),
                "last_login_at": (
                    u.last_login_at.isoformat() if u.last_login_at else None
                ),
            }
            for m, u in rows
        ]
    }


@router.post("/organization/members/invite", status_code=status.HTTP_201_CREATED)
def invite_organization_member(
    payload: InviteMemberRequest,
    ctx: AuthContext = Depends(require_roles("OWNER", "ADMIN")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    email_clean = payload.email.strip().lower()
    user = db.query(User).filter(User.email == email_clean).first()
    if not user:
        user = User(
            email=email_clean,
            full_name=payload.full_name,
            hashed_password=hash_password("NexusInvite@2026!"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    existing_mem = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == ctx.organization.id,
            OrganizationMember.user_id == user.id,
        )
        .first()
    )
    if existing_mem:
        raise HTTPException(
            status_code=400, detail="User is already a member of this organization."
        )

    mem = OrganizationMember(
        organization_id=ctx.organization.id,
        user_id=user.id,
        role=payload.role.upper(),
        status="active",
        invited_by_email=ctx.user.email,
    )
    db.add(mem)
    db.add(
        AuditLog(
            organization_id=ctx.organization.id,
            actor_user_id=ctx.user.id,
            actor_email=ctx.user.email,
            actor_role=ctx.role,
            action="team_member_invited",
            resource_type="organization_member",
            resource_id=user.id,
            status="success",
            metadata_json={"invited_email": email_clean, "role": payload.role.upper()},
        )
    )
    db.commit()
    db.refresh(mem)
    return {
        "member_id": mem.id,
        "user_id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": mem.role,
        "status": mem.status,
    }


@router.patch("/organization/members/{member_id}")
def update_member_role(
    member_id: str,
    payload: UpdateMemberRoleRequest,
    ctx: AuthContext = Depends(require_roles("OWNER", "ADMIN")),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    mem = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.id == member_id,
            OrganizationMember.organization_id == ctx.organization.id,
        )
        .first()
    )
    if not mem:
        raise HTTPException(status_code=404, detail="Member not found.")
    mem.role = payload.role.upper()
    db.commit()
    return {"member_id": mem.id, "role": mem.role}


@router.get("/organization/permissions")
def list_permissions(
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    roles = (
        db.query(Role)
        .filter(Role.organization_id == ctx.organization.id)
        .all()
    )
    perms = (
        db.query(Permission)
        .filter(Permission.organization_id == ctx.organization.id)
        .all()
    )
    return {
        "roles": [
            {"id": r.id, "name": r.name, "description": r.description}
            for r in roles
        ],
        "permissions": [
            {
                "id": p.id,
                "role_name": p.role_name,
                "resource": p.resource,
                "action": p.action,
                "allowed": p.allowed,
            }
            for p in perms
        ],
    }


@router.get("/organization/audit-logs")
def list_audit_logs(
    action_filter: Optional[str] = Query(default=None, alias="action"),
    ctx: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    q = db.query(AuditLog).filter(
        AuditLog.organization_id == ctx.organization.id
    )
    if action_filter:
        q = q.filter(AuditLog.action == action_filter)
    rows = q.order_by(AuditLog.created_at.desc()).limit(100).all()
    return {
        "audit_logs": [
            {
                "id": a.id,
                "actor_email": a.actor_email,
                "actor_role": a.actor_role,
                "action": a.action,
                "resource_type": a.resource_type,
                "resource_id": a.resource_id,
                "status": a.status,
                "ip_address": a.ip_address,
                "metadata": redact_sensitive_data(a.metadata_json),
                "created_at": a.created_at.isoformat(),
            }
            for a in rows
        ]
    }

