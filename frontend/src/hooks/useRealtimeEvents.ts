import { useEffect, useRef, useCallback } from "react";
import type { AgentStatus, FlagPayload, RunEvent } from "../types";

// Joseph's SSE event types (from INTERFACES.md):
//   run.started | node.started | action.requested | safety.scored
//   action.blocked | human.decided | action.allowed | node.completed
//   run.completed | run.error | heartbeat

interface Handlers {
  onAgentStatus: (agentName: string, status: AgentStatus) => void;
  onFlag: (agentName: string, toolName: string, payload: FlagPayload) => void;
  onRunComplete: () => void;
  onError: (msg: string) => void;
  onRawEvent?: (evt: RunEvent) => void;
}

export function useRealtimeEvents(streamUrl: string | null, handlers: Handlers) {
  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;

  const connect = useCallback(() => {
    if (!streamUrl) return () => {};
    const es = new EventSource(streamUrl);

    es.onmessage = (e) => {
      let evt: RunEvent;
      try {
        evt = JSON.parse(e.data);
      } catch {
        return;
      }
      if (!evt.event_type || evt.event_type === "heartbeat") return;

      const h = handlersRef.current;
      h.onRawEvent?.(evt);
      const agentName = evt.agent_name ?? "";

      switch (evt.event_type) {
        case "node.started":
          h.onAgentStatus(agentName, "running");
          break;

        case "node.completed":
        case "action.allowed":
          h.onAgentStatus(agentName, "done");
          break;

        case "action.blocked": {
          // Gate fired — parse FlagPayload from event data
          const d = evt.data as Record<string, unknown>;
          h.onAgentStatus(agentName, "flagged");
          h.onFlag(agentName, evt.tool_name ?? "", {
            action_id: String(d.action_id ?? ""),
            misalignment: Number(d.misalignment ?? 0),
            oversight: Number(d.oversight ?? 0),
            explanation: String(d.explanation ?? ""),
            fix_tool_params: (d.fix_tool_params as Record<string, unknown>) ?? {},
            fix_explanation: String(d.fix_explanation ?? ""),
            fix_impact_preview: String(d.fix_impact_preview ?? ""),
            fix_type: String(d.fix_type ?? ""),
          });
          break;
        }

        case "run.error":
          h.onError(String((evt.data as Record<string, unknown>).error ?? "Runtime error"));
          break;

        case "run.completed":
          h.onRunComplete();
          break;
      }
    };

    es.onerror = () => {
      // SSE auto-reconnects; silent
    };

    return () => es.close();
  }, [streamUrl]);

  useEffect(() => {
    const cleanup = connect();
    return cleanup;
  }, [connect]);
}
