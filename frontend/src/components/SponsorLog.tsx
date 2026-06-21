import { useEffect, useRef } from "react";
import type { RunEvent } from "../types";

export type Sponsor = "anthropic" | "redis" | "arize";

export interface LogEntry {
  id: string;
  timestamp: string;
  sponsor: Sponsor;
  label: string;
  detail?: string;
  tier?: 1 | 2 | 3;
}

// Maps a raw SSE RunEvent to zero, one, or two LogEntry objects
export function eventToLogEntries(evt: RunEvent): LogEntry[] {
  const ts = new Date().toISOString();
  const d = evt.data as Record<string, unknown>;
  const agent = evt.agent_name ?? "";
  const tool = evt.tool_name ?? "";
  const id = `${evt.timestamp_ms}-${Math.random().toString(36).slice(2, 7)}`;

  switch (evt.event_type) {
    case "node.started":
      return [{
        id,
        timestamp: ts,
        sponsor: "anthropic",
        label: `Claude starting ${agent}`,
        detail: tool ? `tool: ${tool}` : undefined,
      }];

    case "safety.scored": {
      const tier = Number(d.tier ?? 3) as 1 | 2 | 3;
      const decision = String(d.decision ?? "");
      const cacheHit = Boolean(d.cache_hit);
      const misalignment = d.misalignment != null ? Number(d.misalignment) : null;
      const oversight = d.oversight != null ? Number(d.oversight) : null;
      const latency = d.latency_ms != null ? `${d.latency_ms}ms` : "";

      if (tier === 1) {
        return [{
          id,
          timestamp: ts,
          sponsor: "redis",
          label: `T1 Guardrails: ${decision} ${latency}`,
          detail: `pattern match on ${tool}`,
          tier: 1,
        }];
      }
      if (tier === 2) {
        return [{
          id,
          timestamp: ts,
          sponsor: "redis",
          label: cacheHit
            ? `T2 Cache HIT — skipped Claude ${latency}`
            : `T2 Semantic routing → T3 ${latency}`,
          detail: `tool: ${tool}`,
          tier: 2,
        }];
      }
      // tier 3 — Claude scored
      return [{
        id,
        timestamp: ts,
        sponsor: "anthropic",
        label: `T3 Sonnet scored: misalignment=${misalignment ?? "—"} oversight=${oversight ?? "—"}`,
        detail: `decision: ${decision} ${latency}`,
        tier: 3,
      }];
    }

    case "action.blocked":
      return [{
        id,
        timestamp: ts,
        sponsor: "redis",
        label: "Gate blocked action → waiting for human",
        detail: `misalignment=${d.misalignment ?? "—"}, written to Redis Stream`,
      }];

    case "human.decided":
      return [{
        id,
        timestamp: ts,
        sponsor: "redis",
        label: `Human decision logged: ${String(d.decision ?? "")}`,
        detail: "appended to Redis Stream audit log",
      }];

    case "action.allowed":
      return [{
        id,
        timestamp: ts,
        sponsor: "redis",
        label: `Action allowed — event written to Stream`,
        detail: String(d.note ?? ""),
      }];

    case "node.completed":
      return [
        {
          id: id + "-a",
          timestamp: ts,
          sponsor: "anthropic",
          label: `${agent} completed`,
          detail: String(d.result_summary ?? ""),
        },
        {
          id: id + "-b",
          timestamp: ts,
          sponsor: "arize",
          label: `Trace emitted for ${agent}`,
          detail: "tokens · latency · cost → Phoenix",
        },
      ];

    case "run.completed":
      return [{
        id,
        timestamp: ts,
        sponsor: "arize",
        label: "Run complete — all traces exported to Phoenix",
        detail: `view at ${import.meta.env.VITE_PHOENIX_URL ?? "localhost:6006"}`,
      }];

    default:
      return [];
  }
}

const SPONSOR_STYLES: Record<Sponsor, { badge: string; dot: string; border: string }> = {
  anthropic: {
    badge: "bg-purple-100 text-purple-700 border border-purple-300",
    dot: "bg-purple-500",
    border: "border-l-purple-400",
  },
  redis: {
    badge: "bg-emerald-100 text-emerald-700 border border-emerald-300",
    dot: "bg-emerald-500",
    border: "border-l-emerald-400",
  },
  arize: {
    badge: "bg-blue-100 text-blue-700 border border-blue-300",
    dot: "bg-blue-500",
    border: "border-l-blue-400",
  },
};

const SPONSOR_LABEL: Record<Sponsor, string> = {
  anthropic: "Anthropic",
  redis: "Redis",
  arize: "Arize",
};

const TIER_PILL: Record<number, string> = {
  1: "bg-red-100 text-red-600 border border-red-200",
  2: "bg-amber-100 text-amber-600 border border-amber-200",
  3: "bg-purple-100 text-purple-600 border border-purple-200",
};

interface Props {
  entries: LogEntry[];
}

export function SponsorLog({ entries }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries.length]);

  return (
    <div className="flex flex-col h-full bg-gray-950 rounded-2xl border border-gray-800 overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-800 shrink-0">
        <span className="text-xs font-bold text-gray-400 uppercase tracking-widest">Live Sponsor Activity</span>
        <span className="ml-auto flex gap-2">
          {(["anthropic", "redis", "arize"] as Sponsor[]).map((s) => (
            <span key={s} className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${SPONSOR_STYLES[s].badge}`}>
              {SPONSOR_LABEL[s]}
            </span>
          ))}
        </span>
      </div>

      {/* Entries */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-1.5 font-mono text-xs">
        {entries.length === 0 && (
          <div className="text-gray-600 text-center pt-6">Waiting for run to start…</div>
        )}
        {entries.map((entry) => {
          const s = SPONSOR_STYLES[entry.sponsor];
          return (
            <div
              key={entry.id}
              className={`flex items-start gap-2 border-l-2 pl-2 py-1 ${s.border}`}
            >
              {/* Dot */}
              <div className={`w-1.5 h-1.5 rounded-full mt-1 shrink-0 ${s.dot}`} />

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${s.badge}`}>
                    {SPONSOR_LABEL[entry.sponsor]}
                  </span>
                  {entry.tier !== undefined && (
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${TIER_PILL[entry.tier]}`}>
                      T{entry.tier}
                    </span>
                  )}
                  <span className="text-gray-200">{entry.label}</span>
                </div>
                {entry.detail && (
                  <div className="text-gray-500 mt-0.5 text-[10px]">{entry.detail}</div>
                )}
              </div>

              {/* Time */}
              <div className="text-gray-600 shrink-0 text-[10px]">
                {new Date(entry.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
              </div>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
