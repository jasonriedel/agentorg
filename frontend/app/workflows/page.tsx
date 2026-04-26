import { TriggerForm } from "@/app/components/TriggerForm";
import { api } from "@/lib/api";
import type { Workflow } from "@/lib/types";

export default async function WorkflowsPage() {
  let workflows: Workflow[] = [];
  try {
    workflows = await api.workflows.list();
  } catch {
    // backend may not be running yet
  }

  return (
    <div>
      <h1 className="text-xl font-semibold text-white mb-6">Workflows</h1>
      {workflows.length === 0 ? (
        <p className="text-zinc-500 text-sm">No workflows found. Make sure the backend is running and workflows/*.yaml files exist.</p>
      ) : (
        <div className="space-y-4">
          {workflows.map((wf) => (
            <div key={wf.id} className="border border-zinc-800 rounded p-4">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h2 className="text-white font-medium">{wf.name}</h2>
                  {wf.description && <p className="text-zinc-500 text-xs mt-0.5">{wf.description}</p>}
                </div>
                <span className="text-zinc-600 text-xs">{wf.slug}</span>
              </div>
              <TriggerForm workflowId={wf.slug} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
