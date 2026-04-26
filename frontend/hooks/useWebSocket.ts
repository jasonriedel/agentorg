"use client";

import { useEffect, useRef, useState } from "react";
import type { RunEvent } from "@/lib/types";
import { wsUrl } from "@/lib/api";

export function useRunEvents(runId: string) {
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket(wsUrl(runId));
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);

    ws.onmessage = (msg) => {
      const data = JSON.parse(msg.data) as RunEvent;
      if (data.event_type === "ping") return;
      setEvents((prev) => [...prev, data]);
    };

    return () => ws.close();
  }, [runId]);

  return { events, connected };
}
