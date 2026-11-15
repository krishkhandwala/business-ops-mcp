"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { AICommandCenter } from "@/components/workspace/AICommandCenter";
import {
  ConversationsView,
  WorkflowsView,
} from "@/components/workspace/ConversationsAndWorkflows";
import {
  IntegrationsView,
  MCPServersView,
  ToolRegistryView,
} from "@/components/connect/ConnectViews";
import {
  AnalyticsView,
  ApprovalsView,
  ExecutionHistoryView,
} from "@/components/manage/ManageViews";
import {
  AuditLogItem,
  AuditLogsView,
  OrgMemberItem,
  PermissionsView,
  SettingsView,
  TeamMembersView,
} from "@/components/organization/OrganizationViews";
import { apiClient } from "@/lib/api";
import {
  AnalyticsSummary,
  ApprovalRecord,
  CommandExecutionResult,
  ConversationMessage,
  ConversationSummary,
  ExecutionHistoryItem,
  IntegrationItem,
  MCPServerItem,
  MCPToolItem,
  NavigationTab,
  OrganizationProfile,
  UserProfile,
  WorkflowTemplateItem,
} from "@/types/nexus";

export default function NexusAppShell() {
  const [activeTab, setActiveTab] = useState<NavigationTab>("command-center");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const [user, setUser] = useState<UserProfile | null>(null);
  const [organization, setOrganization] = useState<OrganizationProfile | null>(
    null
  );
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  // Domain States
  const [servers, setServers] = useState<MCPServerItem[]>([]);
  const [tools, setTools] = useState<MCPToolItem[]>([]);
  const [integrations, setIntegrations] = useState<IntegrationItem[]>([]);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<
    string | null
  >(null);
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [isExecuting, setIsExecuting] = useState(false);

  const [templates, setTemplates] = useState<WorkflowTemplateItem[]>([]);
  const [approvals, setApprovals] = useState<ApprovalRecord[]>([]);
  const [executions, setExecutions] = useState<ExecutionHistoryItem[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [members, setMembers] = useState<OrgMemberItem[]>([]);
  const [roles, setRoles] = useState<
    { id: string; name: string; description: string }[]
  >([]);
  const [permissions, setPermissions] = useState<
    {
      id: string;
      role_name: string;
      resource: string;
      action: string;
      allowed: boolean;
    }[]
  >([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([]);

  const loadWorkspaceData = useCallback(async () => {
    try {
      const [
        srvRes,
        toolsRes,
        integRes,
        convRes,
        tplRes,
        apprRes,
        execRes,
        anaRes,
        memRes,
        permRes,
        audRes,
      ] = await Promise.all([
        apiClient.request<{ servers: MCPServerItem[] }>("/mcp/servers"),
        apiClient.request<{ tools: MCPToolItem[] }>("/mcp/tools"),
        apiClient.request<{ integrations: IntegrationItem[] }>("/integrations"),
        apiClient.request<{ conversations: ConversationSummary[] }>(
          "/conversations"
        ),
        apiClient.request<{ templates: WorkflowTemplateItem[] }>(
          "/workflows/templates"
        ),
        apiClient.request<{ approvals: ApprovalRecord[] }>("/approvals"),
        apiClient.request<{ executions: ExecutionHistoryItem[] }>(
          "/executions"
        ),
        apiClient.request<AnalyticsSummary>("/analytics/summary"),
        apiClient.request<{ members: OrgMemberItem[] }>(
          "/organization/members"
        ),
        apiClient.request<{
          roles: { id: string; name: string; description: string }[];
          permissions: {
            id: string;
            role_name: string;
            resource: string;
            action: string;
            allowed: boolean;
          }[];
        }>("/organization/permissions"),
        apiClient.request<{ audit_logs: AuditLogItem[] }>(
          "/organization/audit-logs"
        ),
      ]);

      setServers(srvRes.servers);
      setTools(toolsRes.tools);
      setIntegrations(integRes.integrations);
      setConversations(convRes.conversations);
      setTemplates(tplRes.templates);
      setApprovals(apprRes.approvals);
      setExecutions(execRes.executions);
      setAnalytics(anaRes);
      setMembers(memRes.members);
      setRoles(permRes.roles);
      setPermissions(permRes.permissions);
      setAuditLogs(audRes.audit_logs);
    } catch (err: unknown) {
      setErrorBanner(
        err instanceof Error ? err.message : "Failed to load workspace data"
      );
    }
  }, []);

  // Initial Login / Session Bootstrap
  useEffect(() => {
    async function bootstrapSession() {
      try {
        const loginData = await apiClient.request<{
          access_token: string;
          user: UserProfile;
          organization: OrganizationProfile;
        }>("/auth/login", {
          method: "POST",
          body: JSON.stringify({
            email: "arjun.mehta@nexus.io",
            password: "Nexus@2026!",
          }),
        });
        apiClient.setToken(loginData.access_token);
        setUser(loginData.user);
        setOrganization(loginData.organization);
        await loadWorkspaceData();
      } catch (err: unknown) {
        setErrorBanner(
          err instanceof Error
            ? err.message
            : "Backend API unreachable on port 8000"
        );
      }
    }
    bootstrapSession();
  }, [loadWorkspaceData]);

  const handleSwitchRole = async (
    role: "OWNER" | "ADMIN" | "OPERATOR" | "VIEWER"
  ) => {
    try {
      const res = await apiClient.request<{
        access_token: string;
        user: UserProfile;
        organization: OrganizationProfile;
      }>("/auth/switch-demo-user", {
        method: "POST",
        body: JSON.stringify({ role }),
      });
      apiClient.setToken(res.access_token);
      setUser(res.user);
      setOrganization(res.organization);
      await loadWorkspaceData();
    } catch (err: unknown) {
      setErrorBanner(err instanceof Error ? err.message : String(err));
    }
  };

  const handleSelectConversation = async (convId: string) => {
    try {
      const detail = await apiClient.request<{
        id: string;
        messages: ConversationMessage[];
      }>(`/conversations/${convId}`);
      setActiveConversationId(detail.id);
      setMessages(detail.messages);
      setActiveTab("command-center");
    } catch (err: unknown) {
      setErrorBanner(err instanceof Error ? err.message : String(err));
    }
  };

  const handleExecutePrompt = async (prompt: string) => {
    setIsExecuting(true);
    setErrorBanner(null);

    const optimisticUserMsg: ConversationMessage = {
      id: `temp-${Date.now()}`,
      role: "user",
      content: prompt,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimisticUserMsg]);

    try {
      const result = await apiClient.request<CommandExecutionResult>(
        "/command/execute",
        {
          method: "POST",
          body: JSON.stringify({
            prompt,
            conversation_id: activeConversationId,
          }),
        }
      );

      setActiveConversationId(result.conversation_id);
      await handleSelectConversation(result.conversation_id);
      await loadWorkspaceData();
    } catch (err: unknown) {
      setErrorBanner(err instanceof Error ? err.message : String(err));
    } finally {
      setIsExecuting(false);
    }
  };

  const handleDecideApproval = async (
    approvalId: string,
    decision: "approve" | "reject",
    comment?: string
  ) => {
    setErrorBanner(null);
    try {
      await apiClient.request(`/approvals/${approvalId}/decide`, {
        method: "POST",
        body: JSON.stringify({ decision, comment }),
      });
      if (activeConversationId) {
        await handleSelectConversation(activeConversationId);
      }
      await loadWorkspaceData();
    } catch (err: unknown) {
      setErrorBanner(err instanceof Error ? err.message : String(err));
    }
  };

  const pendingApprovalsCount = approvals.filter(
    (a) => a.status === "pending"
  ).length;
  const connectedServersCount = servers.filter(
    (s) => s.status === "connected"
  ).length;

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#0B0D10] text-[#F5F7FA]">
      <Sidebar
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        user={user}
        organization={organization}
        pendingApprovalsCount={pendingApprovalsCount}
        connectedServersCount={connectedServersCount}
        onSwitchRole={handleSwitchRole}
      />

      <main className="flex-1 flex flex-col h-full overflow-hidden">
        {errorBanner && (
          <div className="px-6 py-2 bg-[#F06C75]/15 border-b border-[#F06C75]/40 text-xs text-[#F06C75] flex items-center justify-between">
            <span>{errorBanner}</span>
            <button
              onClick={() => setErrorBanner(null)}
              className="underline ml-4"
            >
              Dismiss
            </button>
          </div>
        )}

        <div className="flex-1 overflow-y-auto">
          {activeTab === "command-center" && (
            <AICommandCenter
              user={user}
              servers={servers}
              conversations={conversations}
              activeConversationId={activeConversationId}
              messages={messages}
              isExecuting={isExecuting}
              onExecutePrompt={handleExecutePrompt}
              onSelectConversation={handleSelectConversation}
              onNewConversation={() => {
                setActiveConversationId(null);
                setMessages([]);
              }}
              onDecideApproval={handleDecideApproval}
            />
          )}

          {activeTab === "conversations" && (
            <ConversationsView
              conversations={conversations}
              onOpenConversation={handleSelectConversation}
              onDeleteConversation={async (id) => {
                await apiClient.request(`/conversations/${id}`, {
                  method: "DELETE",
                });
                if (activeConversationId === id) {
                  setActiveConversationId(null);
                  setMessages([]);
                }
                await loadWorkspaceData();
              }}
            />
          )}

          {activeTab === "workflows" && (
            <WorkflowsView
              templates={templates}
              onRunTemplate={async (templateId) => {
                const res = await apiClient.request<CommandExecutionResult>(
                  `/workflows/templates/${templateId}/run`,
                  { method: "POST" }
                );
                await handleSelectConversation(res.conversation_id);
                await loadWorkspaceData();
              }}
              onCreateTemplate={async (payload) => {
                await apiClient.request("/workflows/templates", {
                  method: "POST",
                  body: JSON.stringify(payload),
                });
                await loadWorkspaceData();
              }}
            />
          )}

          {activeTab === "mcp-servers" && (
            <MCPServersView
              servers={servers}
              onSyncServer={async (serverId) => {
                await apiClient.request(`/mcp/servers/${serverId}/sync`, {
                  method: "POST",
                });
                await loadWorkspaceData();
              }}
              onToggleServer={async (serverId) => {
                await apiClient.request(`/mcp/servers/${serverId}/toggle`, {
                  method: "POST",
                });
                await loadWorkspaceData();
              }}
              onCreateServer={async (payload) => {
                await apiClient.request("/mcp/servers", {
                  method: "POST",
                  body: JSON.stringify(payload),
                });
                await loadWorkspaceData();
              }}
            />
          )}

          {activeTab === "tool-registry" && (
            <ToolRegistryView
              tools={tools}
              onUpdateTool={async (toolId, payload) => {
                await apiClient.request(`/mcp/tools/${toolId}`, {
                  method: "PATCH",
                  body: JSON.stringify(payload),
                });
                await loadWorkspaceData();
              }}
              onTestTool={async (toolId, args) => {
                return apiClient.request(`/mcp/tools/${toolId}/test`, {
                  method: "POST",
                  body: JSON.stringify({ arguments: args }),
                });
              }}
            />
          )}

          {activeTab === "integrations" && (
            <IntegrationsView
              integrations={integrations}
              onConnectIntegration={async (id, pubCfg, secCreds) => {
                await apiClient.request(`/integrations/${id}/connect`, {
                  method: "POST",
                  body: JSON.stringify({
                    public_config: pubCfg,
                    secret_credentials: secCreds,
                  }),
                });
                await loadWorkspaceData();
              }}
              onTestIntegration={async (id) => {
                await apiClient.request(`/integrations/${id}/test`, {
                  method: "POST",
                });
                await loadWorkspaceData();
              }}
              onDisconnectIntegration={async (id) => {
                await apiClient.request(`/integrations/${id}/disconnect`, {
                  method: "POST",
                });
                await loadWorkspaceData();
              }}
            />
          )}

          {activeTab === "approvals" && (
            <ApprovalsView
              user={user}
              approvals={approvals}
              onDecideApproval={handleDecideApproval}
            />
          )}

          {activeTab === "execution-history" && (
            <ExecutionHistoryView executions={executions} />
          )}

          {activeTab === "analytics" && <AnalyticsView summary={analytics} />}

          {activeTab === "team-members" && (
            <TeamMembersView
              members={members}
              onInviteMember={async (payload) => {
                await apiClient.request("/organization/members/invite", {
                  method: "POST",
                  body: JSON.stringify(payload),
                });
                await loadWorkspaceData();
              }}
              onUpdateRole={async (memberId, role) => {
                await apiClient.request(`/organization/members/${memberId}`, {
                  method: "PATCH",
                  body: JSON.stringify({ role }),
                });
                await loadWorkspaceData();
              }}
            />
          )}

          {activeTab === "permissions" && (
            <PermissionsView roles={roles} permissions={permissions} />
          )}

          {activeTab === "audit-logs" && <AuditLogsView logs={auditLogs} />}

          {activeTab === "settings" && (
            <SettingsView
              organization={organization}
              onSaveSettings={async (payload) => {
                const updated = await apiClient.request<OrganizationProfile>(
                  "/organization/settings",
                  {
                    method: "PATCH",
                    body: JSON.stringify(payload),
                  }
                );
                setOrganization(updated);
                await loadWorkspaceData();
              }}
            />
          )}
        </div>
      </main>
    </div>
  );
}

