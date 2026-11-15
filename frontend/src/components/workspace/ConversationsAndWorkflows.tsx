"use client";

import React, { useState } from "react";
import {
  MessageSquare,
  GitBranch,
  Play,
  Trash2,
  Plus,
  ArrowUpRight,
  ShieldAlert,
  CheckCircle2,
} from "lucide-react";
import { ConversationSummary, WorkflowTemplateItem } from "@/types/nexus";

interface ConversationsViewProps {
  conversations: ConversationSummary[];
  onOpenConversation: (id: string) => void;
  onDeleteConversation: (id: string) => Promise<void>;
}

export function ConversationsView({
  conversations,
  onOpenConversation,
  onDeleteConversation,
}: ConversationsViewProps) {
  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-[#F5F7FA]">
            Operational Conversations
          </h1>
          <p className="text-xs text-[#929BAA] mt-0.5">
            Auditable multi-turn command sessions and execution threads across
            your organization.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3">
        {conversations.length === 0 ? (
          <div className="p-8 rounded-md bg-[#151A22] border border-[#252B35] text-center text-sm text-[#929BAA]">
            No conversations recorded yet. Launch a prompt in the AI Command
            Center.
          </div>
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.id}
              className="p-4 rounded-md bg-[#151A22] border border-[#252B35] flex items-center justify-between hover:border-[#8B7CFF]/40 transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded bg-[#11151B] border border-[#252B35] flex items-center justify-center">
                  <MessageSquare className="w-4 h-4 text-[#8B7CFF]" />
                </div>
                <div>
                  <div className="text-sm font-medium text-[#F5F7FA]">
                    {conv.title}
                  </div>
                  <div className="text-xs text-[#929BAA] mt-0.5 font-mono">
                    {conv.message_count} messages • Updated{" "}
                    {new Date(conv.updated_at).toLocaleString()}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => onOpenConversation(conv.id)}
                  className="px-3 py-1.5 rounded text-xs font-medium bg-[#8B7CFF]/15 text-[#8B7CFF] border border-[#8B7CFF]/30 hover:bg-[#8B7CFF]/25 flex items-center gap-1"
                >
                  Open in Command Center
                  <ArrowUpRight className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => onDeleteConversation(conv.id)}
                  className="p-1.5 rounded text-[#929BAA] hover:text-[#F06C75] hover:bg-[#11151B]"
                  title="Delete conversation"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

interface WorkflowsViewProps {
  templates: WorkflowTemplateItem[];
  onRunTemplate: (templateId: string) => Promise<void>;
  onCreateTemplate: (payload: {
    name: string;
    description: string;
    category: string;
    prompt_template: string;
    steps_definition: string[];
    risk_level: string;
  }) => Promise<void>;
}

export function WorkflowsView({
  templates,
  onRunTemplate,
  onCreateTemplate,
}: WorkflowsViewProps) {
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [category, setCategory] = useState("Recruitment");
  const [description, setDescription] = useState("");
  const [promptTemplate, setPromptTemplate] = useState("");
  const [riskLevel, setRiskLevel] = useState("READ");
  const [runningId, setRunningId] = useState<string | null>(null);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !promptTemplate.trim()) return;
    await onCreateTemplate({
      name,
      description: description || "Automated LangGraph multi-step workflow",
      category,
      prompt_template: promptTemplate,
      steps_definition: [
        "Intent Detection",
        "MCP Tool Discovery",
        "Execute & Validate",
      ],
      risk_level: riskLevel,
    });
    setName("");
    setDescription("");
    setPromptTemplate("");
    setShowCreate(false);
  };

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-[#F5F7FA]">
            Agentic Workflow Templates
          </h1>
          <p className="text-xs text-[#929BAA] mt-0.5">
            Reusable multi-step LangGraph operational playbooks with checkpoint
            persistence and human approval gates.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="px-3.5 py-2 rounded-md bg-[#8B7CFF] text-[#0B0D10] font-semibold text-xs flex items-center gap-1.5"
        >
          <Plus className="w-4 h-4" />
          New Workflow Template
        </button>
      </div>

      {showCreate && (
        <form
          onSubmit={handleCreate}
          className="p-4 rounded-md bg-[#151A22] border border-[#252B35] space-y-3"
        >
          <div className="text-xs font-semibold text-[#F5F7FA]">
            Create Multi-Step Workflow Template
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <input
              type="text"
              placeholder="Workflow Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="bg-[#11151B] border border-[#252B35] rounded px-3 py-2 text-xs text-[#F5F7FA]"
              required
            />
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="bg-[#11151B] border border-[#252B35] rounded px-3 py-2 text-xs text-[#F5F7FA]"
            >
              <option value="Recruitment">Recruitment</option>
              <option value="HRMS">HRMS</option>
              <option value="Finance">Finance</option>
              <option value="Executive BI">Executive BI</option>
            </select>
            <select
              value={riskLevel}
              onChange={(e) => setRiskLevel(e.target.value)}
              className="bg-[#11151B] border border-[#252B35] rounded px-3 py-2 text-xs text-[#F5F7FA]"
            >
              <option value="READ">READ</option>
              <option value="LOW_RISK_WRITE">LOW_RISK_WRITE</option>
              <option value="HIGH_RISK_WRITE">HIGH_RISK_WRITE</option>
            </select>
          </div>
          <input
            type="text"
            placeholder="Short description of business impact..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full bg-[#11151B] border border-[#252B35] rounded px-3 py-2 text-xs text-[#F5F7FA]"
          />
          <textarea
            placeholder="Natural language operational instruction to execute via LangGraph..."
            value={promptTemplate}
            onChange={(e) => setPromptTemplate(e.target.value)}
            rows={2}
            className="w-full bg-[#11151B] border border-[#252B35] rounded px-3 py-2 text-xs text-[#F5F7FA]"
            required
          />
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setShowCreate(false)}
              className="px-3 py-1.5 rounded text-xs text-[#929BAA] bg-[#11151B] border border-[#252B35]"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-3.5 py-1.5 rounded text-xs font-semibold bg-[#36C98F] text-[#0B0D10]"
            >
              Save Template
            </button>
          </div>
        </form>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {templates.map((tpl) => (
          <div
            key={tpl.id}
            className="p-4 rounded-md bg-[#151A22] border border-[#252B35] flex flex-col justify-between space-y-4"
          >
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-[#8B7CFF]/15 text-[#8B7CFF] border border-[#8B7CFF]/30">
                  {tpl.category}
                </span>
                <span
                  className={`px-2 py-0.5 text-[10px] font-mono rounded flex items-center gap-1 ${
                    tpl.risk_level === "HIGH_RISK_WRITE"
                      ? "bg-[#E9AE54]/15 text-[#E9AE54]"
                      : "bg-[#36C98F]/15 text-[#36C98F]"
                  }`}
                >
                  {tpl.risk_level === "HIGH_RISK_WRITE" ? (
                    <ShieldAlert className="w-3 h-3" />
                  ) : (
                    <CheckCircle2 className="w-3 h-3" />
                  )}
                  {tpl.risk_level}
                </span>
              </div>
              <h3 className="text-sm font-semibold text-[#F5F7FA]">
                {tpl.name}
              </h3>
              <p className="text-xs text-[#929BAA]">{tpl.description}</p>
              <div className="p-2.5 rounded bg-[#11151B] border border-[#252B35] text-xs font-mono text-[#F5F7FA]">
                &ldquo;{tpl.prompt_template}&rdquo;
              </div>
              <div className="flex flex-wrap gap-1.5 pt-1">
                {tpl.steps_definition.map((st, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-0.5 rounded bg-[#11151B] border border-[#252B35] text-[10px] text-[#929BAA]"
                  >
                    {idx + 1}. {st}
                  </span>
                ))}
              </div>
            </div>

            <div className="pt-2 border-t border-[#252B35] flex items-center justify-between">
              <span className="text-[11px] font-mono text-[#929BAA]">
                Executed {tpl.run_count} times
              </span>
              <button
                disabled={runningId === tpl.id}
                onClick={async () => {
                  setRunningId(tpl.id);
                  try {
                    await onRunTemplate(tpl.id);
                  } finally {
                    setRunningId(null);
                  }
                }}
                className="px-3 py-1.5 rounded text-xs font-semibold bg-[#8B7CFF] text-[#0B0D10] hover:bg-[#8B7CFF]/90 flex items-center gap-1.5"
              >
                <Play className="w-3.5 h-3.5" />
                {runningId === tpl.id ? "Executing..." : "Run Workflow"}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

