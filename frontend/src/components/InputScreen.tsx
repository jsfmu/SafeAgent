import { useState } from "react";
import { ChevronRight, Shield } from "lucide-react";

const EXAMPLES = [
  "Hiring agent — screen resumes, score candidates, email shortlist. Merit-based.",
  "Customer support agent — classify tickets, draft replies, escalate critical issues.",
  "Research agent — search web, summarize sources, cite evidence, write report.",
];

interface Props {
  onSubmit: (prompt: string) => void;
  loading: boolean;
}

export function InputScreen({ onSubmit, loading }: Props) {
  const [prompt, setPrompt] = useState("");

  return (
    <div className="min-h-screen bg-emerald-50 flex flex-col items-center justify-center p-8">
      <div className="w-full max-w-2xl">
        <div className="flex items-center gap-3 mb-2">
          <Shield className="text-emerald-600" size={32} />
          <h1 className="text-3xl font-bold text-emerald-900">SafeAgent</h1>
        </div>
        <p className="text-emerald-700 mb-10 text-sm">
          Evidence-backed agent builder with constitutional safety gates.
        </p>

        <label className="block text-emerald-800 text-sm font-semibold mb-2">
          Describe your agent in plain English
        </label>
        <textarea
          className="w-full bg-white border-2 border-emerald-200 rounded-xl p-4 text-emerald-900 placeholder-emerald-300 resize-none focus:outline-none focus:border-emerald-500 text-sm leading-relaxed shadow-sm"
          rows={4}
          placeholder="e.g. Hiring agent — screen resumes, score candidates, email shortlist. Merit-based."
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
        />

        <div className="flex flex-wrap gap-2 mt-3 mb-6">
          {EXAMPLES.map((ex, i) => (
            <button
              key={i}
              onClick={() => setPrompt(ex)}
              className="text-xs bg-emerald-100 hover:bg-emerald-200 text-emerald-700 border border-emerald-200 px-3 py-1 rounded-full transition-colors"
            >
              {ex.split("—")[0].trim()}
            </button>
          ))}
        </div>

        <button
          onClick={() => prompt.trim() && onSubmit(prompt.trim())}
          disabled={!prompt.trim() || loading}
          className="w-full flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-200 disabled:text-emerald-400 text-white font-semibold py-3 px-6 rounded-xl transition-colors shadow-md"
        >
          {loading ? (
            <span className="animate-pulse">Analyzing…</span>
          ) : (
            <>
              Build Agent <ChevronRight size={18} />
            </>
          )}
        </button>
      </div>
    </div>
  );
}
