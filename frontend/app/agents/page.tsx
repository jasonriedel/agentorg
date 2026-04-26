import Link from "next/link";
import { api } from "@/lib/api";
import type { Agent } from "@/lib/types";

export default async function AgentsPage() {
  let agents: Agent[] = [];
  try {
    agents = await api.agents.list();
  } catch {
    // backend may not be running yet
  }

  return (
    <div>
      <h1 className="text-xl font-semibold text-white mb-6">Agents</h1>
      {agents.length === 0 ? (
        <p className="text-zinc-500 text-sm">No agents found. Make sure the backend is running and souls/*.soul.md files exist.</p>
      ) : (
        <div className="space-y-3">
          {agents.map((agent) => (
            <Link
              key={agent.slug}
              href={`/agents/${agent.slug}`}
              className="block border border-zinc-800 rounded p-4 hover:border-zinc-600 transition-colors"
            >
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-white font-medium">{agent.name}</span>
                  <span className="text-zinc-600 text-xs ml-2">{agent.slug}</span>
                </div>
                {agent.current_soul_version && (
                  <span className="text-zinc-500 text-xs font-mono">v{agent.current_soul_version}</span>
                )}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
