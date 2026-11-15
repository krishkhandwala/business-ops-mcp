# NEXUS — AI-Native Business Operations Platform

> **"Your business systems become tools. Your AI becomes the interface. Your instructions become workflows. Your backend performs the actual work."**

NEXUS is a multi-tenant enterprise AI operations platform powered by the **Model Context Protocol (MCP)** and **LangGraph** stateful workflow orchestration. Instead of navigating separate recruitment, HR, billing, and BI dashboards, operators issue natural-language instructions that discover and invoke real MCP tools with backend-enforced **Role-Based Access Control (RBAC)** and **Human Approval Gates**.

---

## 1. Architecture Overview

### Frontend (`frontend/`)
- **Framework**: Next.js 14 (App Router), TypeScript, Tailwind CSS
- **Visualization & Icons**: Recharts, Lucide Icons, Framer Motion
- **Enterprise Dark Design System**:
  - Primary Background: `#0B0D10`
  - Secondary Background: `#11151B`
  - Card Surface: `#151A22`
  - Subtle Borders: `#252B35`
  - Accent: `#8B7CFF` | Success: `#36C98F` | Warning: `#E9AE54` | Error: `#F06C75`

### Backend & AI Layer (`backend/`)
- **API & ORM**: FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic migrations
- **Official MCP Architecture**:
  - Uses the official Python `mcp` SDK (`MCPServer`, `mcp.Client`, `StdioServerParameters`)
  - 4 Domain-Separated MCP Servers (`backend/app/mcp_servers/`):
    1. **Recruitment MCP Server** (`recruitment_server.py`): `get_candidates`, `search_candidates`, `get_pending_applications`, `get_job_openings`, `get_interview_schedule`, `create_job_opening`, `update_candidate_status`
    2. **Employee & HRMS MCP Server** (`employee_server.py`): `get_employees`, `get_employee_details`, `get_attendance`, `get_leave_records`, `get_document_expiry`, `notify_managers`
    3. **Finance & Billing MCP Server** (`finance_server.py`): `get_invoices`, `get_expenses`, `get_payment_status`, `generate_financial_summary`, `send_invoice_reminders`
    4. **Analytics & BI MCP Server** (`analytics_server.py`): `get_business_metrics`, `generate_report`, `compare_periods`
- **LangGraph Workflow Engine (`backend/app/services/workflow_engine.py`)**:
  - Stateful nodes: `intent_detection` → `context_retrieval` → `tool_discovery` → `execution_planning` → `tool_execution_and_approval_gate` → `result_validation_and_response`
  - OpenAI-compatible LLM provider abstraction + deterministic semantic-to-MCP router fallback
- **Security & Governance (`backend/app/core/security.py`)**:
  - JWT access tokens + refresh token rotation
  - Fernet AES-128-CBC + HMAC encryption at rest for all MCP server & integration credentials
  - Strict multi-tenant isolation (`organization_id` injected and verified at the backend & MCP client layer)
  - Backend-enforced Human Approval Engine for `HIGH_RISK_WRITE` operations
  - Prompt injection detection & untrusted MCP tool output sanitization

---

## 2. Quick Start

### Option A: Docker Compose (Full Stack with PostgreSQL & Redis)

```bash
cp .env.example .env
docker compose up --build
```

- **Frontend Command Center**: `http://localhost:3000`
- **Backend FastAPI & OpenAPI Docs**: `http://localhost:8000/docs`

### Option B: Local Development

#### 1. Start the Backend
```bash
cd backend
pip install -r requirements.txt
# Run Alembic database migrations
alembic upgrade head
# Start FastAPI server on port 8000
uvicorn app.main:app --reload --port 8000
```

#### 2. Start the Frontend
```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000` in your browser.

---

## 3. Running Automated End-to-End Tests

The test suite verifies authentication, refresh token rotation, dynamic MCP tool discovery over the official `mcp` SDK, both **MVP Acceptance Criteria**, cross-domain analytics, prompt injection blocking, and multi-tenant isolation:

```bash
PYTHONPATH=backend pytest backend/tests/test_nexus_e2e.py -v
```

---

## 4. Seeded Enterprise RBAC Personas

You can switch between all 4 RBAC roles directly from the bottom-left sidebar switcher in the UI:

| Role | Email | Password | Capabilities |
| :--- | :--- | :--- | :--- |
| **OWNER** | `arjun.mehta@nexus.io` | `Nexus@2026!` | Full organization, MCP server, integration, workflow & approval access |
| **ADMIN** | `priya.nair@nexus.io` | `Nexus@2026!` | Manage integrations, MCP servers, tools, permissions, and approvals |
| **OPERATOR** | `ananya.sharma@nexus.io` | `Nexus@2026!` | Execute AI workflows and approve operational writes |
| **VIEWER** | `rohit.verma@nexus.io` | `Nexus@2026!` | Read-only access; blocked (`403`) from approving high-risk writes |

