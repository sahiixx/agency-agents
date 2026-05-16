"use client";

import { createContext, useContext, useEffect, useState } from "react";

type WSContextType = {
  connected: boolean;
  logs: { time: string; line: string; type: string }[];
};

const WSContext = createContext<WSContextType>({ connected: false, logs: [] });

export function useWS() {
  return useContext(WSContext);
}

export function WSProvider({ children }: { children: React.ReactNode }) {
  const [connected, setConnected] = useState(false);
  const [logs, setLogs] = useState<{ time: string; line: string; type: string }[]>([]);

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:3001");
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "log" || data.type === "job_started" || data.type === "job_completed") {
        setLogs((prev) => [
          ...prev.slice(-50),
          {
            time: new Date().toLocaleTimeString(),
            line: data.line || `${data.type}: ${data.jobId || data.id || ""}`,
            type: data.type === "job_completed" && data.status === "done" ? "ok" : "info",
          },
        ]);
      }
    };
    return () => ws.close();
  }, []);

  return <WSContext.Provider value={{ connected, logs }}>{children}</WSContext.Provider>;
}
