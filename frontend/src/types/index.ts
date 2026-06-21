// ── Classifier ────────────────────────────────────────────────────────────────

export interface ClassifyResponse {
  domain: string;
  complexity: "low" | "medium" | "high";
  risk_profile: string;
  agent_count_estimate: number;
  tool_count_estimate: number;
  has_external_api: boolean;
}

// ── Topology ──────────────────────────────────────────────────────────────────

export interface TopologyOption {
  id: "A" | "B";
  name: string;
  description: string;
  tradeoffs_pro: string[];
  tradeoffs_con: string[];
  estimated_cost_usd_low: number;
  estimated_cost_usd_high: number;
  estimated_latency_sec: number;
  recommended: boolean;
  reasoning_chain: string;
}

export interface TopologyResponse {
  option_a: TopologyOption;
  option_b: TopologyOption;
  thinking_summary: string;
}

// ── Scaffold / Blueprint ───────────────────────────────────────────────────────

export interface AgentDefinition {
  name: string;
  role: string;
  model: "claude-haiku-4-5-20251001" | "claude-sonnet-4-6";
  tools: string[];
  system_prompt: string;
}

export interface CostPrediction {
  cost_usd: number;
  latency_sec: number;
  tokens_in: number;
  tokens_out: number;
  bottleneck_agent: string;
  confidence: "low" | "medium" | "high";
}

export interface GraphEdge {
  from_node: string;
  to_node: string;
  condition?: string;
}

export interface GraphBlueprint {
  topology: "A" | "B";
  topology_name: string;
  agents: AgentDefinition[];
  edges: GraphEdge[];
  entry_node: string;
  prediction: CostPrediction;
}

export interface ScaffoldResponse {
  blueprint: GraphBlueprint;
  session_id: string;
}

// ── Run / SSE events ──────────────────────────────────────────────────────────

export interface RunEvent {
  event_type: string;
  agent_name?: string;
  tool_name?: string;
  data: Record<string, unknown>;
  timestamp_ms: number;
}

// Parsed from action.blocked event data
export interface FlagPayload {
  action_id: string;
  misalignment: number;
  oversight: number;
  explanation: string;
  fix_tool_params: Record<string, unknown>;
  fix_explanation: string;
  fix_impact_preview: string;
  fix_type: string;
}

// ── HITL ──────────────────────────────────────────────────────────────────────

export type HITLDecisionType = "approve_fix" | "modify" | "override";

export interface HITLDecision {
  session_id: string;
  run_id: string;
  action_id: string;
  decision: HITLDecisionType;
  modified_params?: Record<string, unknown> | null;
}

// ── UI-only agent node (for graph rendering) ──────────────────────────────────

export type AgentStatus = "idle" | "running" | "done" | "flagged" | "error";

export interface AgentNode {
  name: string;
  role: string;
  model: string;
  tools: string[];
  status: AgentStatus;
}

// ── Proof panel ───────────────────────────────────────────────────────────────

export interface ArizeTrace {
  agent_name: string;
  model: string;
  tokens_in: number;
  tokens_out: number;
  latency_ms: number;
  cost_usd: number;
  safety_score: number | null;
  topology: "A" | "B";
  step: number;
}

export interface ProofData {
  predicted_cost_usd: number;
  topology_a: { actual_cost_usd: number; actual_latency_ms: number; per_agent: ArizeTrace[] };
  topology_b: { actual_cost_usd: number; actual_latency_ms: number; per_agent: ArizeTrace[] };
  safety_drift: { run: number; misalignment: number; oversight: number }[];
  redis_cache_hits: number;
  redis_total_calls: number;
  tokens_saved: number;
  autofix_eval_score: number;
  hallucination_score: number;
  prior_flags_on_pattern: number;
  ab_winner: "A" | "B";
}

// ── Audit ─────────────────────────────────────────────────────────────────────

export interface AuditEvent {
  id: string;
  timestamp: string;
  type: "gate" | "action" | "hitl" | "scaffold";
  agent_name: string;
  tool_name?: string;
  decision?: "ALLOW" | "WARN" | "BLOCK";
  hitl_action?: HITLDecisionType;
  score?: number;
}

export type AppScreen = "input" | "topology" | "scaffold" | "running" | "proof" | "audit";
