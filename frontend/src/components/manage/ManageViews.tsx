"use client";

import React, { useState } from "react";
import {
  ShieldCheck,
  ShieldAlert,
  History,
  BarChart3,
  CheckCircle2,
  XCircle,
  Clock,
  Cpu,
  Wrench,
  Coins,
  Eye,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import {
  AnalyticsSummary,
  ApprovalRecord,
  ExecutionHistoryItem,
  UserProfile,
} from "@/types/nexus";
import { apiClient } from "@/lib/api";

/* ============================================================================
   MODULE F: HUMAN APPROVAL ENGINE QUEUE
   ============================================================================ */

interface ApprovalsViewProps {
  user: UserProfile | null;
  approvals: ApprovalRecord[];
  onDecideApproval: (
    approvalId: string,
    decision: "approve" | "reject",
    comment?: string
  ) => Promise<void>;
}

export function ApprovalsView({
  user,
  approvals,
  onDecideApproval,
}: ApprovalsViewProps) {
  const [filter, setFilter] = useState<string>("all");
  const [comments, setComments] = useState<Record<string, string>>({});
  const [busyId, setBusyId] = useState<string | null>(null);

  const canApprove =
    user && ["OWNER", "ADMIN", "OPERATOR"].includes(user.role);

  const filtered = approvals.filter((a) =>
    filter === "all" ? true : a.status === filter
  );

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-[#F5F7FA]">
            Human Approval Engine
          </h1>
          <p className="text-xs text-[#929BAA] mt-0.5">
            Backend-enforced governance gate for HIGH_RISK_WRITE operations
            before MCP tool execution.
          </p>
        </div>
        <div className="flex items-center gap-1.5 bg-[#151A22] p-1 rounded-md border border-[#252B35]">
          {["all", "pending", "approved", "rejected"].map((st) => (
            <button
              key={st}
              onClick={() => setFilter(st)}
              className={`px-2.5 py-1 rounded text-xs font-mono uppercase transition-colors ${
                filter === st
                  ? "bg-[#8B7CFF] text-[#0B0D10] font-semibold"
                  : "text-[#929BAA] hover:text-[#F5F7FA]"
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-4">
        {filtered.length === 0 ? (
          <div className="p-8 rounded-md bg-[#151A22] border border-[#252B35] text-center text-sm text-[#929BAA]">
            No approval requests match the selected filter.
          </div>
        ) : (
          filtered.map((ap) => (
            <div
              key={ap.id}
              className="p-5 rounded-md bg-[#151A22] border border-[#252B35] space-y-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  <ShieldAlert className="w-5 h-5 text-[#E9AE54] shrink-0 mt-0.5" />
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-semibold text-[#F5F7FA]">
                        {ap.title}
                      </h3>
                      <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-[#E9AE54]/20 text-[#E9AE54]">
                        {ap.risk_classification}
                      </span>
                    </div>
                    <p className="text-xs text-[#929BAA] mt-1">
                      {ap.description} • Server:{" "}
                      <span className="font-mono text-[#F5F7FA]">
                        {ap.server_name}
                      </span>{" "}
                      • Tool:{" "}
                      <span className="font-mono text-[#8B7CFF]">
                        {ap.tool_name}
                      </span>
                    </p>
                  </div>
                </div>
                <span
                  className={`px-2.5 py-0.5 text-[10px] font-mono uppercase rounded ${
                    ap.status === "approved"
                      ? "bg-[#36C98F]/20 text-[#36C98F]"
                      : ap.status === "rejected"
                      ? "bg-[#F06C75]/20 text-[#F06C75]"
                      : "bg-[#E9AE54]/20 text-[#E9AE54]"
                  }`}
                >
                  {ap.status}
                </span>
              </div>

              <div className="bg-[#0B0D10] border border-[#252B35] rounded p-3">
                <div className="text-[10px] font-mono uppercase text-[#929BAA] mb-1">
                  Proposed Operation Payload
                </div>
                <pre className="text-xs font-mono text-[#F5F7FA] overflow-x-auto whitespace-pre-wrap">
                  {JSON.stringify(ap.proposed_arguments, null, 2)}
                </pre>
              </div>

              {ap.execution_result && (
                <div className="bg-[#0B0D10] border border-[#36C98F]/40 rounded p-3">
                  <div className="text-[10px] font-mono uppercase text-[#36C98F] mb-1">
                    Verified MCP Execution Output
                  </div>
                  <pre className="text-xs font-mono text-[#36C98F] overflow-x-auto whitespace-pre-wrap">
                    {JSON.stringify(ap.execution_result, null, 2)}
                  </pre>
                </div>
              )}

              {ap.status === "pending" && (
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-2 border-t border-[#252B35]">
                  <input
                    type="text"
                    placeholder="Optional audit note / reviewer comment..."
                    value={comments[ap.id] || ""}
                    onChange={(e) =>
                      setComments({ ...comments, [ap.id]: e.target.value })
                    }
                    className="flex-1 bg-[#11151B] border border-[#252B35] rounded px-3 py-1.5 text-xs text-[#F5F7FA]"
                  />
                  <div className="flex items-center gap-2">
                    <button
                      disabled={!canApprove || busyId === ap.id}
                      onClick={async () => {
                        setBusyId(ap.id);
                        try {
                          await onDecideApproval(
                            ap.id,
                            "reject",
                            comments[ap.id] || "Rejected by reviewer"
                          );
                        } finally {
                          setBusyId(null);
                        }
                      }}
                      className="px-3 py-1.5 rounded text-xs bg-[#11151B] text-[#F06C75] border border-[#F06C75]/40 disabled:opacity-40"
                    >
                      Reject Operation
                    </button>
                    <button
                      disabled={!canApprove || busyId === ap.id}
                      onClick={async () => {
                        setBusyId(ap.id);
                        try {
                          await onDecideApproval(
                            ap.id,
                            "approve",
                            comments[ap.id] || "Approved by reviewer"
                          );
                        } finally {
                          setBusyId(null);
                        }
                      }}
                      className="px-4 py-1.5 rounded text-xs font-semibold bg-[#36C98F] text-[#0B0D10] disabled:opacity-40"
                    >
                      Approve & Execute MCP Tool
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

/* ============================================================================
   MODULE G (PART 1): EXECUTION HISTORY & TRACE INSPECTOR
   ============================================================================ */

interface ExecutionHistoryViewProps {
  executions: ExecutionHistoryItem[];
}

export function ExecutionHistoryView({
  executions,
}: ExecutionHistoryViewProps) {
  const [statusFilter, setStatusFilter] = useState("all");
  const [selectedTrace, setSelectedTrace] = useState<Record<
    string,
    unknown
  > | null>(null);
  const [loadingTrace, setLoadingTrace] = useState(false);

  const filtered = executions.filter((ex) =>
    statusFilter === "all" ? true : ex.status === statusFilter
  );

  const handleInspect = async (execId: string) => {
    setLoadingTrace(true);
    try {
      const traceData = await apiClient.request<Record<string, unknown>>(
        `/executions/${execId}`
      );
      setSelectedTrace(traceData);
    } finally {
      setLoadingTrace(false);
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-[#F5F7FA]">
            Auditable Execution History
          </h1>
          <p className="text-xs text-[#929BAA] mt-0.5">
            Complete trace of every user request, LangGraph plan, MCP tool
            invocation, and redacted output.
          </p>
        </div>
        <div className="flex items-center gap-1.5 bg-[#151A22] p-1 rounded-md border border-[#252B35]">
          {["all", "completed", "awaiting_approval", "failed"].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-2.5 py-1 rounded text-xs font-mono uppercase ${
                statusFilter === st
                  ? "bg-[#8B7CFF] text-[#0B0D10] font-semibold"
                  : "text-[#929BAA] hover:text-[#F5F7FA]"
              }`}
            >
              {st.replace("_", " ")}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-3">
          {filtered.map((ex) => (
            <div
              key={ex.id}
              onClick={() => handleInspect(ex.id)}
              className="p-4 rounded-md bg-[#151A22] border border-[#252B35] hover:border-[#8B7CFF]/50 cursor-pointer space-y-2 transition-colors"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="text-sm font-medium text-[#F5F7FA]">
                  &ldquo;{ex.user_prompt}&rdquo;
                </div>
                <span
                  className={`px-2 py-0.5 text-[10px] font-mono uppercase rounded shrink-0 ${
                    ex.status === "completed"
                      ? "bg-[#36C98F]/15 text-[#36C98F]"
                      : ex.status === "awaiting_approval"
                      ? "bg-[#E9AE54]/20 text-[#E9AE54]"
                      : "bg-[#F06C75]/20 text-[#F06C75]"
                  }`}
                >
                  {ex.status}
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-4 text-[11px] font-mono text-[#929BAA]">
                <span>Intent: {ex.intent}</span>
                <span>Duration: {ex.duration_ms}ms</span>
                <span>Steps: {ex.steps_count}</span>
                <span>
                  Tokens: {ex.prompt_tokens + ex.completion_tokens} ($
                  {ex.estimated_cost_usd})
                </span>
              </div>
              {ex.tools_invoked.length > 0 && (
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {ex.tools_invoked.map((t, i) => (
                    <span
                      key={i}
                      className="px-2 py-0.5 rounded bg-[#11151B] border border-[#252B35] text-[10px] font-mono text-[#8B7CFF]"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="bg-[#151A22] border border-[#252B35] rounded-md p-4 h-fit sticky top-6">
          <div className="text-xs font-mono uppercase text-[#8B7CFF] mb-2 flex items-center gap-1.5">
            <Eye className="w-3.5 h-3.5" /> Execution Trace Inspector
          </div>
          {loadingTrace ? (
            <div className="text-xs text-[#929BAA] py-8 text-center">
              Loading redacted execution trace...
            </div>
          ) : selectedTrace ? (
            <pre className="p-2.5 rounded bg-[#0B0D10] border border-[#252B35] text-[11px] font-mono text-[#F5F7FA] overflow-x-auto max-h-[520px]">
              {JSON.stringify(selectedTrace, null, 2)}
            </pre>
          ) : (
            <div className="text-xs text-[#929BAA] py-8 text-center">
              Click any execution on the left to inspect its full LangGraph
              steps, MCP tool payloads, and approval records.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ============================================================================
   MODULE G (PART 2): ANALYTICS DASHBOARD
   ============================================================================ */

interface AnalyticsViewProps {
  summary: AnalyticsSummary | null;
}

export function AnalyticsView({ summary }: AnalyticsViewProps) {
  if (!summary) {
    return (
      <div className="p-6 text-xs text-[#929BAA]">
        Loading real-time platform analytics...
      </div>
    );
  }

  const statCards = [
    {
      label: "Total AI Tasks Executed",
      value: summary.total_ai_tasks_executed,
      icon: Cpu,
      color: "text-[#8B7CFF]",
    },
    {
      label: "Successful Executions",
      value: summary.successful_executions,
      icon: CheckCircle2,
      color: "text-[#36C98F]",
    },
    {
      label: "Failed / Blocked Executions",
      value: summary.failed_executions,
      icon: XCircle,
      color: "text-[#F06C75]",
    },
    {
      label: "Avg Execution Duration",
      value: `${summary.average_execution_duration_ms} ms`,
      icon: Clock,
      color: "text-[#F5F7FA]",
    },
    {
      label: "MCP Tool Invocations",
      value: summary.mcp_tool_invocation_count,
      icon: Wrench,
      color: "text-[#8B7CFF]",
    },
    {
      label: "Pending Human Approvals",
      value: summary.pending_approvals,
      icon: ShieldCheck,
      color: "text-[#E9AE54]",
    },
    {
      label: "Total Token Consumption",
      value: summary.token_consumption.toLocaleString(),
      icon: BarChart3,
      color: "text-[#F5F7FA]",
    },
    {
      label: "Estimated AI Usage Cost",
      value: `$${summary.estimated_ai_usage_cost_usd.toFixed(5)}`,
      icon: Coins,
      color: "text-[#36C98F]",
    },
  ];

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-[#F5F7FA]">
          Operations & MCP Telemetry Analytics
        </h1>
        <p className="text-xs text-[#929BAA] mt-0.5">
          Real-time metrics computed directly from database execution traces,
          MCP tool counters, and token usage records.
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5">
        {statCards.map((card, idx) => {
          const Icon = card.icon;
          return (
            <div
              key={idx}
              className="p-4 rounded-md bg-[#151A22] border border-[#252B35] space-y-1.5"
            >
              <div className="flex items-center justify-between text-xs text-[#929BAA]">
                <span>{card.label}</span>
                <Icon className={`w-4 h-4 ${card.color}`} />
              </div>
              <div className="text-xl font-semibold font-mono text-[#F5F7FA]">
                {card.value}
              </div>
            </div>
          );
        })}
      </div>

      <div className="bg-[#151A22] border border-[#252B35] rounded-md p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-[#F5F7FA]">
            Most Frequently Invoked MCP Tools
          </h3>
          <span className="text-xs font-mono text-[#929BAA]">
            Connected MCP Servers: {summary.connected_mcp_servers} •
            Integrations: {summary.connected_integrations}
          </span>
        </div>
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={summary.most_frequently_used_tools}>
              <CartesianGrid strokeDasharray="3 3" stroke="#252B35" />
              <XAxis
                dataKey="tool_name"
                stroke="#929BAA"
                fontSize={11}
                tickLine={false}
              />
              <YAxis stroke="#929BAA" fontSize={11} tickLine={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#11151B",
                  borderColor: "#252B35",
                  color: "#F5F7FA",
                  fontSize: "12px",
                }}
              />
              <Bar
                dataKey="invocations"
                fill="#8B7CFF"
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

