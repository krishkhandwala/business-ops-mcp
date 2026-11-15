"""
Analytics & Business Intelligence Domain MCP Server
Implements official MCP protocol tools for Cross-Domain Metrics, Reports, and Period Comparisons.
"""
from typing import Any, Dict
from mcp.server.mcpserver import MCPServer
from app.core.database import SessionLocal
from app.models.entities import (
    Application,
    Candidate,
    Employee,
    Expense,
    Invoice,
    JobOpening,
)

analytics_mcp = MCPServer(
    "nexus-analytics-mcp",
    instructions="Enterprise Business Intelligence & Cross-Domain Analytics MCP Server.",
)

ANALYTICS_TOOL_METADATA: Dict[str, Dict[str, Any]] = {
    "get_business_metrics": {
        "display_name": "Get Cross-Domain Business Metrics",
        "risk_classification": "READ",
        "requires_approval": False,
        "required_roles": ["OWNER", "ADMIN", "OPERATOR", "VIEWER"],
    },
    "generate_report": {
        "display_name": "Generate Domain Performance Report",
        "risk_classification": "LOW_RISK_WRITE",
        "requires_approval": False,
        "required_roles": ["OWNER", "ADMIN", "OPERATOR", "VIEWER"],
    },
    "compare_periods": {
        "display_name": "Compare Financial / Operational Periods",
        "risk_classification": "READ",
        "requires_approval": False,
        "required_roles": ["OWNER", "ADMIN", "OPERATOR", "VIEWER"],
    },
}


def _validate_tenant(organization_id: str) -> None:
    if not organization_id or not isinstance(organization_id, str):
        raise ValueError("Missing or invalid organization_id for tenant isolation.")


@analytics_mcp.tool(
    name="get_business_metrics",
    description="Retrieve real-time KPIs across Recruitment, Employees, and Finance for the organization.",
)
def get_business_metrics(organization_id: str) -> Dict[str, Any]:
    _validate_tenant(organization_id)
    with SessionLocal() as db:
        emp_count = (
            db.query(Employee)
            .filter(Employee.organization_id == organization_id)
            .count()
        )
        open_jobs = (
            db.query(JobOpening)
            .filter(
                JobOpening.organization_id == organization_id,
                JobOpening.status == "open",
            )
            .count()
        )
        cand_count = (
            db.query(Candidate)
            .filter(Candidate.organization_id == organization_id)
            .count()
        )
        unpaid_invoices = (
            db.query(Invoice)
            .filter(
                Invoice.organization_id == organization_id,
                Invoice.status.in_(["unpaid", "overdue"]),
            )
            .all()
        )
        return {
            "status": "success",
            "metrics": {
                "active_employees": emp_count,
                "open_job_positions": open_jobs,
                "total_candidates_in_pipeline": cand_count,
                "unpaid_invoices_count": len(unpaid_invoices),
                "unpaid_receivables_inr": sum(i.amount_inr for i in unpaid_invoices),
            },
        }


@analytics_mcp.tool(
    name="generate_report",
    description="Generate a structured business report such as 'recruitment_performance' or 'operations_overview'.",
)
def generate_report(
    organization_id: str, report_type: str = "recruitment_performance"
) -> Dict[str, Any]:
    _validate_tenant(organization_id)
    with SessionLocal() as db:
        candidates = (
            db.query(Candidate)
            .filter(Candidate.organization_id == organization_id)
            .all()
        )
        jobs = (
            db.query(JobOpening)
            .filter(JobOpening.organization_id == organization_id)
            .all()
        )
        apps = (
            db.query(Application)
            .filter(Application.organization_id == organization_id)
            .all()
        )

        stage_breakdown: Dict[str, int] = {}
        recruiter_breakdown: Dict[str, int] = {}
        for c in candidates:
            stage_breakdown[c.stage] = stage_breakdown.get(c.stage, 0) + 1
            recruiter_breakdown[c.recruiter] = (
                recruiter_breakdown.get(c.recruiter, 0) + 1
            )

        avg_wait = (
            round(sum(c.days_waiting for c in candidates) / len(candidates), 1)
            if candidates
            else 0.0
        )
        avg_score = (
            round(
                sum((c.technical_score or 0.0) for c in candidates) / len(candidates), 1
            )
            if candidates
            else 0.0
        )

        rows = [
            {
                "stage": stage,
                "candidate_count": count,
                "share_pct": round((count / max(len(candidates), 1)) * 100, 1),
            }
            for stage, count in stage_breakdown.items()
        ]
        return {
            "status": "success",
            "report_type": report_type,
            "summary_kpis": {
                "total_candidates": len(candidates),
                "active_job_openings": len(jobs),
                "pending_applications": len([a for a in apps if a.status == "pending"]),
                "avg_days_waiting_in_pipeline": avg_wait,
                "avg_technical_assessment_score": avg_score,
            },
            "stage_distribution": rows,
            "recruiter_workload": [
                {"recruiter": r, "candidates_managed": cnt}
                for r, cnt in recruiter_breakdown.items()
            ],
        }


@analytics_mcp.tool(
    name="compare_periods",
    description="Compare organization expenses or operational metrics between two months (e.g., '2026-10' vs '2026-11') and explain major variances.",
)
def compare_periods(
    organization_id: str,
    period_previous: str = "2026-10",
    period_current: str = "2026-11",
) -> Dict[str, Any]:
    _validate_tenant(organization_id)
    with SessionLocal() as db:
        prev_rows = (
            db.query(Expense)
            .filter(
                Expense.organization_id == organization_id,
                Expense.month == period_previous,
            )
            .all()
        )
        curr_rows = (
            db.query(Expense)
            .filter(
                Expense.organization_id == organization_id,
                Expense.month == period_current,
            )
            .all()
        )

        prev_by_cat: Dict[str, float] = {}
        curr_by_cat: Dict[str, float] = {}
        for r in prev_rows:
            prev_by_cat[r.category] = prev_by_cat.get(r.category, 0.0) + r.amount_inr
        for r in curr_rows:
            curr_by_cat[r.category] = curr_by_cat.get(r.category, 0.0) + r.amount_inr

        all_cats = sorted(set(prev_by_cat.keys()) | set(curr_by_cat.keys()))
        comparison_table = []
        for cat in all_cats:
            p_val = prev_by_cat.get(cat, 0.0)
            c_val = curr_by_cat.get(cat, 0.0)
            diff = c_val - p_val
            pct = round((diff / p_val) * 100, 1) if p_val > 0 else 100.0
            comparison_table.append(
                {
                    "category": cat,
                    "previous_month_inr": p_val,
                    "current_month_inr": c_val,
                    "variance_inr": diff,
                    "variance_pct": pct,
                }
            )

        comparison_table.sort(key=lambda x: abs(x["variance_inr"]), reverse=True)
        total_prev = sum(prev_by_cat.values())
        total_curr = sum(curr_by_cat.values())
        total_diff = total_curr - total_prev
        total_pct = round((total_diff / total_prev) * 100, 1) if total_prev > 0 else 0.0

        return {
            "status": "success",
            "period_previous": period_previous,
            "period_current": period_current,
            "total_previous_inr": total_prev,
            "total_current_inr": total_curr,
            "net_variance_inr": total_diff,
            "net_variance_pct": total_pct,
            "category_comparison": comparison_table,
        }


if __name__ == "__main__":
    analytics_mcp.run(transport="stdio")

