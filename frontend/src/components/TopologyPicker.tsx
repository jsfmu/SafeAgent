import { useState } from "react";
import { ChevronDown, ChevronUp, CheckCircle2, Circle } from "lucide-react";
import type { TopologyOption, TopologyResponse } from "../types";

interface Props {
  response: TopologyResponse;
  onSelect: (opt: TopologyOption) => void;
  loading: boolean;
}

export function TopologyPicker({ response, onSelect, loading }: Props) {
  const [selectedId, setSelectedId] = useState<"A" | "B" | null>(null);
  const [showThinking, setShowThinking] = useState(false);
  const options = [response.option_a, response.option_b];

  return (
    <div className="min-h-screen bg-emerald-50 p-8">
      <div className="max-w-4xl mx-auto">
        <h2 className="text-2xl font-bold text-emerald-900 mb-1">Choose Architecture</h2>
        <p className="text-emerald-600 text-sm mb-2">
          Claude Sonnet + Extended Thinking reasoned about two topologies.
        </p>

        {/* Thinking summary badge */}
        <div className="inline-flex items-center gap-2 bg-emerald-100 border border-emerald-300 rounded-full px-3 py-1 text-xs text-emerald-700 font-medium mb-4">
          💡 {response.thinking_summary}
        </div>

        {/* Full reasoning chain */}
        <button
          onClick={() => setShowThinking(!showThinking)}
          className="flex items-center gap-2 text-emerald-600 text-xs mb-6 hover:text-emerald-500 transition-colors font-medium"
        >
          {showThinking ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          {showThinking ? "Hide" : "Show"} extended thinking chain
        </button>
        {showThinking && (
          <div className="bg-white border-2 border-emerald-200 rounded-xl p-4 mb-6 text-emerald-800 text-xs leading-relaxed font-mono whitespace-pre-wrap shadow-sm max-h-48 overflow-y-auto">
            {options.find(o => o.recommended)?.reasoning_chain ?? options[0].reasoning_chain}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          {options.map((opt) => {
            const sel = selectedId === opt.id;
            return (
              <button
                key={opt.id}
                onClick={() => setSelectedId(opt.id)}
                className={`text-left rounded-2xl border-2 p-5 transition-all shadow-sm relative ${
                  sel
                    ? "border-emerald-500 bg-emerald-100 shadow-emerald-200 shadow-md"
                    : "border-emerald-200 bg-white hover:border-emerald-400 hover:shadow-md"
                }`}
              >
                {opt.recommended && (
                  <span className="absolute top-3 right-10 text-xs bg-emerald-500 text-white px-2 py-0.5 rounded-full font-semibold">
                    Recommended
                  </span>
                )}
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <span className="text-xs text-emerald-400 font-mono mr-2">Option {opt.id}</span>
                    <h3 className="font-bold text-emerald-900 inline">{opt.name}</h3>
                  </div>
                  {sel
                    ? <CheckCircle2 size={18} className="text-emerald-500 shrink-0 mt-0.5" />
                    : <Circle size={18} className="text-emerald-300 shrink-0 mt-0.5" />}
                </div>
                <p className="text-emerald-700 text-xs mb-4">{opt.description}</p>

                <div className="flex gap-4 mb-4">
                  <div>
                    <div className="text-xs text-emerald-500 uppercase tracking-wide font-medium">Est. Cost</div>
                    <div className="text-emerald-900 font-mono font-bold">
                      {(opt.estimated_cost_usd_low * 100).toFixed(0)}–{(opt.estimated_cost_usd_high * 100).toFixed(0)}¢
                      <span className="text-xs text-amber-600 ml-1 font-normal">PREDICTION</span>
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-emerald-500 uppercase tracking-wide font-medium">Est. Latency</div>
                    <div className="text-emerald-900 font-mono font-bold">
                      {opt.estimated_latency_sec.toFixed(1)}s
                      <span className="text-xs text-amber-600 ml-1 font-normal">PREDICTION</span>
                    </div>
                  </div>
                </div>

                <div className="space-y-1">
                  {opt.tradeoffs_pro.map((p, i) => (
                    <div key={i} className="text-xs text-emerald-600 font-medium">✓ {p}</div>
                  ))}
                  {opt.tradeoffs_con.map((c, i) => (
                    <div key={i} className="text-xs text-red-400">✗ {c}</div>
                  ))}
                </div>
              </button>
            );
          })}
        </div>

        <button
          onClick={() => {
            const opt = options.find(o => o.id === selectedId);
            if (opt) onSelect(opt);
          }}
          disabled={!selectedId || loading}
          className="w-full bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-200 disabled:text-emerald-400 text-white font-semibold py-3 px-6 rounded-xl transition-colors shadow-md"
        >
          {loading ? "Scaffolding agents…" : `Build with Option ${selectedId ?? "…"} →`}
        </button>
      </div>
    </div>
  );
}
