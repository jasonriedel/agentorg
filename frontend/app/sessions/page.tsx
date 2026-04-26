import Link from "next/link";
import { api } from "@/lib/api";
import type { SessionSummary } from "@/lib/types";

function relativeTime(iso: string | null): string {
  if (!iso) return "—";
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(iso).toLocaleDateString();
}

function projectName(path: string): string {
  const parts = path.split("/").filter(Boolean);
  return parts[parts.length - 1] ?? path;
}

function SessionCard({ s }: { s: SessionSummary }) {
  return (
    <Link
      href={`/sessions/${s.id}`}
      className="block border border-zinc-800 hover:border-zinc-600 rounded-lg p-4 transition-colors group"
    >
      <div className="flex items-start justify-between gap-4 mb-2">
        <div className="min-w-0">
          <p className="text-white font-medium text-sm truncate group-hover:text-zinc-200">
            {s.title}
          </p>
          <p className="text-zinc-500 text-xs mt-0.5 truncate">{s.cwd ?? s.project_path}</p>
        </div>
        <span className="text-zinc-600 text-xs shrink-0">{relativeTime(s.last_active)}</span>
      </div>

      {s.first_message && (
        <p className="text-zinc-500 text-xs line-clamp-2 mb-3">{s.first_message}</p>
      )}

      <div className="flex items-center gap-4 text-xs text-zinc-600">
        <span>{s.message_count} messages</span>
        {s.agent_spawn_count > 0 && (
          <span className="text-violet-500">⬡ {s.agent_spawn_count} agent{s.agent_spawn_count !== 1 ? "s" : ""}</span>
        )}
        <span className="ml-auto font-mono">{s.id.slice(0, 8)}</span>
      </div>
    </Link>
  );
}

export default async function SessionsPage() {
  let sessions: SessionSummary[] = [];
  try {
    sessions = await api.sessions.list(200);
  } catch {
    // backend may not be running
  }

  // Group by project
  const byProject = new Map<string, SessionSummary[]>();
  for (const s of sessions) {
    const key = s.cwd ?? s.project_path;
    if (!byProject.has(key)) byProject.set(key, []);
    byProject.get(key)!.push(s);
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-white">Claude Sessions</h1>
          <p className="text-zinc-500 text-xs mt-1">{sessions.length} sessions across {byProject.size} projects</p>
        </div>
      </div>

      {sessions.length === 0 ? (
        <p className="text-zinc-500 text-sm">No sessions found. Make sure the backend can read ~/.claude/projects/</p>
      ) : (
        <div className="space-y-8">
          {Array.from(byProject.entries()).map(([project, projectSessions]) => (
            <div key={project}>
              <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3 flex items-center gap-2">
                <span className="truncate">{projectName(project)}</span>
                <span className="text-zinc-700 normal-case font-normal tracking-normal shrink-0">{projectSessions.length}</span>
              </h2>
              <div className="space-y-2">
                {projectSessions.map((s) => (
                  <SessionCard key={s.id} s={s} />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
