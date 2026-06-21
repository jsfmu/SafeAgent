/**
 * Voice HITL — listens for spoken "approve", "modify", or "override"
 * during the safety gate pause and calls onDecide automatically.
 *
 * Usage:
 *   useVoiceHITL({ active: !!activeFlag, onDecide: handleHITL });
 */
import { useEffect, useRef, useCallback } from "react";
import type { HITLDecisionType } from "../types";

const DEEPGRAM_WS = "wss://api.deepgram.com/v1/listen";
const API_KEY = import.meta.env.VITE_DEEPGRAM_API_KEY as string | undefined;

// Keyword → decision mapping (matched anywhere in transcript)
const KEYWORD_MAP: Record<string, HITLDecisionType> = {
  approve:  "approve_fix",
  accept:   "approve_fix",
  confirm:  "approve_fix",
  modify:   "modify",
  edit:     "modify",
  change:   "modify",
  override: "override",
  reject:   "override",
  skip:     "override",
};

interface Options {
  active: boolean;
  onDecide: (decision: HITLDecisionType) => void;
}

export function useVoiceHITL({ active, onDecide }: Options) {
  const wsRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const onDecideRef = useRef(onDecide);
  onDecideRef.current = onDecide;

  const stop = useCallback(() => {
    mediaRecorderRef.current?.stop();
    streamRef.current?.getTracks().forEach((t) => t.stop());
    wsRef.current?.close();
    wsRef.current = null;
    mediaRecorderRef.current = null;
    streamRef.current = null;
  }, []);

  useEffect(() => {
    if (!active || !API_KEY) return;

    let cancelled = false;

    (async () => {
      let stream: MediaStream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      } catch {
        return;
      }
      if (cancelled) { stream.getTracks().forEach((t) => t.stop()); return; }
      streamRef.current = stream;

      const ws = new WebSocket(
        `${DEEPGRAM_WS}?model=nova-2&punctuate=false&interim_results=false&keywords=approve:5,modify:5,override:5,reject:5`,
        ["token", API_KEY]
      );
      wsRef.current = ws;

      ws.onopen = () => {
        const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
        mediaRecorderRef.current = recorder;
        recorder.ondataavailable = (e) => {
          if (ws.readyState === WebSocket.OPEN && e.data.size > 0) ws.send(e.data);
        };
        recorder.start(250);
      };

      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        if (msg.type !== "Results" || !msg.is_final) return;
        const text: string = msg.channel?.alternatives?.[0]?.transcript?.toLowerCase() ?? "";
        for (const [keyword, decision] of Object.entries(KEYWORD_MAP)) {
          if (text.includes(keyword)) {
            onDecideRef.current(decision);
            stop();
            return;
          }
        }
      };
    })();

    return () => {
      cancelled = true;
      stop();
    };
  }, [active, stop]);
}
