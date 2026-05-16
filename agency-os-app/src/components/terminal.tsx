"use client";

import { useEffect, useRef, useState } from "react";

interface LogEntry {
  id: string;
  time: string;
  line: string;
  type: "info" | "ok" | "err";
}

export function Terminal() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:3001");
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "log" || data.type === "job_started" || data.type === "job_completed") {
        const type = data.type === "job_completed" && data.status === "done" ? "ok" : "info";
        setLogs((prev) => [
          ...prev,
          {
            id: Math.random().toString(36).slice(2),
            time: new Date().toLocaleTimeString(),
            line: data.line || `${data.type}: ${data.jobId}`,
            type,
          },
        ]);
      }
    };
    return () => ws.close();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  return (
    <div className="flex h-full flex-col rounded-xl border border-border bg-black/60 backdrop-blur">
      <div className="flex items-center gap-2 border-b border-border px-4 py-2">
        <div className="h-2.5 w-2.5 rounded-full bg-red-500/80" />
        <div className="h-2.5 w-2.5 rounded-full bg-amber-500/80" />
        <div className="h-2.5 w-2.5 rounded-full bg-emerald-500/80" />
        <span className="ml-2 text-xs font-medium text-muted-foreground">system.log</span>
      </div>
      <div className="flex-1 overflow-auto p-4 font-mono text-xs">
        {logs.length === 0 && (
          <p className="text-muted-foreground">Waiting for events...</p>
        )}
        {logs.map((log) => (
          <div
            key={log.id}
            className={`mb-0.5 ${
              log.type === "ok"
                ? "text-emerald-400"
                : log.type === "err"
                ? "text-red-400"
                : "text-cyan-400"
            }`}
          >
            <span className="text-muted-foreground">[{log.time}]</span> {log.line}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
