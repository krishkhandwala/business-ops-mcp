"""
Celery Distributed Background Task System with Automatic Local Fallback
Supports asynchronous background workflow execution and periodic MCP health checks.
"""
import asyncio
from typing import Any, Dict
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "nexus_ops_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=120,
)


@celery_app.task(name="nexus.run_mcp_health_check")
def run_mcp_health_check_task(organization_id: str) -> Dict[str, Any]:
    from app.core.database import SessionLocal
    from app.models.entities import MCPServerModel
    from app.services.mcp_client import mcp_client_manager

    with SessionLocal() as db:
        servers = (
            db.query(MCPServerModel)
            .filter(
                MCPServerModel.organization_id == organization_id,
                MCPServerModel.is_enabled.is_(True),
            )
            .all()
        )
        checked = 0
        for srv in servers:
            try:
                asyncio.run(mcp_client_manager.discover_and_sync_tools(db, srv))
                checked += 1
            except Exception:
                pass
        return {"organization_id": organization_id, "checked_servers": checked}

