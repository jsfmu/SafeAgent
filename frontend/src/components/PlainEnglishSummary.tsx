/**
 * Translates a GraphBlueprint into a plain English "What this agent does" card.
 * No jargon — written for someone who has never used an agent builder before.
 */
import { ChevronRight, AlertTriangle, Users } from "lucide-react";
import type { GraphBlueprint } from "../types";

interface Props {
  blueprint: GraphBlueprint;
  builderIntent: string;
  riskProfile?: string;
}

function stepVerb(tools: string[]): string {
  const t = tools[0]?.toLowerCase() ?? "";
  if (t.includes("parse") || t.includes("read") || t.includes("extract")) return "reads and extracts data from";
  if (t.includes("score") || t.includes("rank") || t.includes("eval")) return "scores and ranks";
  if (t.includes("email") || t.includes("send") || t.includes("notify")) return "sends a notification about";
  if (t.includes("search") || t.includes("fetch") || t.includes("web")) return "searches the web for";
  if (t.includes("classify") || t.includes("label") || t.includes("tag")) return "classifies and labels";
  if (t.includes("summarize") || t.includes("summary")) return "summarises";
  if (t.includes("write") || t.includes("draft") || t.includes("generat")) return "drafts a response for";
  if (t.includes("delete") || t.includes("remove")) return "removes";
  return "processes";
}

function agentSentence(name: string, _role: string, tools: string[]): string {
  const verb = stepVerb(tools);
  const toolLabel = tools[0]?.replace(/_/g, " ") ?? "input";
  return `${name} ${verb} ${toolLabel}.`;
}

export function PlainEnglishSummary({ blueprint, builderIntent, riskProfile }: Props) {
  const agents = blueprint.agents;

  const hasDelete = agents.some(a =>
    a.tools.some(t => t.includes("delete") || t.includes("drop") || t.includes("remove"))
  );
  const hasExternalSend = agents.some(a =>
    a.tools.some(t =>
      t.includes("email") || t.includes("send") || t.includes("notify") ||
      t.includes("post") || t.includes("sms") || t.includes("page") ||
      t.includes("ehr") || t.includes("write") || t.includes("roster")
    )
  );

  // Prefer the classifier's risk_profile string, fall back to tool heuristics
  function deriveRiskLevel(): "low" | "medium" | "high" {
    if (riskProfile) {
      const lower = riskProfile.toLowerCase();
      if (lower.startsWith("high")) return "high";
      if (lower.startsWith("medium") || lower.startsWith("med")) return "medium";
      if (lower.startsWith("low")) return "low";
    }
    return hasDelete ? "high" : hasExternalSend ? "medium" : "low";
  }

  const riskLevel = deriveRiskLevel();

  const riskStyleMap = {
    low:    { bg: "bg-emerald-50 border-emerald-200", text: "text-emerald-700", badge: "bg-emerald-100 text-emerald-700 border-emerald-300", label: "Low Risk" },
    medium: { bg: "bg-amber-50 border-amber-200",     text: "text-amber-800",   badge: "bg-amber-100 text-amber-700 border-amber-300",     label: "Medium Risk" },
    high:   { bg: "bg-red-50 border-red-200",         text: "text-red-800",     badge: "bg-red-100 text-red-700 border-red-300",           label: "High Risk" },
  };
  const riskStyles = riskStyleMap[riskLevel] ?? riskStyleMap.low;

  return (
    <div className={`border-2 rounded-2xl p-5 mb-5 ${riskStyles.bg}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Users size={16} className={riskStyles.text} />
          <span className={`text-sm font-bold ${riskStyles.text}`}>What this agent does</span>
        </div>
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${riskStyles.badge}`}>
          {riskStyles.label}
        </span>
      </div>

      {/* Builder intent */}
      <p className={`text-xs mb-3 italic ${riskStyles.text} opacity-70`}>
        Your goal: "{builderIntent.slice(0, 120)}{builderIntent.length > 120 ? "…" : ""}"
      </p>

      {/* Step-by-step flow */}
      <div className="space-y-2 mb-3">
        {agents.map((agent, i) => (
          <div key={agent.name} className="flex items-start gap-2">
            <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5 ${riskStyles.badge} border`}>
              {i + 1}
            </div>
            <div>
              <span className={`text-xs font-semibold ${riskStyles.text}`}>{agent.name}</span>
              <span className={`text-xs ${riskStyles.text} opacity-80`}>
                {" — "}{agentSentence(agent.name, agent.role ?? "", agent.tools)}
              </span>
            </div>
            {i < agents.length - 1 && (
              <ChevronRight size={12} className={`${riskStyles.text} opacity-40 mt-1 shrink-0`} />
            )}
          </div>
        ))}
      </div>

      {/* Human checkpoint notice */}
      <div className="flex items-start gap-2 bg-white/60 rounded-xl p-3 border border-white">
        <AlertTriangle size={13} className="text-amber-500 shrink-0 mt-0.5" />
        <p className="text-xs text-gray-700 leading-relaxed">
          <span className="font-semibold">You stay in control.</span>{" "}
          {hasExternalSend
            ? "Before any email or notification is sent, the safety gate will check the action and pause for your approval if anything looks risky."
            : "The safety gate checks every action before it runs. If anything looks risky or misaligned with your goal, it pauses and asks you to decide."}
          {" "}Every decision is logged to the audit trail.
        </p>
      </div>
    </div>
  );
}
