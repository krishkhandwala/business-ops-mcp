export type NavigationTab =
  | "command-center"
  | "conversations"
  | "workflows"
  | "integrations"
  | "mcp-servers"
  | "tool-registry"
  | "execution-history"
  | "approvals"
  | "analytics"
  | "team-members"
  | "permissions"
  | "audit-logs"
  | "settings";

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  role: "OWNER" | "ADMIN" | "OPERATOR" | "VIEWER";
}

export interface OrganizationProfile {
  id: string;
  name: string;
  slug: string;
  domain?: string;
  plan_tier: string;
  approval_policy: {
    require_approval_for_high_risk: boolean;
    require_approval_for_low_risk: boolean;
    allowed_approver_roles: string[];
    max_auto_tool_calls: number;
  };
  settings_json?: Record<string, unknown>;
}

export interface ExecutionStepItem {
  step_number: number;
  node_name: string;
  title: string;
  status: "running" | "completed" | "awaiting_approval" | "failed";
  details?: Record<string, unknown>;
  duration_ms?: number;
}

export interface PendingApprovalCard {
  approval_id: string;
  tool_name: string;
  display_name?: string;
  server_name: string;
  risk_classification: "READ" | "LOW_RISK_WRITE" | "HIGH_RISK_WRITE";
  title: string;
  description: string;
  proposed_arguments: Record<string, unknown>;
  status: "pending" | "approved" | "rejected";
  created_at?: string;
}

export interface KPICard {
  label: string;
  value: string;
  status?: "accent" | "success" | "warning" | "error";
}

export interface ToolOutputTrace {
  tool_name: string;
  server_id: string;
  server_name: string;
  risk_classification: string;
  duration_ms: number;
  arguments: Record<string, unknown>;
  output: Record<string, unknown>;
}

export interface CommandExecutionResult {
  execution_id: string;
  conversation_id: string;
  message_id?: string;
  status: "completed" | "awaiting_approval" | "failed" | "rejected" | "running";
  intent: string;
  summary: string;
  duration_ms?: number;
  prompt_tokens?: number;
  completion_tokens?: number;
  estimated_cost_usd?: number;
  table_columns?: string[];
  table_rows?: Record<string, unknown>[];
  chart_data?: Record<string, unknown>[];
  kpi_cards?: KPICard[];
  tool_outputs?: ToolOutputTrace[];
  pending_approvals?: PendingApprovalCard[];
  steps?: ExecutionStepItem[];
  error?: string;
}

export interface ConversationSummary {
  id: string;
  title: string;
  status: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface ConversationMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  structured_data?: CommandExecutionResult;
  agent_execution_id?: string;
  created_at: string;
}

export interface MCPServerItem {
  id: string;
  name: string;
  slug: string;
  domain: string;
  description: string;
  transport_type: string;
  endpoint: string;
  auth_method: string;
  has_encrypted_credentials: boolean;
  status: "connected" | "disconnected" | "error";
  health_status: string;
  is_enabled: boolean;
  last_connected_at?: string;
  last_error?: string;
  tools_count: number;
  tools: {
    id: string;
    tool_name: string;
    display_name: string;
    description: string;
    risk_classification: string;
    requires_approval: boolean;
    is_enabled: boolean;
    invocation_count: number;
  }[];
}

export interface MCPToolItem {
  id: string;
  tool_name: string;
  display_name: string;
  description: string;
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  mcp_server_id: string;
  mcp_server_name: string;
  domain: string;
  risk_classification: "READ" | "LOW_RISK_WRITE" | "HIGH_RISK_WRITE";
  required_roles: string[];
  requires_approval: boolean;
  is_enabled: boolean;
  invocation_count: number;
  last_invoked_at?: string;
}

export interface IntegrationItem {
  id: string;
  provider_key: string;
  name: string;
  category: string;
  description: string;
  status: "connected" | "disconnected" | "error";
  public_config: Record<string, unknown>;
  available_tools: string[];
  permissions_scope: string[];
  linked_mcp_server_id?: string;
  last_tested_at?: string;
}

export interface WorkflowTemplateItem {
  id: string;
  name: string;
  description: string;
  category: string;
  prompt_template: string;
  steps_definition: string[];
  risk_level: string;
  run_count: number;
  is_active: boolean;
}

export interface ApprovalRecord {
  id: string;
  agent_execution_id: string;
  conversation_id?: string;
  tool_name: string;
  server_name: string;
  risk_classification: string;
  title: string;
  description: string;
  proposed_arguments: Record<string, unknown>;
  status: "pending" | "approved" | "rejected";
  reviewer_comment?: string;
  execution_result?: Record<string, unknown>;
  created_at: string;
  reviewed_at?: string;
}

export interface ExecutionHistoryItem {
  id: string;
  conversation_id?: string;
  user_prompt: string;
  intent: string;
  status: string;
  duration_ms: number;
  tools_invoked: string[];
  steps_count: number;
  approvals_count: number;
  prompt_tokens: number;
  completion_tokens: number;
  estimated_cost_usd: number;
  started_at: string;
  completed_at?: string;
}

export interface AnalyticsSummary {
  total_ai_tasks_executed: number;
  successful_executions: number;
  failed_executions: number;
  awaiting_approval_executions: number;
  average_execution_duration_ms: number;
  mcp_tool_invocation_count: number;
  connected_integrations: number;
  connected_mcp_servers: number;
  pending_approvals: number;
  token_consumption: number;
  estimated_ai_usage_cost_usd: number;
  most_frequently_used_tools: {
    tool_name: string;
    display_name: string;
    invocations: number;
    risk: string;
  }[];
}

