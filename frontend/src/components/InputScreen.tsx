import { useState, useEffect, useRef } from "react";
import { ChevronRight, Shield, AlertTriangle } from "lucide-react";
import { UseCaseGallery } from "./UseCaseGallery";
import { api } from "../api/client";

interface Props {
  onSubmit: (prompt: string) => void;
  loading: boolean;
}

export function InputScreen({ onSubmit, loading }: Props) {
  const [prompt, setPrompt] = useState("");
  const [keywordWarning, setKeywordWarning] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!prompt.trim()) { setKeywordWarning(null); return; }
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await fetch(`${api.base()}/voice/keywords`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: prompt }),
        });
        if (res.ok) {
          const data = await res.json();
          setKeywordWarning(data.warning ?? null);
        }
      } catch { /* backend not running */ }
    }, 600);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [prompt]);

  return (
    <div className="min-h-screen bg-emerald-50 flex flex-col items-center justify-center p-8">
      <div className="w-full max-w-3xl">
        <div className="flex items-center gap-3 mb-2">
          <Shield className="text-emerald-600" size={32} />
          <h1 className="text-3xl font-bold text-emerald-900">SafeAgent</h1>
        </div>
        <p className="text-emerald-700 mb-8 text-sm">
          Evidence-backed agent builder with constitutional safety gates.
        </p>

        {/* Use case gallery */}
        <UseCaseGallery onSelect={(p) => setPrompt(p)} />

        {/* Custom prompt */}
        <label className="block text-emerald-800 text-sm font-semibold mb-2">
          Or describe your own agent in plain English
        </label>
        <textarea
          className="w-full bg-white border-2 border-emerald-200 rounded-xl p-4 text-emerald-900 placeholder-emerald-300 resize-none focus:outline-none focus:border-emerald-500 text-sm leading-relaxed shadow-sm"
          rows={3}
          placeholder="e.g. Hiring agent — screen resumes, score candidates, email shortlist. Merit-based."
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
        />

        {keywordWarning && (
          <div className="mt-2 flex items-start gap-2 bg-amber-50 border border-amber-300 rounded-lg px-3 py-2 text-xs text-amber-800">
            <AlertTriangle size={14} className="text-amber-500 shrink-0 mt-0.5" />
            <span>{keywordWarning}</span>
          </div>
        )}

        <button
          onClick={() => prompt.trim() && onSubmit(prompt.trim())}
          disabled={!prompt.trim() || loading}
          className="w-full mt-4 flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-200 disabled:text-emerald-400 text-white font-semibold py-3 px-6 rounded-xl transition-colors shadow-md"
        >
          {loading ? (
            <span className="animate-pulse">Analyzing…</span>
          ) : (
            <>Build Agent <ChevronRight size={18} /></>
          )}
        </button>
      </div>
    </div>
  );
}
