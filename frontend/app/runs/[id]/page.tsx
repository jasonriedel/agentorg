import Link from "next/link";
import { api } from "@/lib/api";
import { EventLog } from "@/app/components/EventLog";
import { GateApproval } from "@/app/components/GateApproval";
import { WorkflowDAG } from "@/app/components/WorkflowDAG";
import type { Task, WorkflowDetail } from "@/lib/types";

const TASK_STATUS_COLORS: Record<string, string> = {
  pending: "text-zinc-500",
  running: "text-blue-400",
  completed: "text-green-400",
  failed: "text-red-400",
  skipped: "text-zinc-600",
};

function TaskRow({ task }: { task: Task }) {
  return (
    <div className="border border-zinc-800 rounded p-3 text-sm">
      <div className="flex items-center justify-between mb-1">
        <span className="text-white">{task.name}</span>
        <span className={TASK_STATUS_COLORS[task.status] ?? "text-zinc-400"}>{task.status}</span>
      </div>
      <div className="text-zinc-500 text-xs flex gap-4">
        <span>agent: {task.agent_slug}</span>
        <span>phase: {task.phase}</span>
        {task.token_count > 0 && <span>{task.token_count.toLocaleString()} tokens</span>}
        {task.cost_usd > 0 && <span>${task.cost_usd.toFixed(4)}</span>}
      </div>
      {task.output_summary && (
        <p className="text-zinc-400 text-xs mt-2 line-clamp-3">{task.output_summary}</p>
      )}
      {task.error && (
        <p className="text-red-400 text-xs mt-2">{task.error}</p>
      )}
    </div>
  );
}

export default async function RunDetailPage({ params }: PageProps<"/runs/[id]">) {
  const { id } = await params;
  const [run, tasks, gates] = await Promise.all([
    api.runs.get(id),
    api.runs.tasks(id),
    api.runs.gates(id).catch(() => []),
  ]);

  let workflowDetail: WorkflowDetail | null = null;
  try {
    workflowDetail = await api.workflows.get(run.workflow_slug);
  } catch {
    // workflow detail is optional for the DAG
  }

  const taskStatusMap: Record<string, string> = {};
  tasks.forEach((t) => { taskStatusMap[t.name] = t.status; });

  const pendingGates = gates.filter((g) => g.status === "waiting");

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/runs" className="text-zinc-500 hover:text-white text-sm">← Runs</Link>
        <span className="text-zinc-700">/</span>
        <span className="text-zinc-300 text-sm">{run.workflow_slug}</span>
        <span className="text-zinc-600 text-xs">{run.id.slice(0, 8)}</span>
      </div>

      {/* Run summary */}
      <div className="border border-zinc-800 rounded p-4 grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
        <div>
          <p className="text-zinc-500 text-xs mb-1">Status</p>
          <p className={run.status === "completed" ? "text-green-400" : run.status === "failed" ? "text-red-400" : run.status === "waiting_human" ? "text-yellow-400" : "text-blue-400"}>
            {run.status}
          </p>
        </div>
        <div>
          <p className="text-zinc-500 text-xs mb-1">Phase</p>
          <p className="text-zinc-300">{run.phase ?? "—"}</p>
        </div>
        <div>
          <p className="text-zinc-500 text-xs mb-1">Cost</p>
          <p className="text-zinc-300">${run.cost_usd.toFixed(4)}</p>
        </div>
        <div>
          <p className="text-zinc-500 text-xs mb-1">Tokens</p>
          <p className="text-zinc-300">{run.token_count.toLocaleString()}</p>
        </div>
      </div>

      {/* Human gates waiting for approval */}
      {pendingGates.length > 0 && (
        <div className="space-y-2">
          <h2 className="text-sm font-semibold text-white">Waiting for Approval</h2>
          {pendingGates.map((gate) => (
            <GateApproval key={gate.id} runId={run.id} gate={gate} />
          ))}
        </div>
      )}

      {run.error && (
        <div className="border border-red-800 bg-red-950/20 rounded p-3 text-sm text-red-300">
          {run.error}
        </div>
      )}

      {/* Workflow DAG with live status */}
      {workflowDetail && workflowDetail.definition.tasks.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-white mb-3">Execution Graph</h2>
          <WorkflowDAG
            tasks={workflowDetail.definition.tasks}
            phases={workflowDetail.definition.phases}
            taskStatuses={taskStatusMap}
            height={320}
          />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Tasks */}
        <div className="space-y-2">
          <h2 className="text-sm font-semibold text-white">Tasks ({tasks.length})</h2>
          {tasks.length === 0 ? (
            <p className="text-zinc-600 text-xs">No tasks yet.</p>
          ) : (
            tasks.map((task) => <TaskRow key={task.id} task={task} />)
          )}
        </div>

        {/* Live event log */}
        <EventLog runId={run.id} />
      </div>
    </div>
  );
}
