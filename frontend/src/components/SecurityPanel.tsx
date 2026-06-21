/**
 * Security Trust Panel — shown on scaffold screen.
 * Lists every active protection with honest status indicators.
 * Only shows protections that are actually implemented.
 */
import { ShieldCheck, Zap, Database, Brain, User, FileText, AlertOctagon } from "lucide-react";

interface Protection {
  icon: React.ReactNode;
  title: string;
  description: string;
  latency: string;
  sponsor: string;
  sponsorColor: string;
  status: "active" | "degraded";
  statusLabel: string;
}

interface Props {
  redisConnected?: boolean;
}

export function SecurityPanel({ redisConnected = true }: Props) {
  const protections: Protection[] = [
    {
      icon: <Zap size={14} />,
      title: "T1 — Prompt Injection Defense",
      description: "Blocks known-dangerous tools (drop_table, bulk_delete, rm_rf) and wildcard params (*,  all, everyone) before any AI call.",
      latency: "<1ms",
      sponsor: "Redis",
      sponsorColor: "text-emerald-600",
      status: "active",
      statusLabel: "Pattern match active",
    },
    {
      icon: <Database size={14} />,
      title: "T2 — Semantic Cache Shield",
      description: "If a similar dangerous action was seen before, the cached BLOCK decision is returned instantly — no re-scoring needed.",
      latency: "~5ms",
      sponsor: "Redis",
      sponsorColor: "text-emerald-600",
      status: redisConnected ? "active" : "degraded",
      statusLabel: redisConnected ? "Cache connected" : "Redis offline — T3 only",
    },
    {
      icon: <Brain size={14} />,
      title: "T3 — Constitutional Scoring",
      description: "Claude Sonnet scores every tool call for misalignment with your stated intent and oversight risk. Score ≥ 70 triggers HITL.",
      latency: "~800ms",
      sponsor: "Anthropic",
      sponsorColor: "text-purple-600",
      status: "active",
      statusLabel: "Sonnet 4.6 active",
    },
    {
      icon: <AlertOctagon size={14} />,
      title: "Output Guardrails",
      description: "After each agent node runs, Claude Haiku checks the output for PII leakage, hallucinations, and injected instructions before passing it downstream.",
      latency: "~200ms",
      sponsor: "Anthropic",
      sponsorColor: "text-purple-600",
      status: "active",
      statusLabel: "Haiku 4.5 active",
    },
    {
      icon: <User size={14} />,
      title: "Human-in-the-Loop (HITL)",
      description: "Any flagged action pauses the entire pipeline and surfaces an approval modal. Nothing runs without your decision.",
      latency: "human",
      sponsor: "SafeAgent",
      sponsorColor: "text-blue-600",
      status: "active",
      statusLabel: "Always on",
    },
    {
      icon: <FileText size={14} />,
      title: "Immutable Audit Trail",
      description: "Every gate decision, HITL action, and output check is appended to a Redis Stream — append-only, tamper-evident.",
      latency: "async",
      sponsor: "Redis",
      sponsorColor: "text-emerald-600",
      status: redisConnected ? "active" : "degraded",
      statusLabel: redisConnected ? "Stream connected" : "Redis offline — in-memory only",
    },
  ];

  return (
    <div className="bg-gray-950 border border-gray-800 rounded-2xl overflow-hidden mt-4">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-800">
        <ShieldCheck size={15} className="text-emerald-400" />
        <span className="text-sm font-bold text-gray-200">Active Security Protections</span>
        <span className="ml-auto text-[10px] bg-emerald-900 text-emerald-400 border border-emerald-800 px-2 py-0.5 rounded-full font-bold">
          {protections.filter(p => p.status === "active").length}/{protections.length} ACTIVE
        </span>
      </div>

      {/* Protection rows */}
      <div className="divide-y divide-gray-900">
        {protections.map((p) => (
          <div key={p.title} className="flex items-start gap-3 px-4 py-3">
            {/* Status dot */}
            <div className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${
              p.status === "active" ? "bg-emerald-500" : "bg-amber-500"
            }`} />

            {/* Content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-gray-300 text-xs font-bold">{p.title}</span>
                <span className={`text-[10px] font-semibold ${p.sponsorColor}`}>
                  {p.icon && <span className="inline-block mr-0.5 align-text-bottom">{p.icon}</span>}
                  {p.sponsor}
                </span>
              </div>
              <p className="text-gray-500 text-[11px] mt-0.5 leading-relaxed">{p.description}</p>
            </div>

            {/* Right side: latency + status */}
            <div className="shrink-0 text-right">
              <div className="text-gray-400 text-[10px] font-mono">{p.latency}</div>
              <div className={`text-[10px] mt-0.5 font-medium ${
                p.status === "active" ? "text-emerald-500" : "text-amber-500"
              }`}>
                {p.statusLabel}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
