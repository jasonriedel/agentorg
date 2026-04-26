"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";

export function TriggerForm({ workflowId }: { workflowId: string }) {
  const router = useRouter();
  const [description, setDescription] = useState("");
  const [branch, setBranch] = useState("main");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function trigger() {
    if (!description.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const run = await api.workflows.trigger(workflowId, {
        feature_description: description,
        target_branch: branch,
      });
      router.push(`/runs/${run.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to trigger workflow");
      setLoading(false);
    }
  }

  return (
    <div className="space-y-2">
      <input
        type="text"
        placeholder="Describe the feature to implement…"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        className="w-full bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-sm text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-zinc-500"
      />
      <div className="flex items-center gap-2">
        <input
          type="text"
          placeholder="Target branch"
          value={branch}
          onChange={(e) => setBranch(e.target.value)}
          className="w-32 bg-zinc-900 border border-zinc-700 rounded px-3 py-1.5 text-xs text-zinc-400 placeholder-zinc-600 focus:outline-none focus:border-zinc-500"
        />
        <button
          onClick={trigger}
          disabled={loading || !description.trim()}
          className="bg-blue-700 hover:bg-blue-600 text-white px-4 py-1.5 rounded text-xs transition-colors disabled:opacity-50"
        >
          {loading ? "Triggering…" : "Trigger →"}
        </button>
      </div>
      {error && <p className="text-red-400 text-xs">{error}</p>}
    </div>
  );
}
