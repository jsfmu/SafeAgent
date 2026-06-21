import { useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  type Node,
  type Edge,
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { AgentNode } from "../types";

const STATUS_BG: Record<AgentNode["status"], string> = {
  idle: "#f0fdf4",
  running: "#d1fae5",
  done: "#a7f3d0",
  flagged: "#fef3c7",
  error: "#fee2e2",
};

const STATUS_BORDER: Record<AgentNode["status"], string> = {
  idle: "#a7f3d0",
  running: "#10b981",
  done: "#059669",
  flagged: "#f59e0b",
  error: "#ef4444",
};

const STATUS_TEXT: Record<AgentNode["status"], string> = {
  idle: "#6ee7b7",
  running: "#059669",
  done: "#065f46",
  flagged: "#d97706",
  error: "#dc2626",
};

interface Props {
  agents: AgentNode[];
  topology: "supervisor-worker" | "react";
}

function makeNodes(agents: AgentNode[]): Node[] {
  return agents.map((a, i) => ({
    id: a.name,
    type: "default",
    position:
      a.role.toLowerCase().includes("orchestrat") || a.role.toLowerCase().includes("coordinate")
        ? { x: 300, y: 0 }
        : { x: i * 220, y: 180 },
    data: {
      label: (
        <div style={{ textAlign: "left", minWidth: 140 }}>
          <div style={{ fontWeight: 700, fontSize: 13, color: "#064e3b" }}>{a.name}</div>
          <div style={{ fontSize: 10, color: "#059669", marginTop: 2 }}>{a.role}</div>
          <div style={{ fontSize: 10, color: "#10b981", marginTop: 4 }}>
            {a.model} · {a.tools.length} tools
          </div>
          <div
            style={{
              fontSize: 10,
              fontWeight: 700,
              marginTop: 4,
              color: STATUS_TEXT[a.status],
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}
          >
            {a.status}
          </div>
        </div>
      ),
    },
    style: {
      background: STATUS_BG[a.status],
      border: `2px solid ${STATUS_BORDER[a.status]}`,
      borderRadius: 12,
      padding: "10px 14px",
      boxShadow:
        a.status === "flagged"
          ? "0 0 16px 4px rgba(245,158,11,0.3)"
          : a.status === "running"
          ? "0 0 12px 2px rgba(16,185,129,0.25)"
          : "0 2px 8px rgba(0,0,0,0.06)",
    },
  }));
}

function makeEdges(agents: AgentNode[], _topology: Props["topology"]): Edge[] {
  const coordinator = agents.find(
    (a) =>
      a.role.toLowerCase().includes("orchestrat") ||
      a.role.toLowerCase().includes("coordinate")
  );
  if (!coordinator) return [];
  const subs = agents.filter((a) => a.name !== coordinator.name);
  return subs.map((a) => ({
    id: `${coordinator.name}-${a.name}`,
    source: coordinator.name,
    target: a.name,
    animated: a.status === "running",
    markerEnd: { type: MarkerType.ArrowClosed, color: "#10b981" },
    style: {
      stroke: a.status === "running" ? "#10b981" : "#a7f3d0",
      strokeWidth: 2,
    },
  }));
}

export function AgentGraph({ agents, topology }: Props) {
  const nodes = useMemo(() => makeNodes(agents), [agents]);
  const edges = useMemo(() => makeEdges(agents, topology), [agents, topology]);

  return (
    <div
      style={{
        height: 380,
        background: "#f0fdf4",
        borderRadius: 16,
        overflow: "hidden",
        border: "2px solid #a7f3d0",
        boxShadow: "0 2px 12px rgba(16,185,129,0.08)",
      }}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#a7f3d0" gap={24} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
