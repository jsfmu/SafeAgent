/**
 * Shows AgentVerse agents discovered for the current domain.
 * Rendered on the topology screen below the topology cards.
 * Lets user compare existing certified agents vs SafeAgent's scaffold.
 */
import { Globe, Star, Zap } from "lucide-react";

export interface AsiAgent {
  address: string;
  name: string;
  status: string;
  total_interactions: number;
  recent_interactions: number;
  rating: number | null;
  category: string;
  last_updated: string;
}

interface Props {
  agents: AsiAgent[];
  source: "agentverse" | "mock";
  loading: boolean;
}

export function AsiDiscovery({ agents, source, loading }: Props) {
  if (loading) {
    return (
      <div className="mt-6 bg-white border-2 border-blue-200 rounded-2xl p-5 animate-pulse">
        <div className="flex items-center gap-2 mb-3">
          <Globe size={16} className="text-blue-500" />
          <span className="text-sm font-bold text-blue-900">Querying AgentVerse…</span>
        </div>
        <div className="space-y-2">
          {[1, 2].map((i) => (
            <div key={i} className="h-12 bg-blue-50 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  if (!agents.length) return null;

  return (
    <div className="mt-6 bg-white border-2 border-blue-200 rounded-2xl overflow-hidden shadow-sm">
      {/* Header */}
      <div className="bg-blue-50 border-b border-blue-200 px-5 py-3 flex items-center gap-2">
        <Globe size={15} className="text-blue-600" />
        <span className="text-sm font-bold text-blue-900">
          AgentVerse — {agents.length} existing agent{agents.length > 1 ? "s" : ""} found
        </span>
        {source === "mock" && (
          <span className="ml-auto text-[10px] bg-amber-100 text-amber-600 border border-amber-200 px-2 py-0.5 rounded-full font-medium">
            MOCK · add AGENTVERSE_API_KEY for live data
          </span>
        )}
        {source === "agentverse" && (
          <span className="ml-auto text-[10px] bg-blue-100 text-blue-600 border border-blue-200 px-2 py-0.5 rounded-full font-medium">
            LIVE · agentverse.ai
          </span>
        )}
      </div>

      {/* Agent rows */}
      <div className="divide-y divide-blue-50">
        {agents.map((a) => (
          <div key={a.address} className="px-5 py-3 flex items-center gap-4">
            {/* Name + address */}
            <div className="flex-1 min-w-0">
              <div className="font-semibold text-blue-900 text-sm truncate">{a.name}</div>
              <div className="text-[10px] text-blue-400 font-mono truncate">{a.address}</div>
            </div>

            {/* Interactions */}
            <div className="text-center shrink-0">
              <div className="flex items-center gap-1 text-xs text-blue-700 font-mono font-bold">
                <Zap size={11} className="text-blue-400" />
                {a.total_interactions.toLocaleString()}
              </div>
              <div className="text-[10px] text-blue-400">interactions</div>
            </div>

            {/* Rating */}
            <div className="text-center shrink-0 w-16">
              {a.rating != null ? (
                <>
                  <div className="flex items-center justify-center gap-0.5 text-xs font-bold text-amber-600">
                    <Star size={11} className="fill-amber-400 text-amber-400" />
                    {a.rating.toFixed(1)}
                  </div>
                  <div className="text-[10px] text-blue-400">rating</div>
                </>
              ) : (
                <div className="text-[10px] text-blue-300">no rating</div>
              )}
            </div>

            {/* Category badge */}
            <div className="shrink-0">
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                a.category === "fetch-ai"
                  ? "bg-blue-100 text-blue-700 border-blue-200"
                  : "bg-gray-100 text-gray-600 border-gray-200"
              }`}>
                {a.category === "fetch-ai" ? "Fetch.AI" : "Community"}
              </span>
            </div>

            {/* Status */}
            <div className="shrink-0">
              <span className={`w-2 h-2 rounded-full inline-block ${
                a.status === "active" ? "bg-emerald-500" : "bg-gray-300"
              }`} />
            </div>
          </div>
        ))}
      </div>

      {/* Footer note */}
      <div className="bg-blue-50 border-t border-blue-100 px-5 py-2">
        <p className="text-[11px] text-blue-500">
          SafeAgent will score these agents through the constitutional safety gate before incorporating them into your scaffold.
          Agents with lower misalignment scores will be preferred over building from scratch.
        </p>
      </div>
    </div>
  );
}
