"""
Enterprise Seed & Bootstrap Service
Populates sample organizations, RBAC roles/permissions, real domain data
(Employees, Departments, Job Openings, Candidates, Applications, Attendance, Invoices, Expenses),
registers the 4 Domain MCP Servers, and performs live MCP protocol tool discovery.
"""
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.orm import Session

from app.core.security import encrypt_secret, hash_password
from app.models.entities import (
    Agent,
    AgentExecution,
    Application,
    AttendanceRecord,
    AuditLog,
    Candidate,
    Department,
    Employee,
    ExecutionStep,
    Expense,
    Integration,
    IntegrationCredential,
    Invoice,
    JobOpening,
    LeaveRecord,
    MCPServerModel,
    Organization,
    OrganizationMember,
    Permission,
    Role,
    ToolInvocation,
    UsageRecord,
    User,
    WorkflowTemplate,
)
from app.services.mcp_client import mcp_client_manager


async def ensure_enterprise_seed(db: Session) -> Organization:
    existing_org = (
        db.query(Organization)
        .filter(Organization.slug == "nexus-enterprise")
        .first()
    )
    if existing_org:
        return existing_org

    # 1. Create Primary Organization & Secondary Organization (for tenant isolation verification)
    primary_org = Organization(
        name="Nexus Enterprise Operations",
        slug="nexus-enterprise",
        domain="nexus-enterprise.io",
        plan_tier="enterprise",
        approval_policy={
            "require_approval_for_high_risk": True,
            "require_approval_for_low_risk": False,
            "allowed_approver_roles": ["OWNER", "ADMIN", "OPERATOR"],
            "max_auto_tool_calls": 10,
        },
        settings_json={
            "timezone": "Asia/Kolkata",
            "currency": "INR",
            "audit_retention_days": 365,
            "redact_pii_in_logs": True,
        },
    )
    secondary_org = Organization(
        name="Beta Dynamics Corp",
        slug="beta-dynamics",
        domain="betadynamics.io",
        plan_tier="pro",
    )
    db.add_all([primary_org, secondary_org])
    db.commit()
    db.refresh(primary_org)
    db.refresh(secondary_org)

    # 2. Roles & Granular Permissions
    roles_spec = [
        ("OWNER", "Full organization, security, billing, integration, and workflow access."),
        ("ADMIN", "Manage integrations, MCP servers, tools, permissions, and users."),
        ("OPERATOR", "Execute authorized AI workflows and review operational approvals."),
        ("VIEWER", "Read-only access to authorized data, analytics, and execution history."),
    ]
    for r_name, r_desc in roles_spec:
        db.add(
            Role(
                organization_id=primary_org.id,
                name=r_name,
                description=r_desc,
                is_system=True,
            )
        )

    perm_matrix = [
        ("OWNER", "mcp_servers", "manage", True),
        ("OWNER", "tools", "execute", True),
        ("OWNER", "approvals", "approve", True),
        ("OWNER", "organization", "manage", True),
        ("ADMIN", "mcp_servers", "manage", True),
        ("ADMIN", "tools", "execute", True),
        ("ADMIN", "approvals", "approve", True),
        ("ADMIN", "organization", "manage", True),
        ("OPERATOR", "mcp_servers", "read", True),
        ("OPERATOR", "tools", "execute", True),
        ("OPERATOR", "approvals", "approve", True),
        ("VIEWER", "mcp_servers", "read", True),
        ("VIEWER", "tools", "read", True),
        ("VIEWER", "approvals", "approve", False),
    ]
    for r_name, res, act, allowed in perm_matrix:
        db.add(
            Permission(
                organization_id=primary_org.id,
                role_name=r_name,
                resource=res,
                action=act,
                allowed=allowed,
            )
        )

    # 3. Users & Memberships
    default_pw = hash_password("Nexus@2026!")
    u_owner = User(
        email="arjun.mehta@nexus.io",
        full_name="Arjun Mehta",
        hashed_password=default_pw,
        last_login_at=datetime.now(timezone.utc),
    )
    u_admin = User(
        email="priya.nair@nexus.io",
        full_name="Priya Nair",
        hashed_password=default_pw,
    )
    u_operator = User(
        email="ananya.sharma@nexus.io",
        full_name="Ananya Sharma",
        hashed_password=default_pw,
    )
    u_viewer = User(
        email="rohit.verma@nexus.io",
        full_name="Rohit Verma",
        hashed_password=default_pw,
    )
    u_tenant2 = User(
        email="tenant2@betadynamics.io",
        full_name="Elena Rostova",
        hashed_password=default_pw,
    )
    db.add_all([u_owner, u_admin, u_operator, u_viewer, u_tenant2])
    db.commit()
    for u in (u_owner, u_admin, u_operator, u_viewer, u_tenant2):
        db.refresh(u)

    db.add_all(
        [
            OrganizationMember(
                organization_id=primary_org.id, user_id=u_owner.id, role="OWNER"
            ),
            OrganizationMember(
                organization_id=primary_org.id, user_id=u_admin.id, role="ADMIN"
            ),
            OrganizationMember(
                organization_id=primary_org.id, user_id=u_operator.id, role="OPERATOR"
            ),
            OrganizationMember(
                organization_id=primary_org.id, user_id=u_viewer.id, role="VIEWER"
            ),
            OrganizationMember(
                organization_id=secondary_org.id, user_id=u_tenant2.id, role="OWNER"
            ),
        ]
    )
    db.commit()

    # 4. Business Domain Data (Departments, Employees, Job Openings, Candidates, Applications, Attendance, Invoices, Expenses)
    dept_eng = Department(
        organization_id=primary_org.id,
        name="Engineering",
        code="ENG",
        head_name="Vikram Mehta",
        annual_budget_inr=48000000.0,
    )
    dept_prod = Department(
        organization_id=primary_org.id,
        name="Product & Design",
        code="PRD",
        head_name="Priya Kulkarni",
        annual_budget_inr=22000000.0,
    )
    dept_sales = Department(
        organization_id=primary_org.id,
        name="Enterprise Sales",
        code="SLS",
        head_name="Rajesh Iyer",
        annual_budget_inr=31000000.0,
    )
    dept_hr = Department(
        organization_id=primary_org.id,
        name="People & Talent",
        code="HR",
        head_name="Ananya Sharma",
        annual_budget_inr=12000000.0,
    )
    db.add_all([dept_eng, dept_prod, dept_sales, dept_hr])
    db.commit()

    employees_data = [
        ("EMP-1001", "Rohan Verma", "rohan.verma@nexus.io", dept_eng.id, "Engineering", "Senior Distributed Systems Engineer", "Vikram Mehta", "vikram.mehta@nexus-enterprise.io", 28.0, "2024-03-15", "H-1B / Work Permit Visa", "2026-12-08"),
        ("EMP-1002", "Meera Nair", "meera.nair@nexus.io", dept_prod.id, "Product & Design", "Lead Product Designer", "Priya Kulkarni", "priya.kulkarni@nexus-enterprise.io", 24.0, "2023-07-10", "Passport & EU Business Visa", "2026-12-14"),
        ("EMP-1003", "Kabir Malhotra", "kabir.malhotra@nexus.io", dept_eng.id, "Engineering", "Staff Infrastructure Engineer", "Vikram Mehta", "vikram.mehta@nexus-enterprise.io", 36.0, "2022-11-01", "AWS Security Clearance Cert", "2026-12-19"),
        ("EMP-1004", "Arjun Deshmukh", "arjun.deshmukh@nexus.io", dept_eng.id, "Engineering", "Backend Platform Developer", "Vikram Mehta", "vikram.mehta@nexus-enterprise.io", 18.5, "2025-01-20", "Passport", "2028-06-30"),
        ("EMP-1005", "Neha Gupta", "neha.gupta@nexus.io", dept_prod.id, "Product & Design", "Senior Product Manager", "Priya Kulkarni", "priya.kulkarni@nexus-enterprise.io", 27.0, "2024-05-12", "Passport", "2029-04-15"),
        ("EMP-1006", "Siddharth Joshi", "siddharth.joshi@nexus.io", dept_sales.id, "Enterprise Sales", "Enterprise Account Director", "Rajesh Iyer", "rajesh.iyer@nexus-enterprise.io", 22.0, "2024-08-01", "APAC Work Authorization", "2026-12-22"),
        ("EMP-1007", "Divya Krishnan", "divya.krishnan@nexus.io", dept_eng.id, "Engineering", "AI/ML Research Engineer", "Vikram Mehta", "vikram.mehta@nexus-enterprise.io", 32.0, "2024-02-14", "Passport", "2030-01-10"),
        ("EMP-1008", "Karan Singhania", "karan.singhania@nexus.io", dept_hr.id, "People & Talent", "Technical Recruiting Lead", "Ananya Sharma", "ananya.sharma@nexus.io", 16.5, "2023-09-04", "Passport", "2029-08-22"),
    ]
    emp_objs = []
    for code, name, email, d_id, d_name, desig, mgr_name, mgr_email, sal, joined, doc_type, doc_exp in employees_data:
        emp = Employee(
            organization_id=primary_org.id,
            employee_code=code,
            full_name=name,
            email=email,
            department_id=d_id,
            department_name=d_name,
            designation=desig,
            manager_name=mgr_name,
            manager_email=mgr_email,
            salary_lpa=sal,
            joined_date=joined,
            document_type=doc_type,
            document_expiry_date=doc_exp,
        )
        db.add(emp)
        emp_objs.append(emp)
    db.commit()
    for e in emp_objs:
        db.refresh(e)

    # Attendance & Leave Records
    attendance_seed = [
        (emp_objs[3], "2026-11-14", "missing", 4, 0.0),
        (emp_objs[4], "2026-11-14", "missing", 3, 0.0),
        (emp_objs[5], "2026-11-14", "missing", 3, 0.0),
        (emp_objs[0], "2026-11-14", "present", 0, 8.5),
        (emp_objs[1], "2026-11-14", "present", 0, 8.0),
        (emp_objs[2], "2026-11-14", "present", 0, 9.0),
    ]
    for emp_o, dt, st, streak, hrs in attendance_seed:
        db.add(
            AttendanceRecord(
                organization_id=primary_org.id,
                employee_id=emp_o.id,
                employee_name=emp_o.full_name,
                department_name=emp_o.department_name,
                manager_name=emp_o.manager_name or "Vikram Mehta",
                manager_email=emp_o.manager_email or "vikram.mehta@nexus-enterprise.io",
                date=dt,
                status=st,
                missing_days_streak=streak,
                hours_logged=hrs,
            )
        )
    db.add(
        LeaveRecord(
            organization_id=primary_org.id,
            employee_id=emp_objs[6].id,
            employee_name=emp_objs[6].full_name,
            leave_type="Annual Leave",
            start_date="2026-11-18",
            end_date="2026-11-21",
            days_count=4,
            status="approved",
        )
    )

    # Job Openings
    job_backend = JobOpening(
        organization_id=primary_org.id,
        job_code="JOB-2026-101",
        title="Principal Backend Architect",
        department_name="Engineering",
        location="Bengaluru / Hybrid",
        salary_range="₹28–38 LPA",
        status="open",
        hiring_manager="Vikram Mehta",
        openings_count=2,
    )
    job_ai = JobOpening(
        organization_id=primary_org.id,
        job_code="JOB-2026-102",
        title="Senior AI Platform Engineer",
        department_name="Engineering",
        location="Bengaluru / Remote",
        salary_range="₹24–34 LPA",
        status="open",
        hiring_manager="Vikram Mehta",
        openings_count=3,
    )
    job_fe = JobOpening(
        organization_id=primary_org.id,
        job_code="JOB-2026-103",
        title="Staff Frontend Systems Engineer",
        department_name="Product & Design",
        location="Mumbai / Hybrid",
        salary_range="₹20–28 LPA",
        status="open",
        hiring_manager="Priya Kulkarni",
        openings_count=2,
    )
    db.add_all([job_backend, job_ai, job_fe])
    db.commit()
    for j in (job_backend, job_ai, job_fe):
        db.refresh(j)

    # Candidates (8 waiting > 7 days for an interview + 4 who passed technical interview without offer)
    candidates_seed = [
        ("Aarav Patel", "aarav.patel@devmail.in", "Principal Backend Architect", job_backend.id, "interview_pending", "waiting_for_interview", 14, 11, "2026-10-31", "2026-11-03", "Ananya Sharma", 7.5, 92.0),
        ("Ishita Sengupta", "ishita.sengupta@techmail.io", "Senior AI Platform Engineer", job_ai.id, "interview_pending", "waiting_for_interview", 12, 10, "2026-11-02", "2026-11-04", "Ananya Sharma", 6.0, 94.5),
        ("Devansh Rao", "devansh.rao@cloudops.in", "Principal Backend Architect", job_backend.id, "interview_pending", "waiting_for_interview", 11, 9, "2026-11-03", "2026-11-05", "Karan Singhania", 8.0, 89.0),
        ("Tanvi Bhatia", "tanvi.bhatia@aiworks.dev", "Senior AI Platform Engineer", job_ai.id, "interview_pending", "waiting_for_interview", 10, 9, "2026-11-04", "2026-11-05", "Ananya Sharma", 5.5, 91.0),
        ("Pranav Kulkarni", "pranav.k@systems.io", "Staff Frontend Systems Engineer", job_fe.id, "interview_pending", "waiting_for_interview", 9, 8, "2026-11-05", "2026-11-06", "Karan Singhania", 6.5, 88.5),
        ("Nandini Menon", "nandini.menon@uxstack.in", "Staff Frontend Systems Engineer", job_fe.id, "interview_pending", "waiting_for_interview", 8, 8, "2026-11-06", "2026-11-06", "Ananya Sharma", 5.0, 87.0),
        ("Rishi Chatterjee", "rishi.c@distributed.io", "Principal Backend Architect", job_backend.id, "technical_passed", "technical_passed", 6, 4, "2026-11-08", "2026-11-10", "Ananya Sharma", 7.0, 95.0),
        ("Sanya Kapoor", "sanya.kapoor@mlops.ai", "Senior AI Platform Engineer", job_ai.id, "technical_passed", "technical_passed", 5, 3, "2026-11-09", "2026-11-11", "Karan Singhania", 5.5, 93.0),
        ("Harshvardhan Gill", "harsh.gill@coredev.in", "Principal Backend Architect", job_backend.id, "technical_passed", "technical_passed", 4, 2, "2026-11-10", "2026-11-12", "Ananya Sharma", 6.5, 90.5),
    ]
    for name, email, pos, j_id, stage, int_stat, wait_d, contact_d, int_dt, last_comm, rec, exp_y, score in candidates_seed:
        cand = Candidate(
            organization_id=primary_org.id,
            full_name=name,
            email=email,
            position_applied=pos,
            job_opening_id=j_id,
            stage=stage,
            interview_status=int_stat,
            days_waiting=wait_d,
            days_since_contact=contact_d,
            interview_date=int_dt,
            last_communication_date=last_comm,
            recruiter=rec,
            experience_years=exp_y,
            technical_score=score,
        )
        db.add(cand)
        db.commit()
        db.refresh(cand)

        if stage == "interview_pending":
            db.add(
                Application(
                    organization_id=primary_org.id,
                    candidate_id=cand.id,
                    job_opening_id=j_id,
                    status="pending",
                    applied_date="2026-10-28",
                    last_contacted_date=last_comm,
                    days_since_contact=contact_d,
                    assigned_recruiter=rec,
                    source="LinkedIn Enterprise",
                )
            )

    # Also add a candidate in Secondary Organization to test strict tenant isolation
    db.add(
        Candidate(
            organization_id=secondary_org.id,
            full_name="Tenant Two Secret Candidate",
            email="secret@betadynamics.io",
            position_applied="Stealth Researcher",
            stage="interview_pending",
            interview_status="waiting_for_interview",
            days_waiting=15,
            days_since_contact=15,
            last_communication_date="2026-10-30",
            recruiter="Elena Rostova",
        )
    )

    # Finance Invoices & Expenses
    invoices_seed = [
        ("INV-2026-084", "Apex FinTech Solutions Pvt Ltd", "billing@apexfintech.in", 840000.0, "overdue", "2026-10-01", "2026-10-31", 14),
        ("INV-2026-089", "Horizon Logistics Group", "accounts@horizonlogistics.io", 520000.0, "overdue", "2026-10-10", "2026-11-05", 9),
        ("INV-2026-092", "Vanguard Retail Cloud", "finance@vanguardretail.com", 390000.0, "unpaid", "2026-10-25", "2026-11-15", 0),
        ("INV-2026-078", "Meridian Health Systems", "ap@meridianhealth.org", 1250000.0, "paid", "2026-09-15", "2026-10-15", 0),
        ("INV-2026-081", "Quantum Semiconductor India", "treasury@quantumsemi.in", 980000.0, "paid", "2026-10-01", "2026-10-30", 0),
    ]
    for inv_no, c_name, c_email, amt, st, iss_dt, due_dt, over_d in invoices_seed:
        db.add(
            Invoice(
                organization_id=primary_org.id,
                invoice_number=inv_no,
                client_name=c_name,
                client_email=c_email,
                amount_inr=amt,
                status=st,
                issue_date=iss_dt,
                due_date=due_dt,
                days_overdue=over_d,
            )
        )

    expenses_seed = [
        # 2026-10
        ("Cloud Infrastructure", "2026-10", 620000.0, "AWS Enterprise Cloud", "Production Kubernetes & RDS clusters", "Vikram Mehta"),
        ("AI/LLM Compute", "2026-10", 280000.0, "OpenAI & GPU Inference", "Agentic token & vector embeddings usage", "Vikram Mehta"),
        ("Payroll", "2026-10", 3400000.0, "Nexus Payroll Treasury", "Monthly engineering & operations salaries", "Arjun Mehta"),
        ("Recruitment & Marketing", "2026-10", 190000.0, "LinkedIn Talent Solutions", "Technical recruitment campaigns", "Ananya Sharma"),
        ("SaaS Licenses", "2026-10", 145000.0, "Linear / GitHub / Datadog", "Developer & observability seats", "Priya Nair"),
        # 2026-11
        ("Cloud Infrastructure", "2026-11", 795000.0, "AWS Enterprise Cloud", "Multi-region failover + new staging cluster", "Vikram Mehta"),
        ("AI/LLM Compute", "2026-11", 410000.0, "OpenAI & GPU Inference", "Expanded MCP workflow automation volume", "Vikram Mehta"),
        ("Payroll", "2026-11", 3450000.0, "Nexus Payroll Treasury", "Monthly engineering & operations salaries", "Arjun Mehta"),
        ("Recruitment & Marketing", "2026-11", 265000.0, "LinkedIn Talent Solutions", "Q4 Senior Backend & AI hiring surge", "Ananya Sharma"),
        ("SaaS Licenses", "2026-11", 150000.0, "Linear / GitHub / Datadog", "Developer & observability seats", "Priya Nair"),
    ]
    for cat, mo, amt, vend, desc, appr in expenses_seed:
        db.add(
            Expense(
                organization_id=primary_org.id,
                category=cat,
                month=mo,
                amount_inr=amt,
                vendor=vend,
                description=desc,
                approved_by=appr,
            )
        )
    db.commit()

    # 5. Register the 4 Official MCP Servers & Dynamically Discover Tools via MCP Protocol
    mcp_dir = Path(__file__).resolve().parents[1] / "mcp_servers"
    servers_spec = [
        (
            "Recruitment MCP Server",
            "recruitment-mcp",
            "recruitment",
            "Exposes talent acquisition pipeline, candidate search, interview scheduling, and job opening management tools via MCP.",
            "stdio",
            str(mcp_dir / "recruitment_server.py"),
        ),
        (
            "Employee & HRMS MCP Server",
            "employee-mcp",
            "employee",
            "Exposes employee directory, attendance compliance, leave records, and visa/document expiry monitoring via MCP.",
            "stdio",
            str(mcp_dir / "employee_server.py"),
        ),
        (
            "Finance & Billing MCP Server",
            "finance-mcp",
            "finance",
            "Exposes client invoices, receivables status, monthly expense ledgers, and automated client payment reminders via MCP.",
            "stdio",
            str(mcp_dir / "finance_server.py"),
        ),
        (
            "Analytics & BI MCP Server",
            "analytics-mcp",
            "analytics",
            "Exposes cross-domain executive KPIs, recruitment performance reports, and period-over-period variance analysis via MCP.",
            "stdio",
            str(mcp_dir / "analytics_server.py"),
        ),
    ]
    created_servers = []
    for s_name, s_slug, s_dom, s_desc, s_trans, s_end in servers_spec:
        srv = MCPServerModel(
            organization_id=primary_org.id,
            name=s_name,
            slug=s_slug,
            domain=s_dom,
            description=s_desc,
            transport_type=s_trans,
            endpoint=s_end,
            auth_method="internal_token",
            encrypted_credentials=encrypt_secret({"token_scope": s_dom, "protocol": "mcp/2025-11-25"}),
            status="connected",
            health_status="healthy",
            is_enabled=True,
        )
        db.add(srv)
        created_servers.append(srv)
    db.commit()

    for srv in created_servers:
        db.refresh(srv)
        await mcp_client_manager.discover_and_sync_tools(db, srv)

    # Also register Recruitment MCP server for secondary_org so tenant isolation tests can invoke MCP tools too
    srv_t2 = MCPServerModel(
        organization_id=secondary_org.id,
        name="Beta Recruitment MCP Server",
        slug="beta-recruitment-mcp",
        domain="recruitment",
        description="Isolated Recruitment MCP server for Beta Dynamics Corp.",
        transport_type="stdio",
        endpoint=str(mcp_dir / "recruitment_server.py"),
        auth_method="internal_token",
        encrypted_credentials=encrypt_secret({"token_scope": "recruitment"}),
        status="connected",
        health_status="healthy",
        is_enabled=True,
    )
    db.add(srv_t2)
    db.commit()
    db.refresh(srv_t2)
    await mcp_client_manager.discover_and_sync_tools(db, srv_t2)

    # 6. Integrations Marketplace (Real connected status only for established PostgreSQL & Internal FastAPI connections)
    integrations_catalog = [
        (
            "postgresql",
            "PostgreSQL Enterprise Database",
            "Databases",
            "Primary multi-tenant relational database backing Recruitment, HRMS, and Finance MCP servers.",
            "connected",
            {"host": "localhost", "port": 5432, "database": "nexus_ops", "ssl_mode": "prefer"},
            ["get_candidates", "get_employees", "get_invoices", "get_expenses", "update_candidate_status"],
            ["db:read", "db:write:approved"],
            created_servers[0].id,
        ),
        (
            "fastapi_internal",
            "Internal FastAPI Microservices",
            "Custom APIs",
            "Internal business operations microservices connected via authenticated MCP bridge.",
            "connected",
            {"base_url": "http://localhost:8000/api/v1", "timeout_sec": 30},
            ["get_business_metrics", "generate_report", "compare_periods"],
            ["service:invoke", "metrics:read"],
            created_servers[3].id,
        ),
        (
            "custom_rest",
            "Custom REST API Gateway",
            "Custom APIs",
            "Connect any OpenAPI / REST endpoint and expose its operations as governed MCP tools.",
            "disconnected",
            {"base_url": "", "auth_header": "Authorization"},
            ["custom_http_get", "custom_http_post"],
            ["api:read", "api:write"],
            None,
        ),
        (
            "slack",
            "Slack Enterprise Grid",
            "Communication",
            "Dispatch operational notifications, approval alerts, and manager escalations to Slack channels.",
            "disconnected",
            {"workspace": "", "default_channel": "#ops-alerts"},
            ["send_channel_message", "notify_managers"],
            ["chat:write", "users:read"],
            None,
        ),
        (
            "gmail",
            "Google Workspace / Gmail",
            "Communication",
            "Send transactional candidate updates, interview invites, and client invoice reminders.",
            "disconnected",
            {"sender_domain": "nexus-enterprise.io"},
            ["send_invoice_reminders", "notify_managers"],
            ["mail:send", "mail:draft"],
            None,
        ),
        (
            "google_sheets",
            "Google Sheets BI Sync",
            "Finance",
            "Synchronize financial ledgers, expense comparisons, and board reporting spreadsheets.",
            "disconnected",
            {"spreadsheet_id": ""},
            ["export_sheet_rows", "read_sheet_range"],
            ["sheets:read", "sheets:write"],
            None,
        ),
        (
            "notion",
            "Notion Knowledge & Wiki",
            "Project Management",
            "Index internal SOPs, onboarding policies, and engineering RFCs for agent context.",
            "disconnected",
            {"workspace_id": ""},
            ["search_notion_pages", "create_sop_draft"],
            ["pages:read", "pages:write"],
            None,
        ),
        (
            "mysql",
            "MySQL Analytics Replica",
            "Databases",
            "Connect external MySQL read-replicas for legacy ERP and inventory querying.",
            "disconnected",
            {"host": "", "port": 3306},
            ["query_erp_replica"],
            ["db:read"],
            None,
        ),
    ]
    for p_key, i_name, i_cat, i_desc, i_stat, pub_cfg, avail_tools, perms, linked_srv in integrations_catalog:
        integ = Integration(
            organization_id=primary_org.id,
            provider_key=p_key,
            name=i_name,
            category=i_cat,
            description=i_desc,
            status=i_stat,
            public_config=pub_cfg,
            available_tools=avail_tools,
            permissions_scope=perms,
            linked_mcp_server_id=linked_srv,
            connected_by_user_id=u_owner.id if i_stat == "connected" else None,
            last_tested_at=datetime.now(timezone.utc) if i_stat == "connected" else None,
        )
        db.add(integ)
        db.commit()
        db.refresh(integ)
        if i_stat == "connected":
            db.add(
                IntegrationCredential(
                    organization_id=primary_org.id,
                    integration_id=integ.id,
                    auth_type="connection_string",
                    encrypted_payload=encrypt_secret({"dsn": "postgresql://***@localhost:5432/nexus_ops"}),
                    key_hint="...5432/nexus_ops",
                )
            )

    # 7. Workflow Templates
    templates_spec = [
        (
            "Interview Bottleneck & Shortlist Escalation",
            "Identify candidates waiting > 7 days for an interview and prepare stage updates.",
            "Recruitment",
            "Show me all candidates who have been waiting for an interview for more than seven days.",
            ["Discover Recruitment MCP tools", "Query candidates waiting > 7 days", "Render structured candidate table"],
            ["recruitment"],
            "READ",
        ),
        (
            "Pending Applications 7-Day Follow-up Audit",
            "List all pending job applications where candidates have not been contacted in 7+ days.",
            "Recruitment",
            "Show me all pending job applications and identify candidates who haven't been contacted in seven days.",
            ["Query pending job applications", "Filter by days_since_contact >= 7", "Highlight recruiter assignments"],
            ["recruitment"],
            "READ",
        ),
        (
            "Employee Document Expiry & Manager Notification",
            "Find employees with visas/passports expiring within 45 days and queue manager notifications.",
            "HRMS",
            "Find employees whose documents are expiring next month and prepare notifications for their managers.",
            ["Query Employee MCP for expiring documents", "Prepare manager notification batch", "Request Human Approval before dispatch"],
            ["employee"],
            "HIGH_RISK_WRITE",
        ),
        (
            "Missing Attendance 3-Day Compliance Workflow",
            "Identify employees missing attendance for 3+ consecutive days and notify their managers.",
            "HRMS",
            "Find all employees who haven't submitted their attendance for the past three days and notify their managers.",
            ["Query Attendance records", "Filter missing_days_streak >= 3", "Request Human Approval for manager notifications"],
            ["employee"],
            "HIGH_RISK_WRITE",
        ),
        (
            "Overdue Client Invoice Reminder Automation",
            "Retrieve all unpaid/overdue invoices and dispatch payment reminders after approval.",
            "Finance",
            "Identify all unpaid invoices and send reminders to the respective clients.",
            ["Query unpaid & overdue invoices", "Calculate total outstanding receivables", "Request Human Approval to send client reminders"],
            ["finance"],
            "HIGH_RISK_WRITE",
        ),
        (
            "Month-over-Month Expense Variance Analysis",
            "Compare current month expenses against last month and explain key cost drivers.",
            "Executive BI",
            "Compare this month's expenses with last month and explain the major differences.",
            ["Invoke compare_periods on Analytics MCP", "Fetch itemized expenses from Finance MCP", "Render variance table & chart"],
            ["analytics", "finance"],
            "READ",
        ),
    ]
    for t_name, t_desc, t_cat, t_prompt, t_steps, t_doms, t_risk in templates_spec:
        db.add(
            WorkflowTemplate(
                organization_id=primary_org.id,
                name=t_name,
                description=t_desc,
                category=t_cat,
                prompt_template=t_prompt,
                steps_definition=t_steps,
                required_DOMAINS=t_doms,
                risk_level=t_risk,
                is_active=True,
                run_count=3,
            )
        )

    # 8. Default AI Agent & Initial Audit Log
    db.add(
        Agent(
            organization_id=primary_org.id,
            name="NEXUS Operations Core Agent",
            role_description="Primary LangGraph multi-domain operations orchestrator connected to Recruitment, HRMS, Finance, and Analytics MCP servers.",
            llm_model="gpt-4o-mini",
            allowed_domains=["recruitment", "employee", "finance", "analytics"],
            max_steps=10,
            is_active=True,
        )
    )
    db.add(
        AuditLog(
            organization_id=primary_org.id,
            actor_user_id=u_owner.id,
            actor_email=u_owner.email,
            actor_role="OWNER",
            action="organization_bootstrapped",
            resource_type="organization",
            resource_id=primary_org.id,
            status="success",
            ip_address="127.0.0.1",
            metadata_json={"mcp_servers_connected": 4, "rbac_roles_initialized": 4},
        )
    )
    db.commit()
    return primary_org

