import { WebSocketServer, WebSocket } from "ws";
import { prisma } from "@/lib/prisma";

let wss: WebSocketServer | null = null;
const clients = new Set<WebSocket>();

export function initWebSocketServer(port = 3001) {
  wss = new WebSocketServer({ port });
  wss.on("connection", (ws) => {
    clients.add(ws);
    ws.send(JSON.stringify({ type: "connected", time: Date.now() }));
    ws.on("close", () => clients.delete(ws));
  });
  console.log(`WebSocket server on ws://localhost:${port}`);
}

export function broadcast(event: Record<string, unknown>) {
  const msg = JSON.stringify(event);
  clients.forEach((ws) => {
    if (ws.readyState === WebSocket.OPEN) ws.send(msg);
  });
}

export function emitJobStarted(jobId: string, name: string, engine: string) {
  broadcast({ type: "job_started", jobId, name, engine });
}

export function emitJobCompleted(jobId: string, status: string, items: number) {
  broadcast({ type: "job_completed", jobId, status, items });
}

export function emitLog(jobId: string, line: string) {
  broadcast({ type: "log", jobId, line });
}
