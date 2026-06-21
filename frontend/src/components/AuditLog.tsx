import type { AuditEvent } from "../types";
import { Download, Shield, Zap, User, Wrench } from "lucide-react";

const TYPE_ICON: Record<AuditEvent["type"], React.ReactNode> = {
  gate: <Shield size={14} className="text-amber-500" />,
  action: <Zap size={14} className="text-emerald-500" />,
  hitl: <User size={14} className="text-blue-500" />,
  scaffold: <Wrench size={14} className="text-purple-500" />,
};

const DECISION_COLOR: Record<string, string> = {
  ALLOW: "text-emerald-600 bg-emerald-100 border-emerald-300",
  WARN: "text-amber-700 bg-amber-100 border-amber-300",
  BLOCK: "text-red-600 bg-red-100 border-red-300",
};

interface Props {
  events: AuditEvent[];
  onExport: () => void;
}

export function AuditLog({ events, onExport }: Props) {
  return (
    <div className="min-h-screen bg-emerald-50 p-8">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold text-emerald-900">Audit Log</h2>
            <p className="text-emerald-600 text-sm">
              Redis Streams — append-only, every decision timestamped.
            </p>
          </div>
          <button
            onClick={onExport}
            className="flex items-center gap-2 bg-white border-2 border-emerald-300 hover:bg-emerald-50 text-emerald-700 text-sm px-4 py-2 rounded-xl transition-colors font-medium shadow-sm"
          >
            <Download size={14} /> safe-agent-blueprint.json
          </button>
        </div>

        <div className="space-y-2">
          {events.map((ev) => (
            <div
              key={ev.id}
              className="bg-white border-2 border-emerald-100 hover:border-emerald-200 rounded-xl px-4 py-3 flex items-start gap-3 transition-colors shadow-sm"
            >
              <div className="mt-0.5 shrink-0">{TYPE_ICON[ev.type]}</div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-emerald-900 text-sm font-semibold">{ev.agent_name}</span>
                  {ev.tool_name && (
                    <code className="text-xs bg-emerald-50 border border-emerald-200 text-emerald-700 px-1.5 py-0.5 rounded">
                      {ev.tool_name}
                    </code>
                  )}
                  {ev.decision && (
                    <span
                      className={`text-xs font-bold px-2 py-0.5 rounded-full border ${
                        DECISION_COLOR[ev.decision] ?? "text-gray-600 bg-gray-100 border-gray-300"
                      }`}
                    >
                      {ev.decision}
                    </span>
                  )}
                  {ev.hitl_action && (
                    <span className="text-xs font-bold text-blue-600 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded-full uppercase">
                      HITL: {ev.hitl_action}
                    </span>
                  )}
                  {ev.score !== undefined && (
                    <span className="text-xs text-amber-600 font-medium">score={ev.score}</span>
                  )}
                </div>
              </div>
              <div className="text-xs text-emerald-400 shrink-0 font-mono">
                {new Date(ev.timestamp).toLocaleTimeString()}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
