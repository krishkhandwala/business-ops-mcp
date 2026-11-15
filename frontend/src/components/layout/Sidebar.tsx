"use client";

import React from "react";
import {
  Terminal,
  MessageSquare,
  GitBranch,
  Blocks,
  Server,
  Wrench,
  History,
  ShieldCheck,
  BarChart3,
  Users,
  KeyRound,
  FileSearch,
  Settings,
  PanelLeftClose,
  PanelLeftOpen,
  Cpu,
} from "lucide-react";
import { NavigationTab, OrganizationProfile, UserProfile } from "@/types/nexus";

interface SidebarProps {
  activeTab: NavigationTab;
  onSelectTab: (tab: NavigationTab) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
  user: UserProfile | null;
  organization: OrganizationProfile | null;
  pendingApprovalsCount: number;
  connectedServersCount: number;
  onSwitchRole: (role: "OWNER" | "ADMIN" | "OPERATOR" | "VIEWER") => void;
}

interface NavGroup {
  label: string;
  items: {
    id: NavigationTab;
    label: string;
    icon: React.ComponentType<{ className?: string }>;
    badge?: number;
  }[];
}

export function Sidebar({
  activeTab,
  onSelectTab,
  collapsed,
  onToggleCollapse,
  user,
  organization,
  pendingApprovalsCount,
  connectedServersCount,
  onSwitchRole,
}: SidebarProps) {
  const groups: NavGroup[] = [
    {
      label: "WORKSPACE",
      items: [
        { id: "command-center", label: "AI Command Center", icon: Terminal },
        { id: "conversations", label: "Conversations", icon: MessageSquare },
        { id: "workflows", label: "Workflows", icon: GitBranch },
      ],
    },
    {
      label: "CONNECT",
      items: [
        { id: "integrations", label: "Integrations", icon: Blocks },
        {
          id: "mcp-servers",
          label: "MCP Servers",
          icon: Server,
          badge: connectedServersCount,
        },
        { id: "tool-registry", label: "Tool Registry", icon: Wrench },
      ],
    },
    {
      label: "MANAGE",
      items: [
        { id: "execution-history", label: "Execution History", icon: History },
        {
          id: "approvals",
          label: "Approvals",
          icon: ShieldCheck,
          badge: pendingApprovalsCount,
        },
        { id: "analytics", label: "Analytics", icon: BarChart3 },
      ],
    },
    {
      label: "ORGANIZATION",
      items: [
        { id: "team-members", label: "Team Members", icon: Users },
        { id: "permissions", label: "Permissions", icon: KeyRound },
        { id: "audit-logs", label: "Audit Logs", icon: FileSearch },
        { id: "settings", label: "Settings", icon: Settings },
      ],
    },
  ];

  return (
    <aside
      className={`${
        collapsed ? "w-16" : "w-64"
      } flex flex-col bg-[#11151B] border-r border-[#252B35] transition-all duration-200 select-none shrink-0`}
    >
      {/* Brand Header */}
      <div className="h-14 px-4 flex items-center justify-between border-b border-[#252B35]">
        <div className="flex items-center gap-2.5 overflow-hidden">
          <div className="w-7 h-7 rounded bg-[#151A22] border border-[#8B7CFF]/50 flex items-center justify-center shrink-0">
            <Cpu className="w-4 h-4 text-[#8B7CFF]" />
          </div>
          {!collapsed && (
            <div className="flex flex-col">
              <span className="text-sm font-semibold tracking-wider text-[#F5F7FA]">
                NEXUS
              </span>
              <span className="text-[10px] text-[#929BAA] truncate max-w-[140px]">
                {organization?.name || "Enterprise Operations"}
              </span>
            </div>
          )}
        </div>
        <button
          onClick={onToggleCollapse}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className="p-1.5 rounded text-[#929BAA] hover:text-[#F5F7FA] hover:bg-[#151A22] transition-colors"
        >
          {collapsed ? (
            <PanelLeftOpen className="w-4 h-4" />
          ) : (
            <PanelLeftClose className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* Navigation Sections */}
      <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-5">
        {groups.map((group) => (
          <div key={group.label}>
            {!collapsed && (
              <div className="px-2.5 mb-1.5 text-[10px] font-semibold tracking-widest text-[#929BAA]/80 uppercase">
                {group.label}
              </div>
            )}
            <div className="space-y-0.5">
              {group.items.map((item) => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => onSelectTab(item.id)}
                    title={collapsed ? item.label : undefined}
                    className={`w-full flex items-center justify-between px-2.5 py-2 rounded-md text-xs font-medium transition-colors ${
                      isActive
                        ? "bg-[#151A22] text-[#F5F7FA] border border-[#252B35] shadow-sm"
                        : "text-[#929BAA] hover:text-[#F5F7FA] hover:bg-[#151A22]/60 border border-transparent"
                    }`}
                  >
                    <div className="flex items-center gap-2.5 truncate">
                      <Icon
                        className={`w-4 h-4 shrink-0 ${
                          isActive ? "text-[#8B7CFF]" : "text-[#929BAA]"
                        }`}
                      />
                      {!collapsed && (
                        <span className="truncate">{item.label}</span>
                      )}
                    </div>
                    {!collapsed &&
                      item.badge !== undefined &&
                      item.badge > 0 && (
                        <span
                          className={`px-1.5 py-0.5 text-[10px] rounded font-mono ${
                            item.id === "approvals"
                              ? "bg-[#E9AE54]/20 text-[#E9AE54] border border-[#E9AE54]/40"
                              : "bg-[#8B7CFF]/15 text-[#8B7CFF]"
                          }`}
                        >
                          {item.badge}
                        </span>
                      )}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Active User & RBAC Role Switcher Footer */}
      <div className="p-3 border-t border-[#252B35] bg-[#0B0D10]/50">
        {!collapsed && user ? (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="truncate">
                <div className="text-xs font-medium text-[#F5F7FA] truncate">
                  {user.full_name}
                </div>
                <div className="text-[11px] text-[#929BAA] truncate">
                  {user.email}
                </div>
              </div>
              <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-[#8B7CFF]/15 text-[#8B7CFF] border border-[#8B7CFF]/30">
                {user.role}
              </span>
            </div>
            <div className="pt-1">
              <label className="block text-[10px] text-[#929BAA] mb-1">
                Active RBAC Persona:
              </label>
              <div className="grid grid-cols-4 gap-1">
                {(["OWNER", "ADMIN", "OPERATOR", "VIEWER"] as const).map(
                  (r) => (
                    <button
                      key={r}
                      onClick={() => onSwitchRole(r)}
                      className={`py-1 text-[9px] font-mono rounded border transition-colors ${
                        user.role === r
                          ? "bg-[#8B7CFF] text-[#0B0D10] border-[#8B7CFF] font-semibold"
                          : "bg-[#151A22] text-[#929BAA] border-[#252B35] hover:text-[#F5F7FA]"
                      }`}
                    >
                      {r}
                    </button>
                  )
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="flex justify-center">
            <span className="w-2.5 h-2.5 rounded-full bg-[#36C98F]" />
          </div>
        )}
      </div>
    </aside>
  );
}

