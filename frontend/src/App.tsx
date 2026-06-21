import { useState, useCallback, useRef } from "react";
import { InputScreen } from "./components/InputScreen";
import { TopologyPicker } from "./components/TopologyPicker";
import { AgentGraph } from "./components/AgentGraph";
import { FlagModal } from "./components/FlagModal";
import { ProofPanel } from "./components/ProofPanel";
import { AuditLog } from "./components/AuditLog";
import { SponsorLog, eventToLogEntries } from "./components/SponsorLog";
import type { LogEntry } from "./components/SponsorLog";
import { useRealtimeEvents } from "./hooks/useRealtimeEvents";
import { api, MOCK } from "./api/client";
import type {
  ClassifyResponse,
  TopologyResponse,
  TopologyOption,
  GraphBlueprint,
  AgentNode,
  AgentStatus,
  FlagPayload,
  HITLDecisionType,
  ProofData,
  AuditEvent,
  AppScreen,
} from "./types";
import { BarChart2, List, Play, Shield } from "lucide-react";

const USE_MOCK = import.meta.env.VITE_USE_MOCK !== "false";
const SESSION_ID = `session-${Date.now()}`;

function NavButton({ label, icon, active, onClick }: {
  label: string; icon: React.ReactNode; active: boolean; onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg transition-colors font-medium ${
        active ? "bg-emerald-600 text-white shadow-sm" : "text-emerald-600 hover:bg-emerald-100"
      }`}
    >
      {icon}{label}
    </button>
  );
}

interface ActiveFlag {
  agentName: string;
  toolName: string;
  payload: FlagPayload;
}

export default function App() {
  const [screen, setScreen] = useState<AppScreen>("input");
  const [loading, setLoading] = useState(false);
  const [prompt, setPrompt] = useState("");

  // Data from API calls
  const [classification, setClassification] = useState<ClassifyResponse | null>(null);
  const [topologyResponse, setTopologyResponse] = useState<TopologyResponse | null>(null);
  const [blueprint, setBlueprint] = useState<GraphBlueprint | null>(null);

  // Run state
  const [runId, setRunId] = useState<string | null>(null);
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [agents, setAgents] = useState<AgentNode[]>([]);

  // Flag modal
  const [activeFlag, setActiveFlag] = useState<ActiveFlag | null>(null);
  const pendingActionRef = useRef<{ action_id: string } | null>(null);

  // Proof + audit
  const [proof, setProof] = useState<ProofData | null>(null);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [sponsorLog, setSponsorLog] = useState<LogEntry[]>([]);

  // ── SSE from Joseph's backend ─────────────────────────────────────────────

  useRealtimeEvents(screen === "running" ? streamUrl : null, {
    onAgentStatus: useCallback((agentName: string, status: AgentStatus) => {
      setAgents((prev) =>
        prev.map((a) => a.name === agentName || a.name.toLowerCase().includes(agentName.toLowerCase())
          ? { ...a, status } : a)
      );
      // Track in audit log
      setAuditEvents((prev) => [
        ...prev,
        {
          id: `evt-${Date.now()}-${Math.random()}`,
          timestamp: new Date().toISOString(),
          type: "action",
          agent_name: agentName,
          decision: status === "done" ? "ALLOW" : undefined,
        },
      ]);
    }, []),

    onFlag: useCallback((agentName: string, toolName: string, payload: FlagPayload) => {
      pendingActionRef.current = { action_id: payload.action_id };
      setActiveFlag({ agentName, toolName, payload });
      setAuditEvents((prev) => [
        ...prev,
        {
          id: `gate-${payload.action_id}`,
          timestamp: new Date().toISOString(),
          type: "gate",
          agent_name: agentName,
          tool_name: toolName,
          decision: payload.misalignment >= 70 ? "BLOCK" : "WARN",
          score: payload.misalignment,
        },
      ]);
    }, []),

    onRunComplete: useCallback(async () => {
      const p = USE_MOCK
        ? MOCK.proof()
        : await api.proof(SESSION_ID);
      setProof(p);
      setScreen("proof");
    }, []),

    onError: useCallback((msg: string) => {
      console.error("Run error:", msg);
    }, []),

    onRawEvent: useCallback((evt: import("./types").RunEvent) => {
      const entries = eventToLogEntries(evt);
      if (entries.length > 0) {
        setSponsorLog((prev) => [...prev, ...entries]);
      }
    }, []),
  });

  // ── Step 1: Classify ──────────────────────────────────────────────────────

  async function handlePromptSubmit(p: string) {
    setPrompt(p);
    setLoading(true);
    try {
      const cls = USE_MOCK ? MOCK.classify() : await api.classify(p);
      setClassification(cls);
      const topo = USE_MOCK ? MOCK.topology() : await api.topology(p, cls);
      setTopologyResponse(topo);
      setScreen("topology");
    } finally {
      setLoading(false);
    }
  }

  // ── Step 2: Scaffold ──────────────────────────────────────────────────────

  async function handleTopologySelect(opt: TopologyOption) {
    if (!classification) return;
    setLoading(true);
    try {
      const result = USE_MOCK
        ? MOCK.scaffold()
        : await api.scaffold(prompt, classification, opt, SESSION_ID);
      setBlueprint(result.blueprint);
      // Build UI agent nodes from blueprint
      setAgents(result.blueprint.agents.map((a) => ({
        name: a.name,
        role: a.role,
        model: a.model,
        tools: a.tools,
        status: "idle" as AgentStatus,
      })));
      setScreen("scaffold");
    } finally {
      setLoading(false);
    }
  }

  // ── Step 3: Run ───────────────────────────────────────────────────────────

  async function handleRun() {
    if (!blueprint) return;
    setScreen("running");

    if (USE_MOCK) {
      simulateMockRun();
      return;
    }

    const result = await api.runStart(SESSION_ID, blueprint, prompt);
    setRunId(result.run_id);
    setStreamUrl(api.streamUrl(result.run_id));
  }

  // ── Step 4: HITL ──────────────────────────────────────────────────────────

  async function handleHITL(decision: HITLDecisionType, modifiedParams?: Record<string, unknown>) {
    if (!activeFlag) return;
    const actionId = activeFlag.payload.action_id;

    setAuditEvents((prev) => [
      ...prev,
      {
        id: `hitl-${actionId}`,
        timestamp: new Date().toISOString(),
        type: "hitl",
        agent_name: activeFlag.agentName,
        tool_name: activeFlag.toolName,
        hitl_action: decision,
        score: activeFlag.payload.misalignment,
      },
    ]);

    setActiveFlag(null);

    if (!USE_MOCK && runId) {
      await api.runDecide({
        session_id: SESSION_ID,
        run_id: runId,
        action_id: actionId,
        decision,
        modified_params: modifiedParams ?? null,
      });
    } else {
      // Mock: continue simulation after HITL
      setTimeout(() => setAgents((prev) =>
        prev.map((a) => a.status === "flagged" ? { ...a, status: "done" } : a)
      ), 500);
      setTimeout(() => setAgents((prev) =>
        prev.map((a) => a.name === "Email Agent" ? { ...a, status: "running" } : a)
      ), 1000);
      setTimeout(() => {
        setAgents((prev) =>
          prev.map((a) => a.name === "Email Agent" ? { ...a, status: "done" } : a)
        );
        setProof(MOCK.proof());
        setAuditEvents((prev) => [...prev, ...MOCK_AUDIT_TAIL]);
        setScreen("proof");
      }, 2500);
    }
  }

  // ── Export ─────────────────────────────────────────────────────────────────

  function handleExport() {
    if (!USE_MOCK && proof) {
      const url = api.exportBlueprint(
        SESSION_ID,
        proof.topology_a.actual_cost_usd,
        proof.topology_a.actual_latency_ms / 1000,
      );
      window.open(url, "_blank");
      return;
    }
    const data = { session_id: SESSION_ID, events: auditEvents, proof };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "safe-agent-blueprint.json";
    a.click();
  }

  // ── Mock simulation ────────────────────────────────────────────────────────

  function simulateMockRun() {
    setSponsorLog([]);
    const seq: [string, AgentStatus, number][] = [
      ["Coordinator", "running", 300],
      ["Resume Parser", "running", 900],
      ["Resume Parser", "done", 1900],
      ["Candidate Scorer", "running", 2200],
    ];
    seq.forEach(([name, status, delay]) =>
      setTimeout(() =>
        setAgents((prev) => prev.map((a) => a.name === name ? { ...a, status } : a))
      , delay)
    );

    // Mock sponsor log timeline
    const mockEntries: [LogEntry, number][] = [
      [{ id: "m1", timestamp: "", sponsor: "anthropic", label: "Claude Haiku 4.5 starting Coordinator", detail: "pre-classify domain + complexity" }, 300],
      [{ id: "m2", timestamp: "", sponsor: "arize", label: "Trace emitted for Coordinator", detail: "tokens · latency · cost → Phoenix" }, 700],
      [{ id: "m3", timestamp: "", sponsor: "anthropic", label: "Claude Haiku 4.5 starting Resume Parser", detail: "tool: parse_resume" }, 900],
      [{ id: "m4", timestamp: "", sponsor: "redis", label: "T1 Guardrails: PASS <1ms", detail: "pattern match on parse_resume — no blocked patterns" }, 1100],
      [{ id: "m5", timestamp: "", sponsor: "redis", label: "T2 Semantic Cache: MISS → routing to T3", detail: "similarity 0.61 — below threshold" }, 1300],
      [{ id: "m6", timestamp: "", sponsor: "anthropic", label: "T3 Sonnet scored: misalignment=12 oversight=8", detail: "decision: ALLOW 820ms", tier: 3 }, 1700],
      [{ id: "m7", timestamp: "", sponsor: "redis", label: "Action allowed — event written to Stream", detail: "parse_resume approved" }, 1850],
      [{ id: "m8", timestamp: "", sponsor: "arize", label: "Trace emitted for Resume Parser", detail: "tokens · latency · cost → Phoenix" }, 1900],
      [{ id: "m9", timestamp: "", sponsor: "anthropic", label: "Claude Sonnet 4.6 starting Candidate Scorer", detail: "tool: apply_scoring_rubric" }, 2200],
      [{ id: "m10", timestamp: "", sponsor: "redis", label: "T1 Guardrails: PASS <1ms", detail: "pattern match on apply_scoring_rubric" }, 2350],
      [{ id: "m11", timestamp: "", sponsor: "redis", label: "T2 Semantic routing: goal-divergent signal → Misalignment scorer", detail: "similarity 0.88 — routing with cached context" }, 2600, ],
      [{ id: "m12", timestamp: "", sponsor: "anthropic", label: "T3 Sonnet scored: misalignment=87 oversight=31", detail: "decision: WARN 847ms", tier: 3 }, 3000],
      [{ id: "m13", timestamp: "", sponsor: "redis", label: "Gate blocked action → waiting for human", detail: "misalignment=87, written to Redis Stream" }, 3300],
    ];

    mockEntries.forEach(([entry, delay]) =>
      setTimeout(() =>
        setSponsorLog((prev) => [...prev, { ...entry, timestamp: new Date().toISOString() }])
      , delay)
    );

    setTimeout(() => {
      setAgents((prev) =>
        prev.map((a) => a.name === "Candidate Scorer" ? { ...a, status: "flagged" } : a)
      );
      setActiveFlag({
        agentName: "Candidate Scorer",
        toolName: "apply_scoring_rubric",
        payload: MOCK.flagPayload(),
      });
    }, 3300);
  }

  // ── Render ────────────────────────────────────────────────────────────────

  const showNav = screen !== "input";
  const blueprintTopology = blueprint?.topology === "A" ? "supervisor-worker" : "react";

  return (
    <div className="min-h-screen bg-emerald-50">
      {showNav && (
        <div className="fixed top-0 left-0 right-0 z-40 bg-white/90 backdrop-blur border-b-2 border-emerald-200 px-6 py-2 flex items-center gap-2 shadow-sm">
          <Shield size={16} className="text-emerald-600" />
          <span className="text-emerald-900 font-bold text-sm mr-4">SafeAgent</span>
          <NavButton label="Graph" icon={<Play size={12} />}
            active={screen === "scaffold" || screen === "running"}
            onClick={() => blueprint && setScreen(screen === "scaffold" ? "scaffold" : "running")}
          />
          <NavButton label="Proof" icon={<BarChart2 size={12} />}
            active={screen === "proof"}
            onClick={() => proof && setScreen("proof")}
          />
          <NavButton label="Audit" icon={<List size={12} />}
            active={screen === "audit"}
            onClick={() => setScreen("audit")}
          />
          {USE_MOCK && (
            <span className="ml-auto text-xs text-amber-600 bg-amber-100 border border-amber-300 px-2 py-0.5 rounded-full font-medium">
              MOCK MODE
            </span>
          )}
        </div>
      )}

      <div className={showNav ? "pt-12" : ""}>
        {screen === "input" && (
          <InputScreen onSubmit={handlePromptSubmit} loading={loading} />
        )}

        {screen === "topology" && topologyResponse && (
          <TopologyPicker
            response={topologyResponse}
            onSelect={handleTopologySelect}
            loading={loading}
          />
        )}

        {(screen === "scaffold" || screen === "running") && blueprint && (
          <div className="p-8 max-w-7xl mx-auto flex gap-6">
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-2xl font-bold text-emerald-900">
                  {blueprint.topology_name} — {blueprint.agents.length} agents
                </h2>
                <p className="text-emerald-600 text-sm">
                  Predicted cost:{" "}
                  <span className="text-emerald-900 font-mono font-semibold">
                    {(blueprint.prediction.cost_usd * 100).toFixed(1)}¢
                  </span>
                  <span className="text-amber-600 text-xs ml-1 font-medium">PREDICTION</span>
                  {" · "}Latency:{" "}
                  <span className="text-emerald-900 font-mono font-semibold">
                    {blueprint.prediction.latency_sec.toFixed(1)}s
                  </span>
                  <span className="text-amber-600 text-xs ml-1 font-medium">PREDICTION</span>
                  {" · "}Bottleneck:{" "}
                  <span className="text-emerald-700 font-semibold">{blueprint.prediction.bottleneck_agent}</span>
                  {" · "}Confidence:{" "}
                  <span className={`font-semibold ${
                    blueprint.prediction.confidence === "high" ? "text-emerald-600"
                    : blueprint.prediction.confidence === "medium" ? "text-amber-600"
                    : "text-red-500"
                  }`}>{blueprint.prediction.confidence}</span>
                </p>
              </div>
              {screen === "scaffold" && (
                <button
                  onClick={handleRun}
                  className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold px-5 py-2.5 rounded-xl transition-colors shadow-md"
                >
                  <Play size={16} /> Run Agents
                </button>
              )}
              {screen === "running" && (
                <span className="text-emerald-600 text-sm animate-pulse font-medium">Running…</span>
              )}
            </div>

            {/* Agent cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
              {agents.map((a) => (
                <div key={a.name} className={`rounded-2xl border-2 p-3 transition-all shadow-sm ${
                  a.status === "running" ? "border-emerald-500 bg-emerald-50 shadow-emerald-200 shadow-md"
                  : a.status === "done" ? "border-emerald-400 bg-emerald-50"
                  : a.status === "flagged" ? "border-amber-400 bg-amber-50 shadow-amber-200 shadow-md"
                  : "border-emerald-200 bg-white"
                }`}>
                  <div className="font-bold text-emerald-900 text-sm">{a.name}</div>
                  <div className="text-xs text-emerald-500 mt-0.5">
                    {a.model.includes("haiku") ? "Haiku 4.5" : "Sonnet 4.6"}
                  </div>
                  <div className="text-xs text-emerald-400 mt-1">{a.tools.join(", ") || "—"}</div>
                  <div className={`text-xs font-bold mt-2 uppercase tracking-wide ${
                    a.status === "running" ? "text-emerald-600"
                    : a.status === "done" ? "text-emerald-700"
                    : a.status === "flagged" ? "text-amber-600"
                    : "text-emerald-300"
                  }`}>{a.status}</div>
                </div>
              ))}
            </div>

            <AgentGraph agents={agents} topology={blueprintTopology} />
          </div>

          {/* Sponsor activity log — only visible during run */}
          {screen === "running" && (
            <div className="w-80 shrink-0" style={{ height: "calc(100vh - 5rem)", position: "sticky", top: "4rem" }}>
              <SponsorLog entries={sponsorLog} />
            </div>
          )}
          </div>
        )}

        {screen === "proof" && proof && (
          <ProofPanel data={proof} sessionId={SESSION_ID} onExport={handleExport} />
        )}

        {screen === "audit" && (
          <AuditLog events={auditEvents} onExport={handleExport} />
        )}
      </div>

      {/* Flag modal — always on top when gate fires */}
      {activeFlag && (
        <FlagModal
          agentName={activeFlag.agentName}
          toolName={activeFlag.toolName}
          payload={activeFlag.payload}
          builderIntent={prompt}
          onDecide={handleHITL}
        />
      )}
    </div>
  );
}

const MOCK_AUDIT_TAIL: AuditEvent[] = [
  {
    id: "tail-1",
    timestamp: new Date(Date.now() - 800).toISOString(),
    type: "action",
    agent_name: "Email Agent",
    tool_name: "send_email",
    decision: "ALLOW",
  },
];
