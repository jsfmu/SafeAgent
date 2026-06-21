/**
 * Mic button that drives useDeepgramSTT.
 * When recording stops, calls onTranscript with the full transcript.
 * Shows interim text as a live caption below the button.
 */
import { Mic, MicOff, Loader2 } from "lucide-react";
import { useDeepgramSTT } from "../hooks/useDeepgramSTT";

interface Props {
  onTranscript: (text: string) => void;
  className?: string;
}

export function VoiceInput({ onTranscript, className = "" }: Props) {
  const { transcript, interim, isListening, startListening, stopListening, error } =
    useDeepgramSTT();

  async function toggle() {
    if (isListening) {
      stopListening();
      if (transcript.trim()) onTranscript(transcript.trim());
    } else {
      await startListening();
    }
  }

  return (
    <div className={`flex flex-col items-center gap-1 ${className}`}>
      <button
        type="button"
        onClick={toggle}
        title={isListening ? "Stop recording" : "Speak your agent description"}
        className={`
          flex items-center justify-center w-10 h-10 rounded-full border-2 transition-all shadow-sm
          ${isListening
            ? "bg-red-500 border-red-600 text-white animate-pulse"
            : "bg-white border-emerald-300 text-emerald-600 hover:border-emerald-500 hover:bg-emerald-50"}
        `}
      >
        {isListening ? <MicOff size={18} /> : <Mic size={18} />}
      </button>

      {/* Live caption */}
      {(isListening || interim) && (
        <div className="flex items-center gap-1 text-xs text-emerald-700 max-w-xs text-center">
          {isListening && <Loader2 size={11} className="animate-spin shrink-0" />}
          <span className="italic">{interim || "Listening…"}</span>
        </div>
      )}

      {error && (
        <div className="text-xs text-red-500 max-w-xs text-center">{error}</div>
      )}
    </div>
  );
}
