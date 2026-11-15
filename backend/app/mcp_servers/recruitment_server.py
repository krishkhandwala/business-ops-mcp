"""
Recruitment Domain MCP Server
Implements official MCP protocol tools for Recruitment & Talent Operations.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from mcp.server.mcpserver import MCPServer
from app.core.database import SessionLocal
from app.models.entities import Application, Candidate, JobOpening

recruitment_mcp = MCPServer(
    "nexus-recruitment-mcp",
    instructions="Enterprise Recruitment & Talent Acquisition MCP Server with strict tenant isolation.",
)

RECRUITMENT_TOOL_METADATA: Dict[str, Dict[str, Any]] = {
    "get_candidates": {
        "display_name": "Get Candidates",
        "risk_classification": "READ",
        "requires_approval": False,
        "required_roles": ["OWNER", "ADMIN", "OPERATOR", "VIEWER"],
    },
    "search_candidates": {
        "display_name": "Search Candidates",
        "risk_classification": "READ",
        "requires_approval": False,
        "required_roles": ["OWNER", "ADMIN", "OPERATOR", "VIEWER"],
    },
    "get_pending_applications": {
        "display_name": "Get Pending Applications",
        "risk_classification": "READ",
        "requires_approval": False,
        "required_roles": ["OWNER", "ADMIN", "OPERATOR", "VIEWER"],
    },
    "get_job_openings": {
        "display_name": "Get Job Openings",
        "risk_classification": "READ",
        "requires_approval": False,
        "required_roles": ["OWNER", "ADMIN", "OPERATOR", "VIEWER"],
    },
    "get_interview_schedule": {
        "display_name": "Get Interview Schedule",
        "risk_classification": "READ",
        "requires_approval": False,
        "required_roles": ["OWNER", "ADMIN", "OPERATOR", "VIEWER"],
    },
    "create_job_opening": {
        "display_name": "Create Job Opening",
        "risk_classification": "HIGH_RISK_WRITE",
        "requires_approval": True,
        "required_roles": ["OWNER", "ADMIN", "OPERATOR"],
    },
    "update_candidate_status": {
        "display_name": "Update Candidate Status",
        "risk_classification": "HIGH_RISK_WRITE",
        "requires_approval": True,
        "required_roles": ["OWNER", "ADMIN", "OPERATOR"],
    },
}


def _validate_tenant(organization_id: str) -> None:
    if not organization_id or not isinstance(organization_id, str):
        raise ValueError("Missing or invalid organization_id for tenant isolation.")


@recruitment_mcp.tool(
    name="get_candidates",
    description="Retrieve candidates for the organization with optional filters for stage, interview_status, or minimum days waiting for an interview.",
)
def get_candidates(
    organization_id: str,
    stage: Optional[str] = None,
    interview_status: Optional[str] = None,
    min_days_waiting: Optional[int] = None,
) -> Dict[str, Any]:
    _validate_tenant(organization_id)
    with SessionLocal() as db:
        query = db.query(Candidate).filter(Candidate.organization_id == organization_id)
        if stage:
            query = query.filter(Candidate.stage == stage)
        if interview_status:
            query = query.filter(Candidate.interview_status == interview_status)
        if min_days_waiting is not None:
            query = query.filter(Candidate.days_waiting > min_days_waiting)

        records = query.order_by(Candidate.days_waiting.desc()).all()
        items = [
            {
                "id": c.id,
                "candidate_name": c.full_name,
                "email": c.email,
                "position": c.position_applied,
                "stage": c.stage,
                "interview_status": c.interview_status,
                "days_waiting": c.days_waiting,
                "days_since_contact": c.days_since_contact,
                "interview_date": c.interview_date or "Pending Schedule",
                "recruiter": c.recruiter,
                "last_communication_date": c.last_communication_date,
                "technical_score": c.technical_score,
            }
            for c in records
        ]
        return {
            "status": "success",
            "organization_id": organization_id,
            "count": len(items),
            "candidates": items,
        }


@recruitment_mcp.tool(
    name="search_candidates",
    description="Search candidates by name, position, stage, or recruiter within the organization.",
)
def search_candidates(organization_id: str, query: str) -> Dict[str, Any]:
    _validate_tenant(organization_id)
    q = f"%{query.strip()}%"
    with SessionLocal() as db:
        records = (
            db.query(Candidate)
            .filter(
                Candidate.organization_id == organization_id,
                (Candidate.full_name.ilike(q))
                | (Candidate.position_applied.ilike(q))
                | (Candidate.stage.ilike(q))
                | (Candidate.recruiter.ilike(q)),
            )
            .all()
        )
        items = [
            {
                "id": c.id,
                "candidate_name": c.full_name,
                "position": c.position_applied,
                "stage": c.stage,
                "interview_status": c.interview_status,
                "days_waiting": c.days_waiting,
                "recruiter": c.recruiter,
                "last_communication_date": c.last_communication_date,
            }
            for c in records
        ]
        return {
            "status": "success",
            "query": query,
            "count": len(items),
            "candidates": items,
        }


@recruitment_mcp.tool(
    name="get_pending_applications",
    description="Retrieve pending job applications and optionally filter for candidates who have not been contacted in N days.",
)
def get_pending_applications(
    organization_id: str, min_days_since_contact: Optional[int] = None
) -> Dict[str, Any]:
    _validate_tenant(organization_id)
    with SessionLocal() as db:
        q = (
            db.query(Application, Candidate, JobOpening)
            .join(Candidate, Application.candidate_id == Candidate.id)
            .join(JobOpening, Application.job_opening_id == JobOpening.id)
            .filter(
                Application.organization_id == organization_id,
                Application.status == "pending",
            )
        )
        if min_days_since_contact is not None:
            q = q.filter(Application.days_since_contact >= min_days_since_contact)

        rows = q.order_by(Application.days_since_contact.desc()).all()
        items = [
            {
                "application_id": app.id,
                "candidate_id": cand.id,
                "candidate_name": cand.full_name,
                "position": job.title,
                "job_code": job.job_code,
                "status": app.status,
                "stage": cand.stage,
                "applied_date": app.applied_date,
                "last_contacted_date": app.last_contacted_date,
                "days_since_contact": app.days_since_contact,
                "recruiter": app.assigned_recruiter,
                "source": app.source,
            }
            for app, cand, job in rows
        ]
        return {
            "status": "success",
            "count": len(items),
            "applications": items,
        }


@recruitment_mcp.tool(
    name="get_job_openings",
    description="List active or all job openings for the organization.",
)
def get_job_openings(
    organization_id: str, status: Optional[str] = None
) -> Dict[str, Any]:
    _validate_tenant(organization_id)
    with SessionLocal() as db:
        q = db.query(JobOpening).filter(JobOpening.organization_id == organization_id)
        if status:
            q = q.filter(JobOpening.status == status)
        jobs = q.all()
        items = [
            {
                "id": j.id,
                "job_code": j.job_code,
                "title": j.title,
                "department": j.department_name,
                "location": j.location,
                "salary_range": j.salary_range,
                "status": j.status,
                "hiring_manager": j.hiring_manager,
                "openings_count": j.openings_count,
            }
            for j in jobs
        ]
        return {"status": "success", "count": len(items), "job_openings": items}


@recruitment_mcp.tool(
    name="get_interview_schedule",
    description="Retrieve candidate interview records and technical interview outcomes.",
)
def get_interview_schedule(
    organization_id: str, interview_status: Optional[str] = None
) -> Dict[str, Any]:
    _validate_tenant(organization_id)
    with SessionLocal() as db:
        q = db.query(Candidate).filter(Candidate.organization_id == organization_id)
        if interview_status:
            q = q.filter(Candidate.interview_status == interview_status)
        rows = q.order_by(Candidate.technical_score.desc()).all()
        items = [
            {
                "id": c.id,
                "candidate_name": c.full_name,
                "position": c.position_applied,
                "interview_date": c.interview_date or "2026-11-05",
                "current_status": c.stage,
                "interview_status": c.interview_status,
                "technical_score": c.technical_score,
                "recruiter": c.recruiter,
                "last_communication_date": c.last_communication_date,
            }
            for c in rows
        ]
        return {"status": "success", "count": len(items), "interviews": items}


@recruitment_mcp.tool(
    name="create_job_opening",
    description="Create a new job opening in the recruitment database (High-Risk Write - requires approval).",
)
def create_job_opening(
    organization_id: str,
    title: str,
    salary_range: str,
    department_name: str = "Engineering",
    location: str = "Bengaluru / Hybrid",
    openings_count: int = 2,
    hiring_manager: str = "Vikram Mehta",
) -> Dict[str, Any]:
    _validate_tenant(organization_id)
    with SessionLocal() as db:
        existing_count = (
            db.query(JobOpening)
            .filter(JobOpening.organization_id == organization_id)
            .count()
        )
        job_code = f"JOB-2026-{existing_count + 101}"
        new_job = JobOpening(
            organization_id=organization_id,
            job_code=job_code,
            title=title,
            department_name=department_name,
            location=location,
            employment_type="Full-Time",
            salary_range=salary_range,
            status="open",
            hiring_manager=hiring_manager,
            openings_count=openings_count,
        )
        db.add(new_job)
        db.commit()
        db.refresh(new_job)
        return {
            "status": "success",
            "message": f"Created job opening '{title}' ({job_code}) with salary range {salary_range}.",
            "job_opening": {
                "id": new_job.id,
                "job_code": new_job.job_code,
                "title": new_job.title,
                "department": new_job.department_name,
                "location": new_job.location,
                "salary_range": new_job.salary_range,
                "status": new_job.status,
                "openings_count": new_job.openings_count,
                "hiring_manager": new_job.hiring_manager,
            },
        }


@recruitment_mcp.tool(
    name="update_candidate_status",
    description="Move one or more candidates to a new recruitment stage (e.g., 'shortlisted', 'offer_extended', 'rejected'). High-Risk Write.",
)
def update_candidate_status(
    organization_id: str,
    candidate_ids: List[str],
    new_stage: str,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    _validate_tenant(organization_id)
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    updated_records = []
    with SessionLocal() as db:
        candidates = (
            db.query(Candidate)
            .filter(
                Candidate.organization_id == organization_id,
                Candidate.id.in_(candidate_ids),
            )
            .all()
        )
        for cand in candidates:
            previous_stage = cand.stage
            cand.stage = new_stage
            if new_stage == "shortlisted":
                cand.interview_status = "scheduled"
            cand.last_communication_date = today_str
            cand.days_since_contact = 0
            if notes:
                cand.notes = notes

            # Also sync corresponding application status if present
            apps = (
                db.query(Application)
                .filter(
                    Application.organization_id == organization_id,
                    Application.candidate_id == cand.id,
                )
                .all()
            )
            for app in apps:
                app.status = new_stage
                app.last_contacted_date = today_str
                app.days_since_contact = 0

            updated_records.append(
                {
                    "id": cand.id,
                    "candidate_name": cand.full_name,
                    "position": cand.position_applied,
                    "previous_stage": previous_stage,
                    "new_stage": cand.stage,
                    "recruiter": cand.recruiter,
                    "updated_date": today_str,
                }
            )
        db.commit()
    return {
        "status": "success",
        "updated_count": len(updated_records),
        "new_stage": new_stage,
        "updated_candidates": updated_records,
    }


if __name__ == "__main__":
    recruitment_mcp.run(transport="stdio")

