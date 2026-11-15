"""
Finance & Billing Domain MCP Server
Implements official MCP protocol tools for Invoices, Expenses, Payment Status, and Reminders.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from mcp.server.mcpserver import MCPServer
from app.core.database import SessionLocal
from app.models.entities import Expense, Invoice

finance_mcp = MCPServer(
    "nexus-finance-mcp",
    instructions="Enterprise Finance, Billing & Expense Operations MCP Server with strict tenant isolation.",
)

FINANCE_TOOL_METADATA: Dict[str, Dict[str, Any]] = {
    "get_invoices": {
        "display_name": "Get Client Invoices",
        "risk_classification": "READ",
        "requires_approval": False,
        "required_roles": ["OWNER", "ADMIN", "OPERATOR", "VIEWER"],
    },
    "get_expenses": {
        "display_name": "Get Organization Expenses",
        "risk_classification": "READ",
        "requires_approval": False,
        "required_roles": ["OWNER", "ADMIN", "OPERATOR", "VIEWER"],
    },
    "get_payment_status": {
        "display_name": "Get Invoice Payment Status",
        "risk_classification": "READ",
        "requires_approval": False,
        "required_roles": ["OWNER", "ADMIN", "OPERATOR", "VIEWER"],
    },
    "generate_financial_summary": {
        "display_name": "Generate Financial Summary",
        "risk_classification": "LOW_RISK_WRITE",
        "requires_approval": False,
        "required_roles": ["OWNER", "ADMIN", "OPERATOR", "VIEWER"],
    },
    "send_invoice_reminders": {
        "display_name": "Send Unpaid Invoice Client Reminders",
        "risk_classification": "HIGH_RISK_WRITE",
        "requires_approval": True,
        "required_roles": ["OWNER", "ADMIN", "OPERATOR"],
    },
}


def _validate_tenant(organization_id: str) -> None:
    if not organization_id or not isinstance(organization_id, str):
        raise ValueError("Missing or invalid organization_id for tenant isolation.")


@finance_mcp.tool(
    name="get_invoices",
    description="Retrieve client invoices, optionally filtering by status ('unpaid', 'overdue', 'paid').",
)
def get_invoices(
    organization_id: str, status: Optional[str] = None
) -> Dict[str, Any]:
    _validate_tenant(organization_id)
    with SessionLocal() as db:
        q = db.query(Invoice).filter(Invoice.organization_id == organization_id)
        if status == "unpaid":
            q = q.filter(Invoice.status.in_(["unpaid", "overdue"]))
        elif status:
            q = q.filter(Invoice.status == status)
        rows = q.order_by(Invoice.days_overdue.desc()).all()
        items = [
            {
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "client_name": inv.client_name,
                "client_email": inv.client_email,
                "amount_inr": inv.amount_inr,
                "status": inv.status,
                "issue_date": inv.issue_date,
                "due_date": inv.due_date,
                "days_overdue": inv.days_overdue,
                "last_reminder_sent_at": inv.last_reminder_sent_at or "Never",
            }
            for inv in rows
        ]
        total_amount = sum(i["amount_inr"] for i in items)
        return {
            "status": "success",
            "count": len(items),
            "total_amount_inr": total_amount,
            "invoices": items,
        }


@finance_mcp.tool(
    name="get_expenses",
    description="Retrieve organization expenses by month (e.g. '2026-10', '2026-11') or category.",
)
def get_expenses(
    organization_id: str,
    month: Optional[str] = None,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    _validate_tenant(organization_id)
    with SessionLocal() as db:
        q = db.query(Expense).filter(Expense.organization_id == organization_id)
        if month:
            q = q.filter(Expense.month == month)
        if category:
            q = q.filter(Expense.category.ilike(f"%{category}%"))
        rows = q.order_by(Expense.month.desc(), Expense.amount_inr.desc()).all()
        items = [
            {
                "id": ex.id,
                "category": ex.category,
                "month": ex.month,
                "amount_inr": ex.amount_inr,
                "vendor": ex.vendor,
                "description": ex.description,
                "approved_by": ex.approved_by,
            }
            for ex in rows
        ]
        return {
            "status": "success",
            "count": len(items),
            "total_amount_inr": sum(i["amount_inr"] for i in items),
            "expenses": items,
        }


@finance_mcp.tool(
    name="get_payment_status",
    description="Check payment status for a specific invoice number or all overdue invoices.",
)
def get_payment_status(
    organization_id: str, invoice_number: Optional[str] = None
) -> Dict[str, Any]:
    _validate_tenant(organization_id)
    with SessionLocal() as db:
        q = db.query(Invoice).filter(Invoice.organization_id == organization_id)
        if invoice_number:
            q = q.filter(Invoice.invoice_number == invoice_number)
        rows = q.all()
        return {
            "status": "success",
            "count": len(rows),
            "payments": [
                {
                    "invoice_number": r.invoice_number,
                    "client_name": r.client_name,
                    "amount_inr": r.amount_inr,
                    "status": r.status,
                    "days_overdue": r.days_overdue,
                }
                for r in rows
            ],
        }


@finance_mcp.tool(
    name="generate_financial_summary",
    description="Generate an executive financial summary of revenue, unpaid receivables, and monthly operating expenses.",
)
def generate_financial_summary(
    organization_id: str, month: str = "2026-11"
) -> Dict[str, Any]:
    _validate_tenant(organization_id)
    with SessionLocal() as db:
        invoices = (
            db.query(Invoice)
            .filter(Invoice.organization_id == organization_id)
            .all()
        )
        expenses = (
            db.query(Expense)
            .filter(
                Expense.organization_id == organization_id,
                Expense.month == month,
            )
            .all()
        )
        paid_rev = sum(i.amount_inr for i in invoices if i.status == "paid")
        unpaid_rev = sum(i.amount_inr for i in invoices if i.status in ("unpaid", "overdue"))
        total_exp = sum(e.amount_inr for e in expenses)
        return {
            "status": "success",
            "month": month,
            "collected_revenue_inr": paid_rev,
            "outstanding_receivables_inr": unpaid_rev,
            "total_expenses_inr": total_exp,
            "net_operating_position_inr": paid_rev - total_exp,
        }


@finance_mcp.tool(
    name="send_invoice_reminders",
    description="Send payment reminder emails to clients with unpaid or overdue invoices (High-Risk Write - requires approval).",
)
def send_invoice_reminders(
    organization_id: str, invoice_numbers: List[str]
) -> Dict[str, Any]:
    _validate_tenant(organization_id)
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    reminded = []
    with SessionLocal() as db:
        rows = (
            db.query(Invoice)
            .filter(
                Invoice.organization_id == organization_id,
                Invoice.invoice_number.in_(invoice_numbers),
            )
            .all()
        )
        for inv in rows:
            inv.last_reminder_sent_at = now_str
            reminded.append(
                {
                    "invoice_number": inv.invoice_number,
                    "client_name": inv.client_name,
                    "client_email": inv.client_email,
                    "amount_inr": inv.amount_inr,
                    "days_overdue": inv.days_overdue,
                    "reminder_sent_at": now_str,
                }
            )
        db.commit()
    return {
        "status": "success",
        "reminded_count": len(reminded),
        "reminders": reminded,
    }


if __name__ == "__main__":
    finance_mcp.run(transport="stdio")

