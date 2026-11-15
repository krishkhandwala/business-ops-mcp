"use client";

import React, { useState } from "react";
import {
  Server,
  Wrench,
  Blocks,
  RefreshCw,
  Plus,
  Power,
  CheckCircle2,
  XCircle,
  Play,
  ShieldAlert,
  Lock,
  Code2,
} from "lucide-react";
import { IntegrationItem, MCPServerItem, MCPToolItem } from "@/types/nexus";

/* ============================================================================
   MODULE B: MCP SERVER MANAGEMENT
   ============================================================================ */

interface MCPServersViewProps {
  servers: MCPServerItem[];
  onSyncServer: (serverId: string) => Promise<void>;
  onToggleServer: (serverId: string) => Promise<void>;
  onCreateServer: (payload: {
    name: string;
    domain: string;
    description: string;
    transport_type: string;
    endpoint: string;
    auth_method: string;
    credentials?: Record<string, unknown>;
  }) => Promise<void>;
}

export function MCPServersView({
  servers,
  onSyncServer,
  onToggleServer,
  onCreateServer,
}: MCPServersViewProps) {
  const [showRegister, setShowRegister] = useState(false);
  const [name, setName] = useState("");
  const [domain, setDomain] = useState("recruitment");
  const [description, setDescription] = useState("");
  const [transportType, setTransportType] = useState("stdio");
  const [endpoint, setEndpoint] = useState("");
  const [authMethod, setAuthMethod] = useState("bearer");
  const [secretToken, setSecretToken] = useState("");
  const [syncingId, setSyncingId] = useState<string | null>(null);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !endpoint.trim()) return;
    await onCreateServer({
      name,
      domain,
      description,
      transport_type: transportType,
      endpoint,
      auth_method: authMethod,
      credentials: secretToken ? { token: secretToken } : undefined,
    });
    setName("");
    setDescription("");
    setEndpoint("");
    setSecretToken("");
    setShowRegister(false);
  };

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-[#F5F7FA]">
            MCP Server Management
          </h1>
          <p className="text-xs text-[#929BAA] mt-0.5">
            Manage Model Context Protocol (MCP) servers over stdio and
            Streamable HTTP transports. Credentials are encrypted at rest with
            Fernet AES-128-CBC.
          </p>
        </div>
        <button
          onClick={() => setShowRegister(!showRegister)}
          className="px-3.5 py-2 rounded-md bg-[#8B7CFF] text-[#0B0D10] font-semibold text-xs flex items-center gap-1.5"
        >
          <Plus className="w-4 h-4" />
          Register MCP Server
        </button>
      </div>

      {showRegister && (
        <form
          onSubmit={handleRegister}
          className="p-4 rounded-md bg-[#151A22] border border-[#252B35] space-y-3"
        >
          <div className="text-xs font-semibold text-[#F5F7FA]">
            Register New MCP Server
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <input
              type="text"
              placeholder="Server Name (e.g. CRM MCP Server)"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="bg-[#11151B] border border-[#252B35] rounded px-3 py-2 text-xs text-[#F5F7FA]"
              required
            />
            <select
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              className="bg-[#11151B] border border-[#252B35] rounded px-3 py-2 text-xs text-[#F5F7FA]"
            >
              <option value="recruitment">Recruitment Domain</option>
              <option value="employee">Employee / HRMS Domain</option>
              <option value="finance">Finance Domain</option>
              <option value="analytics">Analytics Domain</option>
              <option value="custom">Custom Remote MCP</option>
            </select>
            <select
              value={transportType}
              onChange={(e) => setTransportType(e.target.value)}
              className="bg-[#11151B] border border-[#252B35] rounded px-3 py-2 text-xs text-[#F5F7FA]"
            >
              <option value="stdio">stdio (Local Subprocess)</option>
              <option value="streamable_http">
                Streamable HTTP (Remote MCP)
              </option>
            </select>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <input
              type="text"
              placeholder="Endpoint path or Streamable HTTP URL"
              value={endpoint}
              onChange={(e) => setEndpoint(e.target.value)}
              className="md:col-span-2 bg-[#11151B] border border-[#252B35] rounded px-3 py-2 text-xs text-[#F5F7FA]"
              required
            />
            <select
              value={authMethod}
              onChange={(e) => setAuthMethod(e.target.value)}
              className="bg-[#11151B] border border-[#252B35] rounded px-3 py-2 text-xs text-[#F5F7FA]"
            >
              <option value="internal_token">Internal HMAC Token</option>
              <option value="bearer">Bearer Token</option>
              <option value="api_key">API Key Header</option>
            </select>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <input
              type="text"
              placeholder="Server description..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="bg-[#11151B] border border-[#252B35] rounded px-3 py-2 text-xs text-[#F5F7FA]"
            />
            <input
              type="password"
              placeholder="Auth Secret / Token (Encrypted at rest, never exposed)"
              value={secretToken}
              onChange={(e) => setSecretToken(e.target.value)}
              className="bg-[#11151B] border border-[#252B35] rounded px-3 py-2 text-xs text-[#F5F7FA]"
            />
          </div>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setShowRegister(false)}
              className="px-3 py-1.5 rounded text-xs text-[#929BAA] bg-[#11151B] border border-[#252B35]"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-3.5 py-1.5 rounded text-xs font-semibold bg-[#36C98F] text-[#0B0D10]"
            >
              Connect & Discover MCP Tools
            </button>
          </div>
        </form>
      )}

      <div className="grid grid-cols-1 gap-4">
        {servers.map((srv) => (
          <div
            key={srv.id}
            className="p-5 rounded-md bg-[#151A22] border border-[#252B35] space-y-4"
          >
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded bg-[#11151B] border border-[#252B35] flex items-center justify-center shrink-0">
                  <Server className="w-5 h-5 text-[#8B7CFF]" />
                </div>
                <div>
                  <div className="flex items-center gap-2.5">
                    <h3 className="text-sm font-semibold text-[#F5F7FA]">
                      {srv.name}
                    </h3>
                    <span
                      className={`px-2 py-0.5 text-[10px] font-mono uppercase rounded flex items-center gap-1 ${
                        srv.status === "connected"
                          ? "bg-[#36C98F]/15 text-[#36C98F] border border-[#36C98F]/30"
                          : "bg-[#F06C75]/15 text-[#F06C75] border border-[#F06C75]/30"
                      }`}
                    >
                      {srv.status === "connected" ? (
                        <CheckCircle2 className="w-3 h-3" />
                      ) : (
                        <XCircle className="w-3 h-3" />
                      )}
                      {srv.status} • {srv.health_status}
                    </span>
                    <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-[#11151B] text-[#929BAA] border border-[#252B35]">
                      {srv.transport_type}
                    </span>
                  </div>
                  <p className="text-xs text-[#929BAA] mt-1">
                    {srv.description}
                  </p>
                  <div className="flex flex-wrap items-center gap-4 mt-2 text-[11px] font-mono text-[#929BAA]">
                    <span>Endpoint: {srv.endpoint}</span>
                    <span className="flex items-center gap-1">
                      <Lock className="w-3 h-3 text-[#36C98F]" /> Auth:{" "}
                      {srv.auth_method} (Encrypted)
                    </span>
                    {srv.last_connected_at && (
                      <span>
                        Last Sync:{" "}
                        {new Date(srv.last_connected_at).toLocaleTimeString()}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <button
                  disabled={syncingId === srv.id}
                  onClick={async () => {
                    setSyncingId(srv.id);
                    try {
                      await onSyncServer(srv.id);
                    } finally {
                      setSyncingId(null);
                    }
                  }}
                  className="px-3 py-1.5 rounded text-xs bg-[#11151B] text-[#F5F7FA] border border-[#252B35] hover:border-[#8B7CFF] flex items-center gap-1.5"
                >
                  <RefreshCw
                    className={`w-3.5 h-3.5 ${
                      syncingId === srv.id ? "animate-spin text-[#8B7CFF]" : ""
                    }`}
                  />
                  Discover Tools
                </button>
                <button
                  onClick={() => onToggleServer(srv.id)}
                  className={`px-3 py-1.5 rounded text-xs font-medium border flex items-center gap-1.5 ${
                    srv.status === "connected"
                      ? "bg-[#11151B] text-[#F06C75] border-[#F06C75]/40 hover:bg-[#F06C75]/10"
                      : "bg-[#36C98F]/15 text-[#36C98F] border-[#36C98F]/40"
                  }`}
                >
                  <Power className="w-3.5 h-3.5" />
                  {srv.status === "connected" ? "Disconnect" : "Connect"}
                </button>
              </div>
            </div>

            {srv.last_error && (
              <div className="p-2.5 rounded bg-[#F06C75]/10 border border-[#F06C75]/40 text-xs text-[#F06C75] font-mono">
                Connection Error: {srv.last_error}
              </div>
            )}

            {/* Discovered MCP Tools Preview */}
            <div className="pt-3 border-t border-[#252B35]">
              <div className="text-[11px] font-mono uppercase text-[#929BAA] mb-2">
                Discovered MCP Tools ({srv.tools.length})
              </div>
              <div className="flex flex-wrap gap-2">
                {srv.tools.map((t) => (
                  <div
                    key={t.id}
                    className="px-2.5 py-1 rounded bg-[#11151B] border border-[#252B35] text-xs flex items-center gap-2"
                  >
                    <span className="font-mono text-[#F5F7FA]">
                      {t.tool_name}
                    </span>
                    <span
                      className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                        t.risk_classification === "HIGH_RISK_WRITE"
                          ? "bg-[#E9AE54]/20 text-[#E9AE54]"
                          : "bg-[#36C98F]/15 text-[#36C98F]"
                      }`}
                    >
                      {t.risk_classification}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ============================================================================
   MODULE C: CENTRALIZED TOOL REGISTRY
   ============================================================================ */

interface ToolRegistryViewProps {
  tools: MCPToolItem[];
  onUpdateTool: (
    toolId: string,
    payload: {
      is_enabled?: boolean;
      risk_classification?: string;
      requires_approval?: boolean;
    }
  ) => Promise<void>;
  onTestTool: (
    toolId: string,
    args: Record<string, unknown>
  ) => Promise<unknown>;
}

export function ToolRegistryView({
  tools,
  onUpdateTool,
  onTestTool,
}: ToolRegistryViewProps) {
  const [selectedTool, setSelectedTool] = useState<MCPToolItem | null>(null);
  const [testArgsText, setTestArgsText] = useState("{}");
  const [testResult, setTestResult] = useState<string | null>(null);
  const [testing, setTesting] = useState(false);

  const handleRunTest = async () => {
    if (!selectedTool) return;
    setTesting(true);
    setTestResult(null);
    try {
      const parsed = JSON.parse(testArgsText || "{}");
      const res = await onTestTool(selectedTool.id, parsed);
      setTestResult(JSON.stringify(res, null, 2));
    } catch (err: unknown) {
      setTestResult(
        `Error: ${err instanceof Error ? err.message : String(err)}`
      );
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-[#F5F7FA]">
          Centralized MCP Tool Registry
        </h1>
        <p className="text-xs text-[#929BAA] mt-0.5">
          Inspect dynamically discovered MCP tool schemas, risk classifications,
          role permissions, and test live MCP execution.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-3">
          {tools.map((tool) => (
            <div
              key={tool.id}
              onClick={() => {
                setSelectedTool(tool);
                setTestResult(null);
              }}
              className={`p-4 rounded-md border cursor-pointer transition-colors ${
                selectedTool?.id === tool.id
                  ? "bg-[#151A22] border-[#8B7CFF]"
                  : "bg-[#151A22] border-[#252B35] hover:border-[#8B7CFF]/40"
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="flex items-center gap-2">
                    <Wrench className="w-4 h-4 text-[#8B7CFF]" />
                    <span className="text-sm font-mono font-semibold text-[#F5F7FA]">
                      {tool.tool_name}
                    </span>
                    <span className="text-xs text-[#929BAA]">
                      ({tool.mcp_server_name})
                    </span>
                  </div>
                  <p className="text-xs text-[#929BAA] mt-1">
                    {tool.description}
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span
                    className={`px-2 py-0.5 text-[10px] font-mono rounded ${
                      tool.risk_classification === "HIGH_RISK_WRITE"
                        ? "bg-[#E9AE54]/20 text-[#E9AE54] border border-[#E9AE54]/40"
                        : tool.risk_classification === "LOW_RISK_WRITE"
                        ? "bg-[#8B7CFF]/20 text-[#8B7CFF]"
                        : "bg-[#36C98F]/15 text-[#36C98F]"
                    }`}
                  >
                    {tool.risk_classification}
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onUpdateTool(tool.id, { is_enabled: !tool.is_enabled });
                    }}
                    className={`px-2 py-0.5 text-[10px] font-mono rounded border ${
                      tool.is_enabled
                        ? "bg-[#36C98F]/15 text-[#36C98F] border-[#36C98F]/30"
                        : "bg-[#11151B] text-[#929BAA] border-[#252B35]"
                    }`}
                  >
                    {tool.is_enabled ? "ENABLED" : "DISABLED"}
                  </button>
                </div>
              </div>
              <div className="flex items-center justify-between mt-3 pt-2 border-t border-[#252B35]/60 text-[11px] font-mono text-[#929BAA]">
                <span>Roles: {tool.required_roles.join(", ")}</span>
                <span>
                  Approval Gate: {tool.requires_approval ? "Required" : "Auto"}
                </span>
                <span>Invocations: {tool.invocation_count}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Right Schema Inspector & Live MCP Tester */}
        <div className="bg-[#151A22] border border-[#252B35] rounded-md p-4 h-fit sticky top-6 space-y-4">
          {selectedTool ? (
            <>
              <div>
                <div className="text-xs font-mono text-[#8B7CFF] uppercase">
                  MCP Tool Schema & Tester
                </div>
                <h3 className="text-sm font-mono font-semibold text-[#F5F7FA] mt-0.5">
                  {selectedTool.tool_name}
                </h3>
                <p className="text-xs text-[#929BAA] mt-1">
                  {selectedTool.description}
                </p>
              </div>

              <div>
                <div className="text-[11px] font-mono text-[#929BAA] mb-1 flex items-center gap-1">
                  <Code2 className="w-3.5 h-3.5" /> JSON Input Schema
                </div>
                <pre className="p-2.5 rounded bg-[#0B0D10] border border-[#252B35] text-[11px] font-mono text-[#F5F7FA] overflow-x-auto max-h-48">
                  {JSON.stringify(selectedTool.input_schema, null, 2)}
                </pre>
              </div>

              {selectedTool.risk_classification === "READ" ? (
                <div className="space-y-2 pt-2 border-t border-[#252B35]">
                  <label className="block text-[11px] font-mono text-[#929BAA]">
                    Test Arguments (JSON):
                  </label>
                  <textarea
                    value={testArgsText}
                    onChange={(e) => setTestArgsText(e.target.value)}
                    rows={3}
                    className="w-full bg-[#0B0D10] border border-[#252B35] rounded p-2 text-xs font-mono text-[#F5F7FA]"
                  />
                  <button
                    disabled={testing}
                    onClick={handleRunTest}
                    className="w-full py-2 rounded bg-[#8B7CFF] text-[#0B0D10] font-semibold text-xs flex items-center justify-center gap-1.5"
                  >
                    <Play className="w-3.5 h-3.5" />
                    {testing
                      ? "Invoking via MCP Client..."
                      : "Test Tool Execution"}
                  </button>
                  {testResult && (
                    <pre className="p-2.5 rounded bg-[#0B0D10] border border-[#252B35] text-[11px] font-mono text-[#36C98F] overflow-x-auto max-h-60">
                      {testResult}
                    </pre>
                  )}
                </div>
              ) : (
                <div className="p-3 rounded bg-[#E9AE54]/10 border border-[#E9AE54]/40 text-xs text-[#E9AE54] flex items-start gap-2">
                  <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>
                    This tool is classified as{" "}
                    <strong>{selectedTool.risk_classification}</strong> and is
                    governed by the Human Approval Engine inside the AI Command
                    Center.
                  </span>
                </div>
              )}
            </>
          ) : (
            <div className="text-xs text-[#929BAA] py-8 text-center">
              Select any MCP tool on the left to inspect its JSON schema and run
              live protocol tests.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ============================================================================
   MODULE D: INTEGRATIONS MARKETPLACE
   ============================================================================ */

interface IntegrationsViewProps {
  integrations: IntegrationItem[];
  onConnectIntegration: (
    id: string,
    publicConfig: Record<string, unknown>,
    secretCredentials: Record<string, unknown>
  ) => Promise<void>;
  onTestIntegration: (id: string) => Promise<void>;
  onDisconnectIntegration: (id: string) => Promise<void>;
}

export function IntegrationsView({
  integrations,
  onConnectIntegration,
  onTestIntegration,
  onDisconnectIntegration,
}: IntegrationsViewProps) {
  const [configuringItem, setConfiguringItem] =
    useState<IntegrationItem | null>(null);
  const [endpointInput, setEndpointInput] = useState("");
  const [secretInput, setSecretInput] = useState("");

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-[#F5F7FA]">
          Enterprise Integrations Marketplace
        </h1>
        <p className="text-xs text-[#929BAA] mt-0.5">
          Connect databases, custom REST APIs, and SaaS platforms to expose
          their capabilities as governed MCP tools. Only verified connections
          are marked connected.
        </p>
      </div>

      {configuringItem && (
        <div className="p-4 rounded-md bg-[#151A22] border border-[#8B7CFF] space-y-3">
          <div className="text-sm font-semibold text-[#F5F7FA]">
            Configure & Connect: {configuringItem.name}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <input
              type="text"
              placeholder="Host / Base URL (e.g. postgresql://localhost:5432 or https://api.example.com)"
              value={endpointInput}
              onChange={(e) => setEndpointInput(e.target.value)}
              className="bg-[#11151B] border border-[#252B35] rounded px-3 py-2 text-xs text-[#F5F7FA]"
            />
            <input
              type="password"
              placeholder="API Key / Password (Encrypted via Fernet)"
              value={secretInput}
              onChange={(e) => setSecretInput(e.target.value)}
              className="bg-[#11151B] border border-[#252B35] rounded px-3 py-2 text-xs text-[#F5F7FA]"
            />
          </div>
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setConfiguringItem(null)}
              className="px-3 py-1.5 rounded text-xs text-[#929BAA] bg-[#11151B] border border-[#252B35]"
            >
              Cancel
            </button>
            <button
              onClick={async () => {
                await onConnectIntegration(
                  configuringItem.id,
                  { endpoint: endpointInput || "localhost" },
                  { api_key: secretInput || "configured" }
                );
                setConfiguringItem(null);
                setEndpointInput("");
                setSecretInput("");
              }}
              className="px-3.5 py-1.5 rounded text-xs font-semibold bg-[#36C98F] text-[#0B0D10]"
            >
              Verify & Establish Connection
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {integrations.map((integ) => {
          const isConnected = integ.status === "connected";
          return (
            <div
              key={integ.id}
              className="p-5 rounded-md bg-[#151A22] border border-[#252B35] flex flex-col justify-between space-y-4"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded bg-[#11151B] border border-[#252B35] flex items-center justify-center">
                      <Blocks className="w-4 h-4 text-[#8B7CFF]" />
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-[#F5F7FA]">
                        {integ.name}
                      </h3>
                      <span className="text-[10px] font-mono text-[#929BAA]">
                        {integ.category}
                      </span>
                    </div>
                  </div>
                  <span
                    className={`px-2 py-0.5 text-[10px] font-mono uppercase rounded ${
                      isConnected
                        ? "bg-[#36C98F]/15 text-[#36C98F] border border-[#36C98F]/30"
                        : "bg-[#11151B] text-[#929BAA] border border-[#252B35]"
                    }`}
                  >
                    {integ.status}
                  </span>
                </div>

                <p className="text-xs text-[#929BAA] leading-relaxed">
                  {integ.description}
                </p>

                <div className="flex flex-wrap gap-1.5 pt-1">
                  {integ.available_tools.map((t) => (
                    <span
                      key={t}
                      className="px-2 py-0.5 rounded bg-[#11151B] border border-[#252B35] text-[10px] font-mono text-[#F5F7FA]"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              </div>

              <div className="pt-3 border-t border-[#252B35] flex items-center justify-between">
                <span className="text-[11px] font-mono text-[#929BAA]">
                  Scopes: {integ.permissions_scope.join(", ")}
                </span>
                <div className="flex items-center gap-2">
                  {isConnected ? (
                    <>
                      <button
                        onClick={() => onTestIntegration(integ.id)}
                        className="px-2.5 py-1 rounded text-xs bg-[#11151B] text-[#F5F7FA] border border-[#252B35] hover:border-[#8B7CFF]"
                      >
                        Test Connection
                      </button>
                      <button
                        onClick={() => onDisconnectIntegration(integ.id)}
                        className="px-2.5 py-1 rounded text-xs bg-[#11151B] text-[#F06C75] border border-[#F06C75]/40"
                      >
                        Disconnect
                      </button>
                    </>
                  ) : (
                    <button
                      onClick={() => setConfiguringItem(integ)}
                      className="px-3 py-1.5 rounded text-xs font-semibold bg-[#8B7CFF] text-[#0B0D10]"
                    >
                      Connect
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

