import type { Gate, Run, RunEvent, Task, Workflow } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`GET ${path} → ${res.status}`);
  return res.json();
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`POST ${path} → ${res.status}`);
  return res.json();
}

export const api = {
  workflows: {
    list: () => get<Workflow[]>("/api/v1/workflows/"),
    trigger: (id: string, inputs: Record<string, string>) =>
      post<Run>(`/api/v1/workflows/${id}/trigger`, { inputs }),
  },
  runs: {
    list: () => get<Run[]>("/api/v1/runs/"),
    get: (id: string) => get<Run>(`/api/v1/runs/${id}`),
    tasks: (id: string) => get<Task[]>(`/api/v1/runs/${id}/tasks`),
    gates: (id: string) => get<Gate[]>(`/api/v1/runs/${id}/gates`),
    resolveGate: (runId: string, gateId: string, action: "approved" | "rejected", feedback?: string) =>
      post(`/api/v1/runs/${runId}/gates/${gateId}`, { action, feedback }),
  },
};

export function wsUrl(runId: string): string {
  const base = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/^http/, "ws");
  return `${base}/ws/runs/${runId}/events`;
}
