"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { Gate } from "@/lib/types";

export function GateApproval({ runId, gate }: { runId: string; gate: Gate }) {
  const [feedback, setFeedback] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(gate.status !== "waiting");

  if (done || gate.status !== "waiting") {
    return (
      <div className="border border-zinc-800 rounded p-3 text-sm">
        <span className="text-zinc-500">Gate </span>
        <span className="text-white">{gate.name}</span>
        <span className={` ml-2 ${gate.status === "approved" ? "text-green-400" : "text-red-400"}`}>
          {gate.status}
        </span>
      </div>
    );
  }

  async function respond(action: "approved" | "rejected") {
    setSubmitting(true);
    try {
      await api.runs.resolveGate(runId, gate.id, action, feedback || undefined);
      setDone(true);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="border border-yellow-700/50 bg-yellow-950/20 rounded p-4 text-sm">
      <p className="text-yellow-300 font-semibold mb-1">⏸ Human Gate: {gate.name}</p>
      <p className="text-zinc-300 mb-3">{gate.message}</p>
      <textarea
        className="w-full bg-zinc-900 border border-zinc-700 rounded p-2 text-xs text-zinc-300 mb-3 resize-none"
        rows={2}
        placeholder="Optional feedback…"
        value={feedback}
        onChange={(e) => setFeedback(e.target.value)}
      />
      <div className="flex gap-2">
        <button
          onClick={() => respond("approved")}
          disabled={submitting}
          className="bg-green-800 hover:bg-green-700 text-white px-3 py-1.5 rounded text-xs transition-colors disabled:opacity-50"
        >
          Approve
        </button>
        <button
          onClick={() => respond("rejected")}
          disabled={submitting}
          className="bg-red-900 hover:bg-red-800 text-white px-3 py-1.5 rounded text-xs transition-colors disabled:opacity-50"
        >
          Reject
        </button>
      </div>
    </div>
  );
}
