import { useState } from "react";
import { AlertTriangle, CheckCircle, Edit3, SkipForward } from "lucide-react";
import type { FlagPayload, HITLDecisionType } from "../types";

interface Props {
  agentName: string;
  toolName: string;
  payload: FlagPayload;
  builderIntent: string;
  onDecide: (decision: HITLDecisionType, modifiedParams?: Record<string, unknown>) => void;
}

function ScoreMeter({ label, value, barColor, textColor }: {
  label: string; value: number; barColor: string; textColor: string;
}) {
  return (
    <div>
      <div className="flex justify-between mb-1">
        <span className="text-xs text-emerald-600 uppercase tracking-wide font-semibold">{label}</span>
        <span className={`text-2xl font-bold font-mono ${textColor}`}>{value}</span>
      </div>
      <div className="w-full bg-emerald-100 rounded-full h-3">
        <div className="h-3 rounded-full transition-all duration-700" style={{ width: `${value}%`, backgroundColor: barColor }} />
      </div>
    </div>
  );
}

export function FlagModal({ agentName, toolName, payload, builderIntent, onDecide }: Props) {
  const [mode, setMode] = useState<"view" | "edit">("view");
  const [_editedFix] = useState(payload.fix_explanation);
  const [editedParams, setEditedParams] = useState(
    JSON.stringify(payload.fix_tool_params, null, 2)
  );

  const isHigh = payload.misalignment >= 70 || payload.oversight >= 70;

  function handleApprove() {
    onDecide("approve_fix");
  }

  function handleModify() {
    let params: Record<string, unknown> | undefined;
    try {
      params = JSON.parse(editedParams);
    } catch {
      params = payload.fix_tool_params;
    }
    onDecide("modify", params);
  }

  return (
    <div className="fixed inset-0 z-50 bg-emerald-900/40 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white border-2 border-amber-400 rounded-2xl w-full max-w-2xl shadow-2xl shadow-amber-200/60 overflow-hidden">
        {/* Header */}
        <div className="bg-amber-50 border-b-2 border-amber-200 px-6 py-4 flex items-center gap-3">
          <AlertTriangle className="text-amber-500 shrink-0" size={22} />
          <div className="flex-1">
            <div className="font-bold text-amber-900 text-lg">Safety Flag Intercepted</div>
            <div className="text-xs text-amber-700 mt-0.5">
              {agentName} ·{" "}
              <code className="bg-amber-100 px-1 rounded text-amber-800">{toolName}</code>
              <span className="ml-3 text-amber-500 font-mono">
                action_id: {payload.action_id}
              </span>
            </div>
          </div>
          <div className={`text-xs font-bold px-2.5 py-1 rounded-full border ${
            isHigh
              ? "bg-red-100 text-red-700 border-red-300"
              : "bg-amber-100 text-amber-700 border-amber-300"
          }`}>
            {isHigh ? "HIGH RISK" : "WARN"}
          </div>
        </div>

        <div className="p-6 space-y-5">
          {/* Score meters */}
          <div className="grid grid-cols-2 gap-4">
            <ScoreMeter label="Misalignment" value={payload.misalignment} barColor="#ef4444" textColor="text-red-600" />
            <ScoreMeter label="Oversight" value={payload.oversight} barColor="#f59e0b" textColor="text-amber-600" />
          </div>

          {/* Explanation */}
          <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4">
            <div className="text-xs text-emerald-600 uppercase tracking-wide font-semibold mb-2">Why Claude flagged this</div>
            <p className="text-sm text-emerald-900 leading-relaxed">{payload.explanation}</p>
          </div>

          {/* Intent vs what agent tried */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3">
              <div className="text-xs text-emerald-600 uppercase tracking-wide font-semibold mb-1">Your intent</div>
              <p className="text-xs text-emerald-800 leading-relaxed">{builderIntent}</p>
            </div>
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-3">
              <div className="text-xs text-amber-600 uppercase tracking-wide font-semibold mb-1">Fix type</div>
              <code className="text-xs text-amber-800 font-mono">{payload.fix_type}</code>
              <p className="text-xs text-amber-700 mt-1 leading-relaxed">{payload.fix_impact_preview}</p>
            </div>
          </div>

          {/* Auto-fix */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="text-xs text-emerald-600 uppercase tracking-wide font-semibold">
                Claude's safer alternative
              </div>
              <button
                onClick={() => setMode(mode === "edit" ? "view" : "edit")}
                className="text-xs text-emerald-600 hover:text-emerald-500 flex items-center gap-1 font-medium"
              >
                <Edit3 size={12} /> {mode === "edit" ? "Done" : "Modify params"}
              </button>
            </div>
            <div className="bg-emerald-50 border-2 border-emerald-300 rounded-xl p-3 text-sm text-emerald-800 leading-relaxed mb-2">
              {payload.fix_explanation}
            </div>
            {mode === "edit" && (
              <textarea
                className="w-full bg-white border-2 border-emerald-400 rounded-xl p-3 text-xs text-emerald-900 font-mono resize-none focus:outline-none focus:border-emerald-500"
                rows={4}
                value={editedParams}
                onChange={(e) => setEditedParams(e.target.value)}
                placeholder="Edit fixed tool params as JSON…"
              />
            )}
          </div>

          {/* HITL Actions */}
          <div className="grid grid-cols-3 gap-3 pt-1">
            <button
              onClick={handleApprove}
              className="flex flex-col items-center gap-1 bg-emerald-500 hover:bg-emerald-600 text-white rounded-2xl py-4 px-3 transition-colors shadow-sm"
            >
              <CheckCircle size={22} />
              <span className="font-bold text-sm">Approve Fix</span>
              <span className="text-xs text-emerald-100 text-center">Use Claude's safer version</span>
            </button>
            <button
              onClick={() => { setMode("edit"); if (mode === "edit") handleModify(); }}
              className="flex flex-col items-center gap-1 bg-blue-500 hover:bg-blue-600 text-white rounded-2xl py-4 px-3 transition-colors shadow-sm"
            >
              <Edit3 size={22} />
              <span className="font-bold text-sm">{mode === "edit" ? "Submit Edit" : "Modify"}</span>
              <span className="text-xs text-blue-100 text-center">Edit params then submit</span>
            </button>
            <button
              onClick={() => onDecide("override")}
              className="flex flex-col items-center gap-1 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-2xl py-4 px-3 transition-colors shadow-sm"
            >
              <SkipForward size={22} />
              <span className="font-bold text-sm">Override</span>
              <span className="text-xs text-gray-500 text-center">Run original (logged)</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
