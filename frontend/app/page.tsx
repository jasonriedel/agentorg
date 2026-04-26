import Link from "next/link";
import { api } from "@/lib/api";
import type { Run, SessionSummary } from "@/lib/types";

const STATUS_COLORS: Record<string, string> = {
  completed: "text-green-400",
  running: "text-blue-400",
  failed: "text-red-400",
  waiting_human: "text-yellow-400",
  pending: "text-zinc-500",
};

function relativeTime(iso: string | null): string {
  if (!iso) return "—";
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function projectName(path: string | null): string {
  if (!path) return "—";
  const parts = path.split("/").filter(Boolean);
  return parts[parts.length - 1] ?? path;
}

export default async function HomePage() {
  let runs: Run[] = [];
  let sessions: SessionSummary[] = [];

  try {
    [runs, sessions] = await Promise.all([
      api.runs.list(),
      api.sessions.list(20),
    ]);
  } catch {
    // backend may not be running yet
  }

  const recentRuns = runs.slice(0, 5);
  const recentSessions = sessions.slice(0, 8);

  return (
    <div className="space-y-10">
      <div>
        <h1 className="text-2xl font-bold text-white">AgentOrg</h1>
        <p className="text-zinc-500 text-sm mt-1">Multi-agent workflow command center</p>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { href: "/workflows", label: "Workflows", desc: "Trigger agent runs" },
          { href: "/runs", label: "Runs", desc: "Execution history" },
          { href: "/agents", label: "Agents", desc: "Soul management" },
          { href: "/sessions", label: "Sessions", desc: "Claude history" },
        ].map(({ href, label, desc }) => (
          <Link
            key={href}
            href={href}
            className="border border-zinc-800 hover:border-zinc-600 rounded-lg p-4 transition-colors group"
          >
            <p className="text-white font-medium text-sm group-hover:text-zinc-200">{label}</p>
            <p className="text-zinc-600 text-xs mt-0.5">{desc}</p>
          </Link>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-white">Recent Runs</h2>
            <Link href="/runs" className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors">View all →</Link>
          </div>
          {recentRuns.length === 0 ? (
            <div className="border border-zinc-800 rounded-lg p-4">
              <p className="text-zinc-600 text-sm">No runs yet.</p>
              <Link href="/workflows" className="text-blue-500 hover:text-blue-400 text-xs mt-1 inline-block">
                Trigger a workflow →
              </Link>
            </div>
          ) : (
            <div className="space-y-2">
              {recentRuns.map((run) => (
                <Link
                  key={run.id}
                  href={`/runs/${run.id}`}
                  className="flex items-center justify-between border border-zinc-800 hover:border-zinc-700 rounded-lg px-3 py-2.5 transition-colors group"
                >
                  <div className="min-w-0">
                    <span className="text-zinc-300 text-sm group-hover:text-white transition-colors">
                      {run.workflow_slug}
                    </span>
                    <span className="text-zinc-700 text-xs ml-2">{run.id.slice(0, 8)}</span>
                  </div>
                  <div className="flex items-center gap-3 shrink-0 text-xs">
                    <span className={STATUS_COLORS[run.status] ?? "text-zinc-400"}>{run.status}</span>
                    <span className="text-zinc-600">{relativeTime(run.started_at)}</span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-white">Recent Claude Sessions</h2>
            <Link href="/sessions" className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors">View all →</Link>
          </div>
          {recentSessions.length === 0 ? (
            <p className="text-zinc-600 text-sm border border-zinc-800 rounded-lg p-4">No sessions found.</p>
          ) : (
            <div className="space-y-2">
              {recentSessions.map((s) => (
                <Link
                  key={s.id}
                  href={`/sessions/${s.id}`}
                  className="flex items-center justify-between border border-zinc-800 hover:border-zinc-700 rounded-lg px-3 py-2.5 transition-colors group"
                >
                  <div className="min-w-0">
                    <span className="text-zinc-300 text-sm group-hover:text-white transition-colors truncate block">
                      {s.title}
                    </span>
                    <span className="text-zinc-600 text-xs">{projectName(s.cwd)}</span>
                  </div>
                  <div className="flex items-center gap-3 shrink-0 text-xs text-zinc-600">
                    {s.agent_spawn_count > 0 && (
                      <span className="text-violet-500">⬡ {s.agent_spawn_count}</span>
                    )}
                    <span>{relativeTime(s.last_active)}</span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
