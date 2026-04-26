"use client";

import "@xyflow/react/dist/style.css";
import {
  Background,
  Controls,
  ReactFlow,
  useEdgesState,
  useNodesState,
} from "@xyflow/react";
import type { Edge, Node } from "@xyflow/react";
import { useMemo } from "react";

export type WorkflowTask = {
  id: string;
  name: string;
  phase: string;
  agent: string;
  depends_on: string[];
  task_type: string;
};

const STATUS_BG: Record<string, string> = {
  running: "#1d4ed8",
  completed: "#166534",
  failed: "#991b1b",
  waiting_human: "#92400e",
  pending: "#18181b",
  skipped: "#09090b",
};

const STATUS_BORDER: Record<string, string> = {
  running: "#3b82f6",
  completed: "#22c55e",
  failed: "#ef4444",
  waiting_human: "#f59e0b",
  pending: "#3f3f46",
  skipped: "#27272a",
};

function TaskNode({ data }: {
  data: { name: string; agent: string; status?: string; task_type: string }
}) {
  const status = data.status ?? "pending";
  return (
    <div style={{
      background: STATUS_BG[status] ?? STATUS_BG.pending,
      border: `1px solid ${STATUS_BORDER[status] ?? STATUS_BORDER.pending}`,
      borderRadius: 6,
      padding: "8px 12px",
      minWidth: 160,
      maxWidth: 200,
    }}>
      <div style={{ color: "#fafafa", fontSize: 12, fontWeight: 600, lineHeight: 1.3 }}>
        {data.name}
      </div>
      {data.task_type === "human_gate" ? (
        <div style={{ color: "#fcd34d", fontSize: 10, marginTop: 3 }}>⏸ human gate</div>
      ) : (
        <div style={{ color: "#a1a1aa", fontSize: 10, marginTop: 3 }}>{data.agent || "—"}</div>
      )}
      {status !== "pending" && (
        <div style={{ color: "#d4d4d8", fontSize: 10, marginTop: 2, opacity: 0.8 }}>{status}</div>
      )}
    </div>
  );
}

const nodeTypes = { task: TaskNode };

export function WorkflowDAG({
  tasks,
  phases,
  taskStatuses = {},
  height = 380,
}: {
  tasks: WorkflowTask[];
  phases: string[];
  taskStatuses?: Record<string, string>;
  height?: number;
}) {
  const { nodes: initialNodes, edges: initialEdges } = useMemo(() => {
    const phaseIndex: Record<string, number> = {};
    phases.forEach((p, i) => { phaseIndex[p] = i; });

    const phaseCounts: Record<string, number> = {};

    const nodes: Node[] = tasks.map((task) => {
      const pi = phaseIndex[task.phase] ?? 0;
      const wi = phaseCounts[task.phase] ?? 0;
      phaseCounts[task.phase] = wi + 1;

      return {
        id: task.id,
        type: "task",
        position: { x: pi * 280, y: wi * 110 },
        data: {
          name: task.name,
          agent: task.agent,
          task_type: task.task_type,
          status: taskStatuses[task.name] ?? taskStatuses[task.id],
        },
      };
    });

    const edges: Edge[] = [];
    tasks.forEach((task) => {
      (task.depends_on ?? []).forEach((dep) => {
        edges.push({
          id: `${dep}->${task.id}`,
          source: dep,
          target: task.id,
          style: { stroke: "#52525b", strokeWidth: 1.5 },
          markerEnd: "arrowclosed",
        });
      });
    });

    return { nodes, edges };
  }, [tasks, phases, taskStatuses]);

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  return (
    <div style={{ height, background: "#09090b", borderRadius: 8, border: "1px solid #27272a" }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        colorMode="dark"
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#1c1c1c" gap={20} />
        <Controls />
      </ReactFlow>
    </div>
  );
}
