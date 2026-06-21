/**
 * Deepgram live STT — streams mic audio via WebSocket, returns real-time transcript.
 * Uses raw WebSocket (no SDK needed) against Deepgram's live transcription endpoint.
 *
 * Usage:
 *   const { transcript, interim, isListening, startListening, stopListening, error } = useDeepgramSTT();
 */
import { useState, useRef, useCallback } from "react";

const DEEPGRAM_WS = "wss://api.deepgram.com/v1/listen";
const API_KEY = import.meta.env.VITE_DEEPGRAM_API_KEY as string | undefined;

interface DeepgramWord {
  word: string;
  punctuated_word?: string;
}

interface DeepgramAlternative {
  transcript: string;
  words?: DeepgramWord[];
}

interface DeepgramResult {
  channel: { alternatives: DeepgramAlternative[] };
  is_final: boolean;
  speech_final: boolean;
}

interface DeepgramMessage {
  type: string;
  channel?: { alternatives: DeepgramAlternative[] };
  is_final?: boolean;
  speech_final?: boolean;
}

export function useDeepgramSTT() {
  const [transcript, setTranscript] = useState("");   // finalized text so far
  const [interim, setInterim] = useState("");          // in-progress words
  const [isListening, setIsListening] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const stopListening = useCallback(() => {
    mediaRecorderRef.current?.stop();
    streamRef.current?.getTracks().forEach((t) => t.stop());
    wsRef.current?.close();
    wsRef.current = null;
    mediaRecorderRef.current = null;
    streamRef.current = null;
    setIsListening(false);
    setInterim("");
  }, []);

  const startListening = useCallback(async () => {
    if (!API_KEY) {
      setError("VITE_DEEPGRAM_API_KEY not set in frontend .env");
      return;
    }
    setError(null);
    setTranscript("");
    setInterim("");

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setError("Microphone access denied");
      return;
    }
    streamRef.current = stream;

    // Open Deepgram WebSocket
    const ws = new WebSocket(`${DEEPGRAM_WS}?model=nova-2&punctuate=true&interim_results=true&endpointing=300`, [
      "token",
      API_KEY,
    ]);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsListening(true);
      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (ws.readyState === WebSocket.OPEN && e.data.size > 0) {
          ws.send(e.data);
        }
      };
      recorder.start(250); // send a chunk every 250ms
    };

    ws.onmessage = (e) => {
      const msg: DeepgramMessage = JSON.parse(e.data);
      if (msg.type !== "Results" || !msg.channel) return;

      const result = msg as unknown as DeepgramResult;
      const alt = result.channel.alternatives[0];
      if (!alt?.transcript) return;

      if (result.is_final) {
        setTranscript((prev) => (prev + " " + alt.transcript).trim());
        setInterim("");
      } else {
        setInterim(alt.transcript);
      }
    };

    ws.onerror = () => setError("Deepgram connection error");
    ws.onclose = () => {
      setIsListening(false);
      setInterim("");
    };
  }, []);

  return { transcript, interim, isListening, startListening, stopListening, error };
}
