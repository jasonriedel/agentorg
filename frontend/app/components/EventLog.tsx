"use client";

import { useRunEvents } from "@/hooks/useWebSocket";
import type { RunEvent } from "@/lib/types";

const EVENT_COLORS: Record<string, string> = {
  run_started: "text-blue-400",
  run_completed: "text-green-400",
  run_failed: "text-red-400",
  phase_started: "text-purple-400",
  task_started: "text-blue-300",
  task_completed: "text-green-300",
  task_failed: "text-red-300",
  tool_call: "text-yellow-400",
  human_gate: "text-orange-400",
  gate_resolved: "text-teal-400",
  cost_warning: "text-orange-300",
};

function EventRow({ event }: { event: RunEvent }) {
  const color = EVENT_COLORS[event.event_type] ?? "text-zinc-400";
  const time = new Date(event.created_at).toLocaleTimeString();
  const payload = Object.entries(event.payload ?? {})
    .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
    .join(" ");

  return (
    <div className="flex gap-3 text-xs py-0.5 font-mono">
      <span className="text-zinc-600 shrink-0">{time}</span>
      <span className={`shrink-0 w-32 ${color}`}>{event.event_type}</span>
      <span className="text-zinc-400 truncate">{payload}</span>
    </div>
  );
}

export function EventLog({ runId }: { runId: string }) {
  const { events, connected } = useRunEvents(runId);

  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <h2 className="text-sm font-semibold text-white">Event Log</h2>
        <span className={`text-xs ${connected ? "text-green-400" : "text-zinc-600"}`}>
          {connected ? "● live" : "○ disconnected"}
        </span>
      </div>
      <div className="bg-zinc-950 border border-zinc-800 rounded p-3 h-72 overflow-y-auto">
        {events.length === 0 ? (
          <p className="text-zinc-600 text-xs">Waiting for events…</p>
        ) : (
          events.map((e, i) => <EventRow key={e.id ?? i} event={e} />)
        )}
      </div>
    </div>
  );
}
