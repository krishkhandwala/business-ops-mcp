"use client";

import React, { useState } from "react";
import {
  Users,
  KeyRound,
  FileSearch,
  Settings,
  UserPlus,
  ShieldCheck,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { OrganizationProfile } from "@/types/nexus";

/* ============================================================================
   TEAM MEMBERS & INVITATIONS
   ============================================================================ */

export interface OrgMemberItem {
  member_id: string;
  user_id: string;
  email: string;
  full_name: string;
  role: "OWNER" | "ADMIN" | "OPERATOR" | "VIEWER";
  status: string;
  joined_at: string;
  last_login_at?: string;
}

interface TeamMembersViewProps {
  members: OrgMemberItem[];
  onInviteMember: (payload: {
    email: string;
    full_name: string;
    role: string;
  }) => Promise<void>;
  onUpdateRole: (memberId: string, role: string) => Promise<void>;
}

export function TeamMembersView({
  members,
  onInviteMember,
  onUpdateRole,
}: TeamMembersViewProps) {
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState("OPERATOR");

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !fullName.trim()) return;
    await onInviteMember({ email, full_name: fullName, role });
    setEmail("");
    setFullName("");
  };

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-[#F5F7FA]">
          Organization Team Members
        </h1>
        <p className="text-xs text-[#929BAA] mt-0.5">
          Manage workspace members and assign RBAC roles (OWNER, ADMIN,
          OPERATOR, VIEWER).
        </p>
      </div>

      <form
        onSubmit={handleInvite}
        className="p-4 rounded-md bg-[#151A22] border border-[#252B35] grid grid-cols-1 md:grid-cols-4 gap-3"
      >
        <input
          type="text"
          placeholder="Full Name"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          className="bg-[#11151B] border border-[#252B35] rounded px-3 py-2 text-xs text-[#F5F7FA]"
          required
        />
        <input
          type="email"
          placeholder="Work Email Address"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="bg-[#11151B] border border-[#252B35] rounded px-3 py-2 text-xs text-[#F5F7FA]"
          required
        />
        <select
          value={role}
          onChange={(e) => setRole(e.target.value)}
          className="bg-[#11151B] border border-[#252B35] rounded px-3 py-2 text-xs text-[#F5F7FA]"
        >
          <option value="OWNER">OWNER</option>
          <option value="ADMIN">ADMIN</option>
          <option value="OPERATOR">OPERATOR</option>
          <option value="VIEWER">VIEWER</option>
        </select>
        <button
          type="submit"
          className="px-4 py-2 rounded bg-[#8B7CFF] text-[#0B0D10] font-semibold text-xs flex items-center justify-center gap-1.5"
        >
          <UserPlus className="w-3.5 h-3.5" />
          Invite Member
        </button>
      </form>

      <div className="bg-[#151A22] border border-[#252B35] rounded-md overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-[#252B35] bg-[#11151B] text-[11px] font-semibold uppercase text-[#929BAA]">
              <th className="px-4 py-2.5">Name</th>
              <th className="px-4 py-2.5">Email</th>
              <th className="px-4 py-2.5">RBAC Role</th>
              <th className="px-4 py-2.5">Status</th>
              <th className="px-4 py-2.5">Joined</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#252B35]/60 text-xs">
            {members.map((m) => (
              <tr key={m.member_id} className="hover:bg-[#11151B]/50">
                <td className="px-4 py-3 font-medium text-[#F5F7FA]">
                  {m.full_name}
                </td>
                <td className="px-4 py-3 text-[#929BAA] font-mono">
                  {m.email}
                </td>
                <td className="px-4 py-3">
                  <select
                    value={m.role}
                    onChange={(e) => onUpdateRole(m.member_id, e.target.value)}
                    className="bg-[#11151B] border border-[#252B35] rounded px-2 py-1 text-xs font-mono text-[#8B7CFF]"
                  >
                    <option value="OWNER">OWNER</option>
                    <option value="ADMIN">ADMIN</option>
                    <option value="OPERATOR">OPERATOR</option>
                    <option value="VIEWER">VIEWER</option>
                  </select>
                </td>
                <td className="px-4 py-3">
                  <span className="px-2 py-0.5 text-[10px] font-mono uppercase rounded bg-[#36C98F]/15 text-[#36C98F]">
                    {m.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-[#929BAA] font-mono">
                  {new Date(m.joined_at).toLocaleDateString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ============================================================================
   PERMISSIONS MATRIX
   ============================================================================ */

interface PermissionsViewProps {
  roles: { id: string; name: string; description: string }[];
  permissions: {
    id: string;
    role_name: string;
    resource: string;
    action: string;
    allowed: boolean;
  }[];
}

export function PermissionsView({ roles, permissions }: PermissionsViewProps) {
  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-[#F5F7FA]">
          Role-Based Access Control (RBAC) & Permissions
        </h1>
        <p className="text-xs text-[#929BAA] mt-0.5">
          Enforced at the backend authorization and MCP client invocation layers.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-3.5">
        {roles.map((r) => (
          <div
            key={r.id}
            className="p-4 rounded-md bg-[#151A22] border border-[#252B35] space-y-1.5"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-semibold text-[#8B7CFF]">
                {r.name}
              </span>
              <KeyRound className="w-3.5 h-3.5 text-[#929BAA]" />
            </div>
            <p className="text-xs text-[#929BAA] leading-relaxed">
              {r.description}
            </p>
          </div>
        ))}
      </div>

      <div className="bg-[#151A22] border border-[#252B35] rounded-md overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-[#252B35] bg-[#11151B] text-[11px] font-semibold uppercase text-[#929BAA]">
              <th className="px-4 py-2.5">Role</th>
              <th className="px-4 py-2.5">Resource</th>
              <th className="px-4 py-2.5">Action</th>
              <th className="px-4 py-2.5">Enforcement Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#252B35]/60 text-xs">
            {permissions.map((p) => (
              <tr key={p.id}>
                <td className="px-4 py-2.5 font-mono text-[#8B7CFF]">
                  {p.role_name}
                </td>
                <td className="px-4 py-2.5 font-mono text-[#F5F7FA]">
                  {p.resource}
                </td>
                <td className="px-4 py-2.5 font-mono text-[#929BAA]">
                  {p.action}
                </td>
                <td className="px-4 py-2.5">
                  {p.allowed ? (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-[#36C98F]/15 text-[#36C98F]">
                      <CheckCircle2 className="w-3 h-3" /> ALLOWED
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-[#F06C75]/15 text-[#F06C75]">
                      <XCircle className="w-3 h-3" /> DENIED
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ============================================================================
   AUDIT LOGS
   ============================================================================ */

export interface AuditLogItem {
  id: string;
  actor_email: string;
  actor_role: string;
  action: string;
  resource_type: string;
  resource_id: string;
  status: string;
  ip_address?: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export function AuditLogsView({ logs }: { logs: AuditLogItem[] }) {
  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-[#F5F7FA]">
          Immutable Security & Operations Audit Logs
        </h1>
        <p className="text-xs text-[#929BAA] mt-0.5">
          Every login, MCP server registration, tool configuration change,
          workflow execution, and approval decision is recorded with automatic
          secret redaction.
        </p>
      </div>

      <div className="bg-[#151A22] border border-[#252B35] rounded-md overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-[#252B35] bg-[#11151B] text-[11px] font-semibold uppercase text-[#929BAA]">
              <th className="px-4 py-2.5">Timestamp (UTC)</th>
              <th className="px-4 py-2.5">Actor</th>
              <th className="px-4 py-2.5">Action</th>
              <th className="px-4 py-2.5">Resource</th>
              <th className="px-4 py-2.5">Metadata</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#252B35]/60 text-xs">
            {logs.map((l) => (
              <tr key={l.id} className="hover:bg-[#11151B]/50">
                <td className="px-4 py-2.5 font-mono text-[#929BAA] whitespace-nowrap">
                  {new Date(l.created_at).toLocaleString()}
                </td>
                <td className="px-4 py-2.5">
                  <span className="text-[#F5F7FA]">{l.actor_email}</span>{" "}
                  <span className="text-[10px] font-mono text-[#8B7CFF]">
                    ({l.actor_role})
                  </span>
                </td>
                <td className="px-4 py-2.5 font-mono text-[#36C98F]">
                  {l.action}
                </td>
                <td className="px-4 py-2.5 font-mono text-[#929BAA]">
                  {l.resource_type}
                </td>
                <td className="px-4 py-2.5 font-mono text-[11px] text-[#929BAA] max-w-md truncate">
                  {JSON.stringify(l.metadata)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ============================================================================
   ORGANIZATION & APPROVAL POLICY SETTINGS
   ============================================================================ */

interface SettingsViewProps {
  organization: OrganizationProfile | null;
  onSaveSettings: (payload: {
    name?: string;
    domain?: string;
    approval_policy?: Record<string, unknown>;
  }) => Promise<void>;
}

export function SettingsView({
  organization,
  onSaveSettings,
}: SettingsViewProps) {
  const [orgName, setOrgName] = useState(organization?.name || "");
  const [domain, setDomain] = useState(organization?.domain || "");
  const [highRiskGate, setHighRiskGate] = useState(
    organization?.approval_policy?.require_approval_for_high_risk ?? true
  );
  const [lowRiskGate, setLowRiskGate] = useState(
    organization?.approval_policy?.require_approval_for_low_risk ?? false
  );
  const [savedBanner, setSavedBanner] = useState(false);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSaveSettings({
      name: orgName,
      domain,
      approval_policy: {
        require_approval_for_high_risk: highRiskGate,
        require_approval_for_low_risk: lowRiskGate,
        allowed_approver_roles: ["OWNER", "ADMIN", "OPERATOR"],
        max_auto_tool_calls: 10,
      },
    });
    setSavedBanner(true);
    setTimeout(() => setSavedBanner(false), 2500);
  };

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-[#F5F7FA]">
          Organization & Governance Settings
        </h1>
        <p className="text-xs text-[#929BAA] mt-0.5">
          Configure workspace tenant metadata and backend-enforced Human
          Approval policies.
        </p>
      </div>

      <form
        onSubmit={handleSave}
        className="p-5 rounded-md bg-[#151A22] border border-[#252B35] space-y-5"
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-[#929BAA] mb-1">
              Organization Name
            </label>
            <input
              type="text"
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
              className="w-full bg-[#11151B] border border-[#252B35] rounded px-3 py-2 text-xs text-[#F5F7FA]"
            />
          </div>
          <div>
            <label className="block text-xs text-[#929BAA] mb-1">
              Verified Enterprise Domain
            </label>
            <input
              type="text"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              className="w-full bg-[#11151B] border border-[#252B35] rounded px-3 py-2 text-xs text-[#F5F7FA]"
            />
          </div>
        </div>

        <div className="pt-4 border-t border-[#252B35] space-y-3">
          <div className="text-xs font-semibold text-[#F5F7FA] flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-[#8B7CFF]" />
            Human Approval Engine Policy
          </div>
          <label className="flex items-center justify-between p-3 rounded bg-[#11151B] border border-[#252B35] cursor-pointer">
            <div>
              <div className="text-xs font-medium text-[#F5F7FA]">
                Require Explicit Approval for HIGH_RISK_WRITE Operations
              </div>
              <div className="text-[11px] text-[#929BAA]">
                Pauses candidate stage transitions, job creation, client invoice
                reminders, and manager notifications until approved.
              </div>
            </div>
            <input
              type="checkbox"
              checked={highRiskGate}
              onChange={(e) => setHighRiskGate(e.target.checked)}
              className="accent-[#8B7CFF] w-4 h-4"
            />
          </label>

          <label className="flex items-center justify-between p-3 rounded bg-[#11151B] border border-[#252B35] cursor-pointer">
            <div>
              <div className="text-xs font-medium text-[#F5F7FA]">
                Require Explicit Approval for LOW_RISK_WRITE Operations
              </div>
              <div className="text-[11px] text-[#929BAA]">
                Also require human sign-off before generating summary reports or
                draft records.
              </div>
            </div>
            <input
              type="checkbox"
              checked={lowRiskGate}
              onChange={(e) => setLowRiskGate(e.target.checked)}
              className="accent-[#8B7CFF] w-4 h-4"
            />
          </label>
        </div>

        <div className="flex items-center justify-between pt-2">
          {savedBanner ? (
            <span className="text-xs text-[#36C98F] font-mono">
              ✓ Governance settings saved and enforced at backend.
            </span>
          ) : (
            <span />
          )}
          <button
            type="submit"
            className="px-4 py-2 rounded bg-[#8B7CFF] text-[#0B0D10] font-semibold text-xs"
          >
            Save Policy Settings
          </button>
        </div>
      </form>
    </div>
  );
}

