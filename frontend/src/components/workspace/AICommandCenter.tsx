"use client";

import React, { useState } from "react";
import {
  Send,
  Plus,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ShieldAlert,
  Wrench,
  Server,
  Download,
  Sparkles,
  ChevronRight,
  XCircle,
  Loader2,
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
  CommandExecutionResult,
  ConversationMessage,
  ConversationSummary,
  MCPServerItem,
  PendingApprovalCard,
  UserProfile,
} from "@/types/nexus";

interface AICommandCenterProps {
  user: UserProfile | null;
  servers: MCPServerItem[];
  conversations: ConversationSummary[];
  activeConversationId: string | null;
  messages: ConversationMessage[];
  isExecuting: boolean;
  onExecutePrompt: (prompt: string) => Promise<void>;
  onSelectConversation: (id: string) => Promise<void>;
  onNewConversation: () => void;
  onDecideApproval: (
    approvalId: string,
    decision: "approve" | "reject",
    comment?: string
  ) => Promise<void>;
}

const SUGGESTED_PROMPTS = [
  {
    category: "MVP Criterion 1 • Recruitment MCP",
    prompt:
      "Show me all candidates who have been waiting for an interview for more than seven days.",
  },
  {
    category: "MVP Criterion 2 • High-Risk Write Approval",
    prompt: "Move all these candidates to the shortlisted stage.",
  },
  {
    category: "Recruitment • Follow-up Audit",
    prompt:
      "Show me all pending job applications and identify candidates who haven't been contacted in seven days.",
  },
  {
    category: "HRMS • Compliance & Escalation",
    prompt:
      "Find employees whose documents are expiring next month and prepare notifications for their managers.",
  },
  {
    category: "Analytics • Executive BI",
    prompt: "Generate this month's recruitment performance report.",
  },
  {
    category: "Finance • Receivables & Reminders",
    prompt:
      "Identify all unpaid invoices and send reminders to the respective clients.",
  },
  {
    category: "Recruitment • Job Creation",
    prompt:
      "Create a new job opening for a Senior Backend Developer with a salary range of ₹12–18 LPA.",
  },
  {
    category: "Finance & Analytics • Variance Analysis",
    prompt:
      "Compare this month's expenses with last month and explain the major differences.",
  },
];

export function AICommandCenter({
  user,
  servers,
  conversations,
  activeConversationId,
  messages,
  isExecuting,
  onExecutePrompt,
  onSelectConversation,
  onNewConversation,
  onDecideApproval,
}: AICommandCenterProps) {
  const [inputPrompt, setInputPrompt] = useState("");
  const [decidingApprovalId, setDecidingApprovalId] = useState<string | null>(
    null
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputPrompt.trim() || isExecuting) return;
    const text = inputPrompt.trim();
    setInputPrompt("");
    await onExecutePrompt(text);
  };

  const handleExportCsv = (
    columns: string[],
    rows: Record<string, unknown>[]
  ) => {
    if (!columns.length || !rows.length) return;
    const header = columns.join(",");
    const csvRows = rows.map((row) =>
      columns
        .map((col) => `"${String(row[col] ?? "").replace(/"/g, '""')}"`)
        .join(",")
    );
    const csvContent = "data:text/csv;charset=utf-8," + [header, ...csvRows].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `nexus-export-${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const renderStructuredResult = (data: CommandExecutionResult) => {
    const steps = data.steps || [];
    const toolOutputs = data.tool_outputs || [];
    const approvals = data.pending_approvals || [];
    const columns = data.table_columns || [];
    const rows = data.table_rows || [];
    const chartData = data.chart_data || [];
    const kpiCards = data.kpi_cards || [];

    return (
      <div className="mt-3 space-y-4">
        {/* 1. Multi-Step LangGraph Execution Progress */}
        {steps.length > 0 && (
          <div className="bg-[#11151B] border border-[#252B35] rounded-md p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-mono uppercase tracking-wider text-[#929BAA] flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-[#8B7CFF]" />
                LangGraph Execution Pipeline ({steps.length} steps)
              </span>
              {data.duration_ms !== undefined && (
                <span className="text-[11px] font-mono text-[#929BAA]">
                  {data.duration_ms} ms
                </span>
              )}
            </div>
            <div className="space-y-1.5">
              {steps.map((step, idx) => (
                <div
                  key={`${step.step_number}-${idx}`}
                  className="flex items-center justify-between text-xs py-1 px-2 rounded bg-[#151A22]/70 border border-[#252B35]/60"
                >
                  <div className="flex items-center gap-2">
                    {step.status === "completed" && (
                      <CheckCircle2 className="w-3.5 h-3.5 text-[#36C98F] shrink-0" />
                    )}
                    {step.status === "awaiting_approval" && (
                      <AlertTriangle className="w-3.5 h-3.5 text-[#E9AE54] shrink-0" />
                    )}
                    {step.status === "failed" && (
                      <XCircle className="w-3.5 h-3.5 text-[#F06C75] shrink-0" />
                    )}
                    <span className="font-mono text-[11px] text-[#929BAA]">
                      Step {step.step_number}:
                    </span>
                    <span className="text-[#F5F7FA]">{step.title}</span>
                  </div>
                  {step.duration_ms !== undefined && (
                    <span className="text-[10px] font-mono text-[#929BAA]">
                      {step.duration_ms}ms
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 2. MCP Tool Invocation Badges */}
        {toolOutputs.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {toolOutputs.map((t, i) => (
              <div
                key={`${t.tool_name}-${i}`}
                className="inline-flex items-center gap-2 px-2.5 py-1 rounded bg-[#151A22] border border-[#252B35] text-xs"
              >
                <Wrench className="w-3.5 h-3.5 text-[#8B7CFF]" />
                <span className="font-mono text-[#F5F7FA]">{t.tool_name}</span>
                <span className="text-[#929BAA]">•</span>
                <span className="text-[11px] text-[#929BAA]">
                  {t.server_name}
                </span>
                <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-[#36C98F]/15 text-[#36C98F]">
                  {t.duration_ms}ms
                </span>
              </div>
            ))}
          </div>
        )}

        {/* 3. KPI Summary Cards */}
        {kpiCards.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
            {kpiCards.map((kpi, idx) => (
              <div
                key={idx}
                className="p-3 rounded-md bg-[#11151B] border border-[#252B35]"
              >
                <div className="text-[11px] text-[#929BAA]">{kpi.label}</div>
                <div className="text-lg font-semibold font-mono text-[#F5F7FA] mt-0.5">
                  {kpi.value}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* 4. Human Approval Cards (Backend-Enforced Write Gate) */}
        {approvals.length > 0 && (
          <div className="space-y-3">
            {approvals.map((ap: PendingApprovalCard) => {
              const isPending = ap.status === "pending";
              const canApprove =
                user && ["OWNER", "ADMIN", "OPERATOR"].includes(user.role);
              return (
                <div
                  key={ap.approval_id}
                  className="p-4 rounded-md bg-[#11151B] border border-[#E9AE54]/60 space-y-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <ShieldAlert className="w-5 h-5 text-[#E9AE54] shrink-0" />
                      <div>
                        <div className="text-sm font-semibold text-[#F5F7FA] flex items-center gap-2">
                          {ap.title}
                          <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-[#E9AE54]/20 text-[#E9AE54] border border-[#E9AE54]/40">
                            {ap.risk_classification}
                          </span>
                        </div>
                        <div className="text-xs text-[#929BAA] mt-0.5">
                          {ap.description} • Target Server:{" "}
                          <span className="text-[#F5F7FA] font-mono">
                            {ap.server_name}
                          </span>
                        </div>
                      </div>
                    </div>
                    <span
                      className={`px-2 py-0.5 text-[10px] font-mono uppercase rounded ${
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

                  <div className="bg-[#0B0D10] border border-[#252B35] rounded p-2.5">
                    <div className="text-[10px] font-mono uppercase text-[#929BAA] mb-1">
                      Proposed MCP Tool Parameters (`{ap.tool_name}`)
                    </div>
                    <pre className="text-[11px] font-mono text-[#F5F7FA] overflow-x-auto whitespace-pre-wrap">
                      {JSON.stringify(ap.proposed_arguments, null, 2)}
                    </pre>
                  </div>

                  {isPending && (
                    <div className="flex items-center justify-between pt-1">
                      <span className="text-[11px] text-[#929BAA]">
                        {canApprove
                          ? `Authorized as ${user?.role} to approve this operation.`
                          : `Role ${user?.role} has read-only access and cannot approve high-risk writes.`}
                      </span>
                      <div className="flex items-center gap-2">
                        <button
                          disabled={
                            !canApprove ||
                            decidingApprovalId === ap.approval_id
                          }
                          onClick={async () => {
                            setDecidingApprovalId(ap.approval_id);
                            try {
                              await onDecideApproval(
                                ap.approval_id,
                                "reject",
                                "Rejected from AI Command Center"
                              );
                            } finally {
                              setDecidingApprovalId(null);
                            }
                          }}
                          className="px-3 py-1.5 rounded text-xs font-medium bg-[#151A22] text-[#F06C75] border border-[#F06C75]/40 hover:bg-[#F06C75]/10 disabled:opacity-40 transition-colors"
                        >
                          Reject
                        </button>
                        <button
                          disabled={
                            !canApprove ||
                            decidingApprovalId === ap.approval_id
                          }
                          onClick={async () => {
                            setDecidingApprovalId(ap.approval_id);
                            try {
                              await onDecideApproval(
                                ap.approval_id,
                                "approve",
                                "Approved from AI Command Center"
                              );
                            } finally {
                              setDecidingApprovalId(null);
                            }
                          }}
                          className="px-3.5 py-1.5 rounded text-xs font-semibold bg-[#36C98F] text-[#0B0D10] hover:bg-[#36C98F]/90 disabled:opacity-40 transition-colors flex items-center gap-1.5"
                        >
                          {decidingApprovalId === ap.approval_id ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <CheckCircle2 className="w-3.5 h-3.5" />
                          )}
                          Approve & Execute via MCP
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* 5. Recharts Analytics Chart (When Returned) */}
        {chartData.length > 0 && (
          <div className="bg-[#11151B] border border-[#252B35] rounded-md p-4">
            <div className="text-xs font-semibold text-[#F5F7FA] mb-3">
              Operational Analytics Visualization
            </div>
            <div className="h-56 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#252B35" />
                  <XAxis
                    dataKey="name"
                    stroke="#929BAA"
                    fontSize={11}
                    tickLine={false}
                  />
                  <YAxis stroke="#929BAA" fontSize={11} tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#151A22",
                      borderColor: "#252B35",
                      color: "#F5F7FA",
                      fontSize: "12px",
                    }}
                  />
                  {"Previous" in (chartData[0] || {}) ? (
                    <>
                      <Bar
                        dataKey="Previous"
                        fill="#929BAA"
                        radius={[3, 3, 0, 0]}
                      />
                      <Bar
                        dataKey="Current"
                        fill="#8B7CFF"
                        radius={[3, 3, 0, 0]}
                      />
                    </>
                  ) : (
                    <Bar
                      dataKey="value"
                      fill="#8B7CFF"
                      radius={[3, 3, 0, 0]}
                    />
                  )}
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* 6. Structured Enterprise Data Table */}
        {columns.length > 0 && rows.length > 0 && (
          <div className="bg-[#11151B] border border-[#252B35] rounded-md overflow-hidden">
            <div className="px-3.5 py-2 border-b border-[#252B35] flex items-center justify-between">
              <span className="text-xs font-medium text-[#F5F7FA]">
                Retrieved Records ({rows.length})
              </span>
              <button
                onClick={() => handleExportCsv(columns, rows)}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] bg-[#151A22] text-[#929BAA] hover:text-[#F5F7FA] border border-[#252B35] transition-colors"
              >
                <Download className="w-3 h-3" />
                Export CSV
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-[#252B35] bg-[#151A22]/60">
                    {columns.map((col) => (
                      <th
                        key={col}
                        className="px-3.5 py-2 text-[11px] font-semibold uppercase tracking-wider text-[#929BAA]"
                      >
                        {col.replace(/_/g, " ")}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#252B35]/60 text-xs">
                  {rows.map((row, rIdx) => (
                    <tr
                      key={rIdx}
                      className="hover:bg-[#151A22]/50 transition-colors"
                    >
                      {columns.map((col) => {
                        const rawVal = row[col];
                        const valStr =
                          typeof rawVal === "number" && col.includes("inr")
                            ? `₹${rawVal.toLocaleString()}`
                            : String(rawVal ?? "—");
                        const isStatusBadge =
                          col === "stage" ||
                          col === "status" ||
                          col === "new_stage" ||
                          col === "interview_status";
                        return (
                          <td
                            key={col}
                            className="px-3.5 py-2.5 text-[#F5F7FA] whitespace-nowrap"
                          >
                            {isStatusBadge ? (
                              <span
                                className={`px-2 py-0.5 text-[11px] font-mono rounded ${
                                  valStr.includes("shortlisted") ||
                                  valStr.includes("passed") ||
                                  valStr.includes("paid") ||
                                  valStr.includes("dispatched") ||
                                  valStr.includes("open")
                                    ? "bg-[#36C98F]/15 text-[#36C98F] border border-[#36C98F]/30"
                                    : valStr.includes("overdue") ||
                                      valStr.includes("missing")
                                    ? "bg-[#F06C75]/15 text-[#F06C75] border border-[#F06C75]/30"
                                    : "bg-[#8B7CFF]/15 text-[#8B7CFF] border border-[#8B7CFF]/30"
                                }`}
                              >
                                {valStr}
                              </span>
                            ) : (
                              valStr
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="flex h-full overflow-hidden">
      {/* Main Conversational Command Workspace */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Connected MCP Systems Status Header */}
        <div className="h-14 px-6 border-b border-[#252B35] bg-[#11151B]/80 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <h1 className="text-sm font-semibold text-[#F5F7FA]">
              AI Command Center
            </h1>
            <span className="text-xs text-[#929BAA] hidden sm:inline">
              • Multi-Domain MCP Operations Layer
            </span>
          </div>
          <div className="flex items-center gap-2 overflow-x-auto">
            {servers.map((srv) => (
              <div
                key={srv.id}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#151A22] border border-[#252B35] text-[11px] shrink-0"
              >
                <span
                  className={`w-2 h-2 rounded-full ${
                    srv.status === "connected"
                      ? "bg-[#36C98F]"
                      : "bg-[#F06C75]"
                  }`}
                />
                <span className="text-[#F5F7FA] font-medium">{srv.name}</span>
                <span className="text-[#929BAA] font-mono">
                  ({srv.tools_count})
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Workspace Stream / Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 ? (
            <div className="max-w-4xl mx-auto space-y-6 py-4">
              <div className="space-y-2">
                <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded bg-[#8B7CFF]/15 border border-[#8B7CFF]/30 text-[#8B7CFF] text-xs font-mono">
                  MODEL CONTEXT PROTOCOL (MCP) • LANGGRAPH ORCHESTRATOR
                </div>
                <h2 className="text-2xl font-semibold text-[#F5F7FA] tracking-tight">
                  Stop clicking through dashboards. Describe the operation.
                </h2>
                <p className="text-sm text-[#929BAA] max-w-2xl">
                  NEXUS dynamically discovers tools across your connected
                  Recruitment, HRMS, Finance, and Analytics MCP servers, executes
                  read queries against real database records, and enforces human
                  approval before high-risk writes.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {SUGGESTED_PROMPTS.map((item, idx) => (
                  <button
                    key={idx}
                    onClick={() => onExecutePrompt(item.prompt)}
                    disabled={isExecuting}
                    className="text-left p-3.5 rounded-md bg-[#151A22] border border-[#252B35] hover:border-[#8B7CFF]/60 transition-all group"
                  >
                    <div className="flex items-center justify-between text-[11px] font-mono text-[#8B7CFF] mb-1">
                      <span>{item.category}</span>
                      <ChevronRight className="w-3.5 h-3.5 opacity-60 group-hover:translate-x-0.5 transition-transform" />
                    </div>
                    <div className="text-xs text-[#F5F7FA] leading-relaxed">
                      &ldquo;{item.prompt}&rdquo;
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="max-w-5xl mx-auto space-y-5">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`p-4 rounded-md border ${
                    msg.role === "user"
                      ? "bg-[#11151B] border-[#252B35]"
                      : "bg-[#151A22] border-[#252B35]"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[11px] font-mono uppercase tracking-wider text-[#929BAA]">
                      {msg.role === "user"
                        ? `${user?.full_name || "Operator"} (${user?.role})`
                        : "NEXUS Operations Engine"}
                    </span>
                    <span className="text-[11px] font-mono text-[#929BAA]">
                      {new Date(msg.created_at).toLocaleTimeString()}
                    </span>
                  </div>
                  <div className="text-sm text-[#F5F7FA] whitespace-pre-wrap leading-relaxed">
                    {msg.content}
                  </div>
                  {msg.structured_data &&
                    renderStructuredResult(msg.structured_data)}
                </div>
              ))}

              {isExecuting && (
                <div className="p-4 rounded-md bg-[#151A22] border border-[#8B7CFF]/40 flex items-center gap-3">
                  <Loader2 className="w-4 h-4 text-[#8B7CFF] animate-spin" />
                  <span className="text-xs font-mono text-[#F5F7FA]">
                    Discovering MCP tools, planning workflow, and querying
                    connected domain servers...
                  </span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Bottom Command Input Bar */}
        <div className="p-4 border-t border-[#252B35] bg-[#11151B]">
          <form
            onSubmit={handleSubmit}
            className="max-w-5xl mx-auto flex items-center gap-2.5"
          >
            <button
              type="button"
              onClick={onNewConversation}
              title="Start New Session"
              className="p-2.5 rounded-md bg-[#151A22] text-[#929BAA] hover:text-[#F5F7FA] border border-[#252B35] transition-colors shrink-0"
            >
              <Plus className="w-4 h-4" />
            </button>
            <input
              type="text"
              value={inputPrompt}
              onChange={(e) => setInputPrompt(e.target.value)}
              placeholder="Instruct NEXUS across Recruitment, HRMS, Finance, or Analytics (e.g., 'Show me all candidates waiting > 7 days')..."
              className="flex-1 bg-[#151A22] border border-[#252B35] focus:border-[#8B7CFF] rounded-md px-4 py-2.5 text-sm text-[#F5F7FA] placeholder-[#929BAA] outline-none transition-colors"
            />
            <button
              type="submit"
              disabled={isExecuting || !inputPrompt.trim()}
              className="px-4 py-2.5 rounded-md bg-[#8B7CFF] hover:bg-[#8B7CFF]/90 disabled:opacity-40 text-[#0B0D10] font-semibold text-xs flex items-center gap-1.5 transition-colors shrink-0"
            >
              <Send className="w-3.5 h-3.5" />
              Execute
            </button>
          </form>
        </div>
      </div>

      {/* Right Session History Sidebar */}
      <div className="w-64 border-l border-[#252B35] bg-[#11151B] hidden xl:flex flex-col shrink-0">
        <div className="h-14 px-4 border-b border-[#252B35] flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-[#929BAA]">
            Operations Sessions
          </span>
          <button
            onClick={onNewConversation}
            className="text-xs text-[#8B7CFF] hover:underline flex items-center gap-1"
          >
            <Plus className="w-3.5 h-3.5" /> New
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {conversations.length === 0 ? (
            <div className="p-3 text-xs text-[#929BAA]">
              No active sessions yet. Execute a command to start.
            </div>
          ) : (
            conversations.map((conv) => (
              <button
                key={conv.id}
                onClick={() => onSelectConversation(conv.id)}
                className={`w-full text-left p-2.5 rounded-md border text-xs transition-colors ${
                  activeConversationId === conv.id
                    ? "bg-[#151A22] border-[#8B7CFF]/50 text-[#F5F7FA]"
                    : "bg-transparent border-transparent text-[#929BAA] hover:bg-[#151A22]/60 hover:text-[#F5F7FA]"
                }`}
              >
                <div className="font-medium truncate">{conv.title}</div>
                <div className="text-[10px] text-[#929BAA] mt-0.5 flex items-center justify-between">
                  <span>{conv.message_count} messages</span>
                  <span>{new Date(conv.updated_at).toLocaleDateString()}</span>
                </div>
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

