"""
Employee & HRMS Domain MCP Server
Implements official MCP protocol tools for Employee Records, Attendance, Leave, and Document Compliance.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from mcp.server.mcpserver import MCPServer
from app.core.database import SessionLocal
from app.models.entities import AttendanceRecord, Employee, LeaveRecord

employee_mcp = MCPServer(
    "nexus-employee-mcp",
    instructions="Enterprise HRMS & Employee Operations MCP Server with strict tenant isolation.",
)

EMPLOYEE_TOOL_METADATA: Dict[str, Dict[str, Any]] = {
    "get_employees": {
        "display_name": "Get Employees",
        "risk_classification": "READ",
        "requires_approval": False,
        "required_roles": ["OWNER", "ADMIN", "OPERATOR", "VIEWER"],
    },
    "get_employee_details": {
        "display_name": "Get Employee Details",
        "risk_classification": "READ",
        "requires_approval": False,
        "required_roles": ["OWNER", "ADMIN", "OPERATOR", "VIEWER"],
    },
    "get_attendance": {
        "display_name": "Get Attendance Records",
        "risk_classification": "READ",
        "requires_approval": False,
        "required_roles": ["OWNER", "ADMIN", "OPERATOR", "VIEWER"],
    },
    "get_leave_records": {
        "display_name": "Get Leave Records",
        "risk_classification": "READ",
        "requires_approval": False,
        "required_roles": ["OWNER", "ADMIN", "OPERATOR", "VIEWER"],
    },
    "get_document_expiry": {
        "display_name": "Get Expiring Employee Documents",
        "risk_classification": "READ",
        "requires_approval": False,
        "required_roles": ["OWNER", "ADMIN", "OPERATOR", "VIEWER"],
    },
    "notify_managers": {
        "display_name": "Send Manager Compliance / Attendance Notifications",
        "risk_classification": "HIGH_RISK_WRITE",
        "requires_approval": True,
        "required_roles": ["OWNER", "ADMIN", "OPERATOR"],
    },
}


def _validate_tenant(organization_id: str) -> None:
    if not organization_id or not isinstance(organization_id, str):
        raise ValueError("Missing or invalid organization_id for tenant isolation.")


@employee_mcp.tool(
    name="get_employees",
    description="Retrieve employee directory records for the organization, optionally filtered by department.",
)
def get_employees(
    organization_id: str, department: Optional[str] = None
) -> Dict[str, Any]:
    _validate_tenant(organization_id)
    with SessionLocal() as db:
        q = db.query(Employee).filter(Employee.organization_id == organization_id)
        if department:
            q = q.filter(Employee.department_name.ilike(f"%{department}%"))
        rows = q.all()
        items = [
            {
                "id": e.id,
                "employee_code": e.employee_code,
                "full_name": e.full_name,
                "email": e.email,
                "department": e.department_name,
                "designation": e.designation,
                "manager_name": e.manager_name,
                "manager_email": e.manager_email,
                "status": e.status,
                "joined_date": e.joined_date,
            }
            for e in rows
        ]
        return {"status": "success", "count": len(items), "employees": items}


@employee_mcp.tool(
    name="get_employee_details",
    description="Look up detailed employee record by employee code or name.",
)
def get_employee_details(
    organization_id: str, query: str
) -> Dict[str, Any]:
    _validate_tenant(organization_id)
    with SessionLocal() as db:
        emp = (
            db.query(Employee)
            .filter(
                Employee.organization_id == organization_id,
                (Employee.employee_code.ilike(f"%{query}%"))
                | (Employee.full_name.ilike(f"%{query}%")),
            )
            .first()
        )
        if not emp:
            return {"status": "not_found", "query": query}
        return {
            "status": "success",
            "employee": {
                "id": emp.id,
                "employee_code": emp.employee_code,
                "full_name": emp.full_name,
                "email": emp.email,
                "department": emp.department_name,
                "designation": emp.designation,
                "manager_name": emp.manager_name,
                "manager_email": emp.manager_email,
                "salary_lpa": emp.salary_lpa,
                "document_type": emp.document_type,
                "document_expiry_date": emp.document_expiry_date,
            },
        }


@employee_mcp.tool(
    name="get_attendance",
    description="Retrieve employee attendance records and identify employees who missed attendance submission for N days.",
)
def get_attendance(
    organization_id: str,
    status: Optional[str] = None,
    min_missing_days: Optional[int] = None,
) -> Dict[str, Any]:
    _validate_tenant(organization_id)
    with SessionLocal() as db:
        q = db.query(AttendanceRecord).filter(
            AttendanceRecord.organization_id == organization_id
        )
        if status:
            q = q.filter(AttendanceRecord.status == status)
        if min_missing_days is not None:
            q = q.filter(AttendanceRecord.missing_days_streak >= min_missing_days)
        rows = q.order_by(AttendanceRecord.missing_days_streak.desc()).all()
        items = [
            {
                "id": r.id,
                "employee_id": r.employee_id,
                "employee_name": r.employee_name,
                "department": r.department_name,
                "manager_name": r.manager_name,
                "manager_email": r.manager_email,
                "date": r.date,
                "status": r.status,
                "missing_days_streak": r.missing_days_streak,
                "hours_logged": r.hours_logged,
            }
            for r in rows
        ]
        return {"status": "success", "count": len(items), "attendance_records": items}


@employee_mcp.tool(
    name="get_leave_records",
    description="Retrieve employee leave requests and balances for the organization.",
)
def get_leave_records(
    organization_id: str, status: Optional[str] = None
) -> Dict[str, Any]:
    _validate_tenant(organization_id)
    with SessionLocal() as db:
        q = db.query(LeaveRecord).filter(LeaveRecord.organization_id == organization_id)
        if status:
            q = q.filter(LeaveRecord.status == status)
        rows = q.all()
        items = [
            {
                "id": l.id,
                "employee_name": l.employee_name,
                "leave_type": l.leave_type,
                "start_date": l.start_date,
                "end_date": l.end_date,
                "days_count": l.days_count,
                "status": l.status,
            }
            for l in rows
        ]
        return {"status": "success", "count": len(items), "leave_records": items}


@employee_mcp.tool(
    name="get_document_expiry",
    description="Find employees whose compliance documents (visas, passports, certifications) are expiring next month or within N days.",
)
def get_document_expiry(
    organization_id: str, expiring_within_days: int = 45
) -> Dict[str, Any]:
    _validate_tenant(organization_id)
    cutoff = (datetime.now(timezone.utc) + timedelta(days=expiring_within_days)).strftime(
        "%Y-%m-%d"
    )
    with SessionLocal() as db:
        rows = (
            db.query(Employee)
            .filter(
                Employee.organization_id == organization_id,
                Employee.document_expiry_date.isnot(None),
                Employee.document_expiry_date <= cutoff,
            )
            .order_by(Employee.document_expiry_date.asc())
            .all()
        )
        items = [
            {
                "employee_id": e.id,
                "employee_code": e.employee_code,
                "employee_name": e.full_name,
                "department": e.department_name,
                "document_type": e.document_type,
                "expiry_date": e.document_expiry_date,
                "manager_name": e.manager_name,
                "manager_email": e.manager_email,
                "notification_draft": f"Action Required: {e.full_name}'s {e.document_type} expires on {e.document_expiry_date}.",
            }
            for e in rows
        ]
        return {"status": "success", "count": len(items), "expiring_documents": items}


@employee_mcp.tool(
    name="notify_managers",
    description="Send official compliance or attendance notifications to employee managers (High-Risk Write - requires human approval).",
)
def notify_managers(
    organization_id: str,
    reason: str,
    employee_names: List[str],
    manager_emails: List[str],
) -> Dict[str, Any]:
    _validate_tenant(organization_id)
    sent_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    dispatched = [
        {
            "employee_name": emp,
            "manager_email": mgr,
            "reason": reason,
            "delivery_status": "dispatched",
            "sent_at": sent_at,
        }
        for emp, mgr in zip(employee_names, manager_emails)
    ]
    return {
        "status": "success",
        "dispatched_count": len(dispatched),
        "notifications": dispatched,
    }


if __name__ == "__main__":
    employee_mcp.run(transport="stdio")

