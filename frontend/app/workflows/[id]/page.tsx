import Link from "next/link";
import { api } from "@/lib/api";
import { TriggerForm } from "@/app/components/TriggerForm";
import { WorkflowDAG } from "@/app/components/WorkflowDAG";

export default async function WorkflowDetailPage({ params }: PageProps<"/workflows/[id]">) {
  const { id } = await params;
  const wf = await api.workflows.get(id);
  const { phases, tasks } = wf.definition;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/workflows" className="text-zinc-500 hover:text-white text-sm">← Workflows</Link>
        <span className="text-zinc-700">/</span>
        <span className="text-zinc-300 text-sm">{wf.name}</span>
        <span className="text-zinc-600 text-xs">{wf.slug}</span>
      </div>

      {wf.description && (
        <p className="text-zinc-400 text-sm">{wf.description}</p>
      )}

      {/* Phases */}
      <div className="flex gap-3">
        {phases.map((phase, i) => (
          <div key={phase} className="flex items-center gap-2">
            {i > 0 && <span className="text-zinc-700 text-xs">→</span>}
            <span className="text-xs text-zinc-400 bg-zinc-900 border border-zinc-800 rounded px-2 py-1">
              {phase}
            </span>
          </div>
        ))}
      </div>

      {/* DAG */}
      <div>
        <h2 className="text-sm font-semibold text-white mb-3">Task Graph</h2>
        <WorkflowDAG tasks={tasks} phases={phases} />
      </div>

      {/* Trigger */}
      <div className="border border-zinc-800 rounded p-4">
        <h2 className="text-sm font-semibold text-white mb-3">Trigger Run</h2>
        <TriggerForm workflowId={wf.slug} />
      </div>

      {/* YAML */}
      <div className="border border-zinc-800 rounded p-4">
        <h2 className="text-sm font-semibold text-white mb-3">Definition</h2>
        <pre className="text-zinc-400 text-xs font-mono overflow-auto max-h-64 bg-zinc-950 rounded p-3 whitespace-pre">
          {wf.definition_yaml}
        </pre>
      </div>
    </div>
  );
}
