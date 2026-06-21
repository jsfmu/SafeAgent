/**
 * Shows the generated LangGraph Python code artifact.
 * Copy button + download button. Shown as a collapsible panel on the scaffold screen.
 */
import { useState } from "react";
import { Code2, Copy, Download, ChevronDown, ChevronUp, Check } from "lucide-react";

interface Props {
  code: string;
  sessionId: string;
  codeUrl: string;
}

export function CodeViewer({ code, sessionId, codeUrl }: Props) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  function handleDownload() {
    window.open(codeUrl, "_blank");
  }

  return (
    <div className="mt-4 bg-gray-950 border border-gray-800 rounded-2xl overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-2 px-4 py-3 text-left hover:bg-gray-900 transition-colors"
      >
        <Code2 size={15} className="text-emerald-400 shrink-0" />
        <span className="text-sm font-bold text-gray-200 flex-1">
          Generated LangGraph Code
        </span>
        <span className="text-xs text-gray-500 mr-2">safe_agent_{sessionId.slice(-8)}.py</span>
        {open ? <ChevronUp size={14} className="text-gray-500" /> : <ChevronDown size={14} className="text-gray-500" />}
      </button>

      {open && (
        <>
          {/* Toolbar */}
          <div className="flex items-center gap-2 px-4 py-2 border-t border-gray-800 border-b border-gray-800 bg-gray-900">
            <span className="text-[10px] text-gray-500 font-mono flex-1">
              Python · LangGraph · runnable as-is
            </span>
            <button
              onClick={handleCopy}
              className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-200 transition-colors"
            >
              {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
              {copied ? "Copied!" : "Copy"}
            </button>
            <button
              onClick={handleDownload}
              className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-200 transition-colors"
            >
              <Download size={12} /> Download
            </button>
          </div>

          {/* Code */}
          <pre className="p-4 text-xs text-gray-300 font-mono overflow-x-auto max-h-96 overflow-y-auto leading-relaxed">
            {code}
          </pre>
        </>
      )}
    </div>
  );
}
