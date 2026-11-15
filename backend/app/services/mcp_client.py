"""
Official MCP Client Protocol Manager
Connects to domain MCP servers using the official Python `mcp` SDK (`mcp.Client` & `StdioServerParameters`),
dynamically discovers tool schemas, syncs them to the Tool Registry, and executes tool invocations
with strict tenant isolation, RBAC enforcement, and untrusted output sanitization.
"""
import json
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import mcp
from mcp import StdioServerParameters
from mcp.server.mcpserver import MCPServer
from sqlalchemy.orm import Session

from app.core.security import sanitize_untrusted_tool_output
from app.mcp_servers.analytics_server import ANALYTICS_TOOL_METADATA, analytics_mcp
from app.mcp_servers.employee_server import EMPLOYEE_TOOL_METADATA, employee_mcp
from app.mcp_servers.finance_server import FINANCE_TOOL_METADATA, finance_mcp
from app.mcp_servers.recruitment_server import (
    RECRUITMENT_TOOL_METADATA,
    recruitment_mcp,
)
from app.models.entities import MCPConnection, MCPServerModel, MCPToolModel

BUILTIN_MCP_SERVERS: Dict[str, MCPServer] = {
    "recruitment": recruitment_mcp,
    "employee": employee_mcp,
    "finance": finance_mcp,
    "analytics": analytics_mcp,
}

BUILTIN_TOOL_METADATA: Dict[str, Dict[str, Any]] = {
    **RECRUITMENT_TOOL_METADATA,
    **EMPLOYEE_TOOL_METADATA,
    **FINANCE_TOOL_METADATA,
    **ANALYTICS_TOOL_METADATA,
}


def classify_tool_risk(tool_name: str, description: str = "") -> Dict[str, Any]:
    if tool_name in BUILTIN_TOOL_METADATA:
        return BUILTIN_TOOL_METADATA[tool_name]
    lower_name = tool_name.lower()
    if any(
        k in lower_name
        for k in ("create", "update", "delete", "send", "notify", "remove", "transfer")
    ):
        return {
            "display_name": tool_name.replace("_", " ").title(),
            "risk_classification": "HIGH_RISK_WRITE",
            "requires_approval": True,
            "required_roles": ["OWNER", "ADMIN", "OPERATOR"],
        }
    if any(k in lower_name for k in ("generate", "prepare", "draft", "export")):
        return {
            "display_name": tool_name.replace("_", " ").title(),
            "risk_classification": "LOW_RISK_WRITE",
            "requires_approval": False,
            "required_roles": ["OWNER", "ADMIN", "OPERATOR", "VIEWER"],
        }
    return {
        "display_name": tool_name.replace("_", " ").title(),
        "risk_classification": "READ",
        "requires_approval": False,
        "required_roles": ["OWNER", "ADMIN", "OPERATOR", "VIEWER"],
    }


class MCPClientManager:
    """Manages official MCP protocol client sessions across stdio, Streamable HTTP, and built-in MCPServers."""

    def _resolve_client_target(self, server_model: MCPServerModel) -> Any:
        domain_key = (server_model.domain or "").lower()
        if domain_key in BUILTIN_MCP_SERVERS and server_model.transport_type in (
            "stdio",
            "in_process",
        ):
            return BUILTIN_MCP_SERVERS[domain_key]

        if server_model.transport_type == "stdio" and server_model.endpoint.endswith(
            ".py"
        ):
            backend_root = str(Path(__file__).resolve().parents[2])
            return StdioServerParameters(
                command=sys.executable,
                args=[server_model.endpoint],
                cwd=backend_root,
            )

        if server_model.transport_type in ("streamable_http", "sse", "http"):
            return server_model.endpoint

        if domain_key in BUILTIN_MCP_SERVERS:
            return BUILTIN_MCP_SERVERS[domain_key]

        raise ValueError(
            f"Unsupported MCP server configuration for '{server_model.name}' ({server_model.transport_type} -> {server_model.endpoint})"
        )

    async def discover_and_sync_tools(
        self, db: Session, server_model: MCPServerModel
    ) -> List[MCPToolModel]:
        """Connect to MCP server via official `mcp.Client`, run `list_tools()`, and sync schemas to PostgreSQL/DB."""
        start_ts = time.perf_counter()
        target = self._resolve_client_target(server_model)
        discovered_models: List[MCPToolModel] = []

        try:
            async with mcp.Client(target) as client:
                tools_result = await client.list_tools()
                latency_ms = round((time.perf_counter() - start_ts) * 1000, 2)

                server_model.status = "connected"
                server_model.health_status = "healthy"
                server_model.last_connected_at = datetime.now(timezone.utc)
                server_model.last_error = None

                conn_record = MCPConnection(
                    organization_id=server_model.organization_id,
                    mcp_server_id=server_model.id,
                    session_id=f"mcp-sess-{uuid.uuid4().hex[:12]}",
                    transport_type=server_model.transport_type,
                    status="active",
                    latency_ms=latency_ms,
                    protocol_version="2025-11-25",
                )
                db.add(conn_record)

                for mcp_tool in tools_result.tools:
                    meta = classify_tool_risk(
                        mcp_tool.name, mcp_tool.description or ""
                    )
                    input_schema = getattr(mcp_tool, "input_schema", None) or getattr(
                        mcp_tool, "inputSchema", {}
                    )
                    output_schema = getattr(
                        mcp_tool, "output_schema", None
                    ) or getattr(mcp_tool, "outputSchema", {"type": "object"})

                    existing = (
                        db.query(MCPToolModel)
                        .filter(
                            MCPToolModel.organization_id
                            == server_model.organization_id,
                            MCPToolModel.mcp_server_id == server_model.id,
                            MCPToolModel.tool_name == mcp_tool.name,
                        )
                        .first()
                    )
                    if existing:
                        existing.description = (
                            mcp_tool.description or existing.description
                        )
                        existing.input_schema = input_schema or {}
                        existing.output_schema = output_schema or {"type": "object"}
                        discovered_models.append(existing)
                    else:
                        new_tool = MCPToolModel(
                            organization_id=server_model.organization_id,
                            mcp_server_id=server_model.id,
                            tool_name=mcp_tool.name,
                            display_name=meta["display_name"],
                            description=mcp_tool.description
                            or f"Execute {mcp_tool.name} via MCP.",
                            input_schema=input_schema or {},
                            output_schema=output_schema or {"type": "object"},
                            risk_classification=meta["risk_classification"],
                            required_roles=meta["required_roles"],
                            requires_approval=meta["requires_approval"],
                            is_enabled=True,
                        )
                        db.add(new_tool)
                        discovered_models.append(new_tool)

                db.commit()
                for m in discovered_models:
                    db.refresh(m)
                return discovered_models

        except Exception as exc:
            server_model.status = "error"
            server_model.health_status = "unreachable"
            server_model.last_error = str(exc)
            db.commit()
            raise

    async def invoke_tool(
        self,
        db: Session,
        organization_id: str,
        user_role: str,
        tool_name: str,
        arguments: Dict[str, Any],
        bypass_approval_gate: bool = False,
    ) -> Dict[str, Any]:
        """
        Invoke an MCP tool over the official MCP client protocol after verifying:
        1. Organization ownership & server availability
        2. Tool enabled status
        3. User role authorization (RBAC)
        4. Enforced tenant boundary (`organization_id` overridden by authenticated context)
        """
        tool_model = (
            db.query(MCPToolModel)
            .join(MCPServerModel, MCPToolModel.mcp_server_id == MCPServerModel.id)
            .filter(
                MCPToolModel.organization_id == organization_id,
                MCPToolModel.tool_name == tool_name,
            )
            .first()
        )
        if not tool_model:
            raise PermissionError(
                f"Tool '{tool_name}' is not registered for organization '{organization_id}'."
            )
        if not tool_model.is_enabled:
            raise PermissionError(
                f"Tool '{tool_name}' is currently disabled in the Tool Registry."
            )

        server_model = tool_model.server
        if not server_model or not server_model.is_enabled or server_model.status == "disconnected":
            raise RuntimeError(
                f"MCP Server '{server_model.name if server_model else 'Unknown'}' is disconnected or disabled."
            )

        allowed_roles = tool_model.required_roles or [
            "OWNER",
            "ADMIN",
            "OPERATOR",
            "VIEWER",
        ]
        if user_role not in allowed_roles:
            raise PermissionError(
                f"Role '{user_role}' does not have permission to invoke '{tool_name}'. Allowed roles: {allowed_roles}"
            )

        if tool_model.requires_approval and not bypass_approval_gate:
            raise PermissionError(
                f"Tool '{tool_name}' is classified as {tool_model.risk_classification} and requires explicit Human Approval before execution."
            )

        # Enforce tenant boundary: always inject authenticated organization_id
        safe_args = dict(arguments or {})
        safe_args["organization_id"] = organization_id

        start_ts = time.perf_counter()
        target = self._resolve_client_target(server_model)

        async with mcp.Client(target) as client:
            call_result = await client.call_tool(tool_name, safe_args)
            duration_ms = round((time.perf_counter() - start_ts) * 1000, 2)

            if getattr(call_result, "isError", False) or getattr(
                call_result, "is_error", False
            ):
                err_text = (
                    call_result.content[0].text
                    if call_result.content
                    else "MCP Tool Execution Error"
                )
                raise RuntimeError(f"MCP tool '{tool_name}' failed: {err_text}")

            raw_text = (
                call_result.content[0].text
                if call_result.content and hasattr(call_result.content[0], "text")
                else "{}"
            )
            try:
                parsed_output = json.loads(raw_text)
            except json.JSONDecodeError:
                parsed_output = {"raw_output": raw_text}

            sanitized_output = sanitize_untrusted_tool_output(parsed_output)

            tool_model.invocation_count = (tool_model.invocation_count or 0) + 1
            tool_model.last_invoked_at = datetime.now(timezone.utc)
            server_model.last_connected_at = datetime.now(timezone.utc)
            db.commit()

            return {
                "tool_name": tool_name,
                "server_id": server_model.id,
                "server_name": server_model.name,
                "risk_classification": tool_model.risk_classification,
                "duration_ms": duration_ms,
                "arguments": {
                    k: v for k, v in safe_args.items() if k != "organization_id"
                },
                "output": sanitized_output,
            }


mcp_client_manager = MCPClientManager()

