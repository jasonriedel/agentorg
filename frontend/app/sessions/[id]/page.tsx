"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { SessionDetail, SessionMessage } from "@/lib/types";

const ROLE_STYLES: Record<string, string> = {
  user: "bg-zinc-900 border-zinc-800 text-zinc-200",
  assistant: "bg-zinc-950 border-zinc-800/50 text-zinc-300",
  tool_use: "bg-zinc-900/50 border-zinc-800 text-zinc-500",
  agent_spawn: "bg-violet-950/40 border-violet-800/50 text-violet-200",
};

const ROLE_LABEL: Record<string, string> = {
  user: "You",
  assistant: "Claude",
  tool_use: "Tool",
  agent_spawn: "Agent Spawn",
};

function Message({ msg }: { msg: SessionMessage }) {
  const [expanded, setExpanded] = useState(msg.role === "user" || msg.role === "assistant");

  const isLong = msg.content.length > 400;
  const preview = isLong && !expanded ? msg.content.slice(0, 400) + "…" : msg.content;

  return (
    <div className={`border rounded-lg p-3 ${ROLE_STYLES[msg.role] ?? ROLE_STYLES.assistant}`}>
      <div className="flex items-center justify-between mb-2 text-xs opacity-60">
        <span className="font-semibold uppercase tracking-wide">
          {msg.role === "tool_use" ? `⚙ ${msg.tool_name}` :
           msg.role === "agent_spawn" ? `⬡ ${msg.tool_name ?? "agent"}` :
           ROLE_LABEL[msg.role]}
        </span>
        {msg.timestamp && (
          <span>{new Date(msg.timestamp).toLocaleTimeString()}</span>
        )}
      </div>
      <pre className="text-xs whitespace-pre-wrap font-mono leading-relaxed">{preview}</pre>
      {isLong && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-2 text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          {expanded ? "Show less ↑" : "Show more ↓"}
        </button>
      )}
    </div>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }}
      className="text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-300 px-3 py-1.5 rounded transition-colors font-mono"
    >
      {copied ? "✓ Copied" : text}
    </button>
  );
}

export default function SessionDetailPage({ params }: PageProps<"/sessions/[id]">) {
  const [id, setId] = useState<string | null>(null);
  const [session, setSession] = useState<SessionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "user" | "assistant" | "agent_spawn">("all");

  useEffect(() => {
    params.then(({ id: sessionId }) => {
      setId(sessionId);
      api.sessions.get(sessionId)
        .then(setSession)
        .catch((e) => setError(e.message))
        .finally(() => setLoading(false));
    });
  }, [params]);

  const filtered = session?.messages.filter(
    (m) => filter === "all" || m.role === filter
  ) ?? [];

  if (loading) {
    return <div className="text-zinc-500 text-sm">Loading session…</div>;
  }

  if (error || !session) {
    return (
      <div className="space-y-4">
        <Link href="/sessions" className="text-zinc-500 hover:text-white text-sm">← Sessions</Link>
        <p className="text-red-400 text-sm">{error ?? "Session not found"}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-3">
        <Link href="/sessions" className="text-zinc-500 hover:text-white text-sm mt-0.5">←</Link>
        <div className="min-w-0 flex-1">
          <h1 className="text-xl font-semibold text-white truncate">{session.title}</h1>
          <p className="text-zinc-500 text-xs mt-0.5">{session.cwd ?? session.project_path}</p>
        </div>
      </div>

      {/* Stats + Resume */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex gap-6 text-sm">
          <div>
            <p className="text-zinc-600 text-xs">Messages</p>
            <p className="text-zinc-300">{session.message_count}</p>
          </div>
          <div>
            <p className="text-zinc-600 text-xs">Agents spawned</p>
            <p className="text-violet-400">{session.agent_spawn_count}</p>
          </div>
          <div>
            <p className="text-zinc-600 text-xs">Last active</p>
            <p className="text-zinc-300">
              {session.last_active ? new Date(session.last_active).toLocaleString() : "—"}
            </p>
          </div>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <span className="text-zinc-600 text-xs">Resume in terminal:</span>
          <CopyButton text={session.resume_command} />
        </div>
      </div>

      {/* Agent spawns summary */}
      {session.agent_spawns.length > 0 && (
        <div className="border border-violet-900/50 bg-violet-950/20 rounded-lg p-4">
          <h2 className="text-xs font-semibold text-violet-400 uppercase tracking-wider mb-3">
            ⬡ Agents Spawned ({session.agent_spawns.length})
          </h2>
          <div className="space-y-2">
            {session.agent_spawns.map((a, i) => (
              <div key={i} className="flex items-start gap-3 text-xs">
                <span className="text-violet-600 shrink-0 font-mono">{a.subagent_type}</span>
                <span className="text-zinc-400 line-clamp-2">{a.description}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Message filter */}
      <div className="flex items-center gap-2">
        <span className="text-zinc-600 text-xs">Filter:</span>
        {(["all", "user", "assistant", "agent_spawn"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`text-xs px-2.5 py-1 rounded transition-colors ${
              filter === f
                ? "bg-zinc-700 text-white"
                : "bg-zinc-900 text-zinc-500 hover:text-zinc-300"
            }`}
          >
            {f === "agent_spawn" ? "agents" : f}
          </button>
        ))}
        <span className="text-zinc-700 text-xs ml-2">{filtered.length} messages</span>
      </div>

      {/* Messages */}
      <div className="space-y-2">
        {filtered.map((msg, i) => (
          <Message key={i} msg={msg} />
        ))}
      </div>
    </div>
  );
}
