import { api } from "@/lib/api";
import type { SoulVersion } from "@/lib/types";

export default async function AgentDetailPage({ params }: PageProps<"/agents/[slug]">) {
  const { slug } = await params;

  let soul: SoulVersion | null = null;
  let versions: SoulVersion[] = [];

  try {
    [soul, versions] = await Promise.all([
      api.agents.soul(slug),
      api.agents.versions(slug),
    ]);
  } catch {
    // agent or soul may not exist
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-white">{slug}</h1>
        {soul && (
          <p className="text-zinc-500 text-xs mt-1">Active soul: v{soul.version}</p>
        )}
      </div>

      {soul ? (
        <div className="space-y-4">
          <div className="border border-zinc-800 rounded p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-zinc-300 text-sm font-medium">Soul</h2>
              <div className="flex items-center gap-3">
                <span className="text-zinc-600 text-xs font-mono">v{soul.version}</span>
                {soul.pr_url && (
                  <a
                    href={soul.pr_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-500 hover:text-blue-400 text-xs"
                  >
                    PR →
                  </a>
                )}
              </div>
            </div>
            <pre className="text-zinc-400 text-xs font-mono whitespace-pre-wrap overflow-auto max-h-96 bg-zinc-950 rounded p-3">
              {soul.soul_md}
            </pre>
          </div>

          {versions.length > 1 && (
            <div className="border border-zinc-800 rounded p-4">
              <h2 className="text-zinc-300 text-sm font-medium mb-3">Version History</h2>
              <div className="space-y-2">
                {versions.map((v) => (
                  <div key={v.id} className="flex items-center justify-between text-xs py-1.5 border-b border-zinc-800 last:border-0">
                    <div className="flex items-center gap-3">
                      <span className={`font-mono ${v.is_active ? "text-white" : "text-zinc-500"}`}>
                        v{v.version}
                      </span>
                      {v.is_active && (
                        <span className="text-emerald-500 text-[10px] uppercase tracking-wide">active</span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 text-zinc-600">
                      {v.commit_sha && (
                        <span className="font-mono">{v.commit_sha.slice(0, 8)}</span>
                      )}
                      {v.pr_url && (
                        <a
                          href={v.pr_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-500 hover:text-blue-400"
                        >
                          PR →
                        </a>
                      )}
                      <span>{new Date(v.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <p className="text-zinc-500 text-sm">No soul found for this agent.</p>
      )}
    </div>
  );
}
