import Link from "next/link";
import { api } from "@/lib/api";
import type { Run } from "@/lib/types";

const STATUS_COLORS: Record<string, string> = {
  pending: "text-zinc-400",
  running: "text-blue-400",
  waiting_human: "text-yellow-400",
  completed: "text-green-400",
  failed: "text-red-400",
  cancelled: "text-zinc-500",
};

function fmt(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

export default async function RunsPage() {
  let runs: Run[] = [];
  try {
    runs = await api.runs.list();
  } catch {
    // backend may not be running yet
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold text-white">Runs</h1>
        <Link
          href="/workflows"
          className="text-sm bg-zinc-800 hover:bg-zinc-700 text-white px-3 py-1.5 rounded transition-colors"
        >
          + New Run
        </Link>
      </div>

      {runs.length === 0 ? (
        <p className="text-zinc-500 text-sm">No runs yet. Trigger a workflow to get started.</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-zinc-500 border-b border-zinc-800">
              <th className="pb-2 pr-4">Workflow</th>
              <th className="pb-2 pr-4">Status</th>
              <th className="pb-2 pr-4">Phase</th>
              <th className="pb-2 pr-4">Cost</th>
              <th className="pb-2 pr-4">Started</th>
              <th className="pb-2">Completed</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.id} className="border-b border-zinc-900 hover:bg-zinc-900/50">
                <td className="py-2 pr-4">
                  <Link href={`/runs/${run.id}`} className="text-zinc-200 hover:text-white">
                    {run.workflow_slug}
                  </Link>
                  <span className="text-zinc-600 ml-2 text-xs">{run.id.slice(0, 8)}</span>
                </td>
                <td className={`py-2 pr-4 ${STATUS_COLORS[run.status] ?? "text-zinc-400"}`}>
                  {run.status}
                </td>
                <td className="py-2 pr-4 text-zinc-400">{run.phase ?? "—"}</td>
                <td className="py-2 pr-4 text-zinc-400">${run.cost_usd.toFixed(4)}</td>
                <td className="py-2 pr-4 text-zinc-500">{fmt(run.started_at)}</td>
                <td className="py-2 text-zinc-500">{fmt(run.completed_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
