export type RunStatus = "pending" | "running" | "waiting_human" | "completed" | "failed" | "cancelled";

export interface Agent {
  id: string;
  slug: string;
  name: string;
  current_soul_version: string | null;
  created_at: string;
  updated_at: string;
}

export interface SoulVersion {
  id: string;
  version: string;
  soul_md: string;
  commit_sha: string | null;
  pr_url: string | null;
  is_active: boolean;
  created_at: string;
}
export type TaskStatus = "pending" | "running" | "completed" | "failed" | "skipped";

export interface WorkflowTask {
  id: string;
  name: string;
  phase: string;
  agent: string;
  depends_on: string[];
  task_type: string;
}

export interface Workflow {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  is_active: boolean;
}

export interface WorkflowDetail extends Workflow {
  definition: { phases: string[]; tasks: WorkflowTask[] };
  definition_yaml: string;
}

export interface Run {
  id: string;
  workflow_id: string;
  workflow_slug: string;
  status: RunStatus;
  phase: string | null;
  cost_usd: number;
  token_count: number;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
  created_at: string;
}

export interface Task {
  id: string;
  agent_slug: string;
  name: string;
  phase: string;
  status: TaskStatus;
  output_summary: string | null;
  full_output: string | null;
  token_count: number;
  cost_usd: number;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
}

export interface RunEvent {
  id?: string;
  run_id: string;
  task_id: string | null;
  event_type: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface Gate {
  id: string;
  name: string;
  message: string;
  status: "waiting" | "approved" | "rejected";
  response: { action: string; feedback?: string } | null;
  created_at: string;
  resolved_at: string | null;
}
