/**
 * The Agency — Mission Control on Cloudflare Workers
 *
 * Architecture:
 *   MissionRoom (Durable Object, SQLite-backed)
 *     — Holds live mission state in embedded SQLite
 *     — Fan-out to all browser clients via WebSocket Hibernation API
 *     — One DO instance per mission ID, globally unique
 *
 *   MissionWorkflow (Cloudflare Workflows)
 *     — Durable execution of the multi-agent pipeline
 *     — Each agent call is a retryable step
 *     — Pushes events to DO as each agent completes
 *
 *   AGENCY_KV      — Titans memory ledger (mission history, surprise weights)
 *   AGENCY_DB (D1) — Structured observability traces, SQL queryable
 */

import { DurableObject } from "cloudflare:workers";
import { WorkflowEntrypoint, WorkflowStep, WorkflowEvent } from "cloudflare:workers";
import Anthropic from "@anthropic-ai/sdk";

// ── Environment ───────────────────────────────────────────────────────────────

export interface Env {
  MISSION_ROOM: DurableObjectNamespace;
  AGENCY_KV: KVNamespace;
  AGENCY_DB: D1Database;
  MISSION_WORKFLOW: Workflow;
  ANTHROPIC_API_KEY: string;
  CLAUDE_MODEL: string;
}

// ── Agent system prompts ──────────────────────────────────────────────────────

const AGENT_PROMPTS: Record<string, string> = {
  pm: `You are a Senior Project Manager AI agent. For any mission:
1. Decompose into clear sprint phases with owners and timelines
2. Identify risks, blockers, and dependencies
3. Define success criteria and MVP milestones
4. Output a structured sprint plan. Be concise and action-oriented.`,

  backend: `You are a Backend Architect AI agent. For any mission:
1. Design the data layer, API contracts, and system architecture
2. Select stack, define DB schema, caching strategy, auth pattern
3. Define performance targets (p99 latency, throughput, availability SLA)
4. Output a complete technical spec with endpoint definitions
Be specific about UAE/CBUAE regulatory compliance where relevant.`,

  frontend: `You are a Frontend Developer AI agent. For any mission:
1. Design component architecture and data flow
2. Select framework (Next.js preferred), state management, UI library
3. Plan RTL support, Arabic locale, mobile-first for UAE market
4. Output complete UI spec with component tree and API integration plan`,

  security: `You are a Security Engineer AI agent. For any mission:
1. Run threat model: OWASP Top 10, data flow analysis, attack surface
2. Flag HIGH/MED/LOW issues with concrete remediation steps
3. Check UAE PDPL compliance and data residency requirements
4. Output security review with explicit pre-launch gates
Mark any BLOCKER clearly.`,

  qa: `You are a QA Engineer AI agent. For any mission:
1. Design test plan: unit, integration, E2E, load, security cases
2. Define acceptance criteria and critical user paths
3. Identify domain-specific edge cases (gold pricing, FX, UAE lending)
4. Output complete test matrix with pass/fail criteria`,

  copywriter: `You are a Content Strategist AI agent. For any mission:
1. Develop messaging hierarchy: headline, value prop, CTAs
2. Write English copy with notes on Arabic adaptation
3. Align tone to UAE professional/fintech market
4. Output complete copy deck with A/B headline variants`,

  ai: `You are an AI/ML Engineer AI agent. For any mission:
1. Research relevant ML approaches, models, and architectures
2. Assess feasibility, accuracy targets, inference latency, cost
3. Recommend data requirements, training strategy, evaluation metrics
4. Output technical AI recommendation with phased implementation path`,

  core: `You are the Claude Reasoning Core — the final constitutional gate.
You receive all specialist agent outputs and must:
1. Verify technical accuracy and consistency across all outputs
2. Check for safety, legal compliance, and completeness
3. Resolve conflicts between specialist recommendations
4. Issue a final verdict. Start your response with EXACTLY one of:
   VERDICT: GO
   VERDICT: CONDITIONAL GO
   VERDICT: NO-GO
5. Then write:
   SUMMARY: [one paragraph]
   BLOCKERS: [bullet list or "None"]
   DELIVERABLE: [synthesized final output]`,
};

const PARALLEL_GROUPS: Record<string, string[][]> = {
  full:     [["pm"], ["backend", "frontend", "security"], ["qa"], ["core"]],
  saas:     [["pm"], ["copywriter", "frontend"], ["qa"], ["core"]],
  research: [["pm", "ai"], ["qa"], ["core"]],
};

// ── Types ─────────────────────────────────────────────────────────────────────

interface AgentLog {
  ts: string;
  agent: string;
  msg: string;
  kind: "system" | "agent" | "output" | "verdict" | "error";
}

interface WSEvent {
  type: "log" | "agent_status" | "metrics" | "verdict" | "init";
  payload: unknown;
}

// ── Durable Object: MissionRoom ───────────────────────────────────────────────

export class MissionRoom extends DurableObject {
  private sql: SqlStorage;

  constructor(ctx: DurableObjectState, env: Env) {
    super(ctx, env);
    this.sql = ctx.storage.sql;

    // Idempotent schema bootstrap
    this.sql.exec(`
      CREATE TABLE IF NOT EXISTS mission (
        id TEXT PRIMARY KEY,
        goal TEXT,
        preset TEXT,
        agents TEXT,
        status TEXT DEFAULT 'pending',
        verdict TEXT DEFAULT 'PENDING'
      );
      CREATE TABLE IF NOT EXISTS logs (
        rowid INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT, agent TEXT, msg TEXT, kind TEXT
      );
      CREATE TABLE IF NOT EXISTS metrics (
        key TEXT PRIMARY KEY, value TEXT
      );
      CREATE TABLE IF NOT EXISTS agent_status (
        agent TEXT PRIMARY KEY, status TEXT
      );
    `);
  }

  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);

    // WebSocket upgrade — each browser tab that opens the UI connects here
    if (request.headers.get("Upgrade") === "websocket") {
      const pair = new WebSocketPair();
      const [client, server] = Object.values(pair);
      this.ctx.acceptWebSocket(server);
      // Immediately send full state snapshot to the new client
      server.send(JSON.stringify({ type: "snapshot", payload: this.snapshot() }));
      return new Response(null, { status: 101, webSocket: client });
    }

    // Internal: Workflow pushes events here
    if (url.pathname === "/push" && request.method === "POST") {
      const event = await request.json() as WSEvent;
      this.apply(event);
      this.broadcast(event);
      return new Response("ok");
    }

    // REST state read (polling fallback)
    if (url.pathname === "/state") {
      return Response.json(this.snapshot());
    }

    return new Response("Not found", { status: 404 });
  }

  // WebSocket Hibernation API — DO NOT use addEventListener
  async webSocketMessage(_ws: WebSocket, _msg: string | ArrayBuffer): Promise<void> {
    // Client pings ignored; all data flows server → client
  }

  async webSocketClose(ws: WebSocket, code: number): Promise<void> {
    ws.close(code, "closed");
  }

  async webSocketError(_ws: WebSocket, error: unknown): Promise<void> {
    console.error("WS error in MissionRoom:", error);
  }

  private apply(event: WSEvent): void {
    switch (event.type) {
      case "init": {
        const p = event.payload as { missionId: string; goal: string; preset: string; agents: string[] };
        this.sql.exec(
          "INSERT OR IGNORE INTO mission (id, goal, preset, agents, status) VALUES (?, ?, ?, ?, 'running')",
          p.missionId, p.goal, p.preset, p.agents.join(",")
        );
        break;
      }
      case "log": {
        const l = event.payload as AgentLog;
        this.sql.exec(
          "INSERT INTO logs (ts, agent, msg, kind) VALUES (?, ?, ?, ?)",
          l.ts, l.agent, l.msg, l.kind
        );
        break;
      }
      case "agent_status": {
        const s = event.payload as { agent: string; status: string };
        this.sql.exec(
          "INSERT OR REPLACE INTO agent_status (agent, status) VALUES (?, ?)",
          s.agent, s.status
        );
        break;
      }
      case "metrics": {
        const m = event.payload as Record<string, string | number>;
        for (const [k, v] of Object.entries(m)) {
          this.sql.exec(
            "INSERT OR REPLACE INTO metrics (key, value) VALUES (?, ?)",
            k, String(v)
          );
        }
        break;
      }
      case "verdict": {
        const v = event.payload as { verdict: string };
        this.sql.exec(
          "UPDATE mission SET verdict = ?, status = 'done'",
          v.verdict
        );
        break;
      }
    }
  }

  private broadcast(event: WSEvent): void {
    const msg = JSON.stringify(event);
    for (const ws of this.ctx.getWebSockets()) {
      try { ws.send(msg); } catch { /* stale socket, skip */ }
    }
  }

  private snapshot(): object {
    const mission = [...this.sql.exec("SELECT * FROM mission LIMIT 1")][0] ?? {};
    const logs = [...this.sql.exec("SELECT ts, agent, msg, kind FROM logs ORDER BY rowid")];
    const agentStatuses = Object.fromEntries(
      [...this.sql.exec("SELECT agent, status FROM agent_status")].map(r => [r.agent as string, r.status])
    );
    const metrics = Object.fromEntries(
      [...this.sql.exec("SELECT key, value FROM metrics")].map(r => [r.key as string, r.value])
    );
    return { mission, logs, agentStatuses, metrics };
  }
}

// ── Workflow: MissionWorkflow ─────────────────────────────────────────────────

interface MissionParams {
  missionId: string;
  goal: string;
  preset: string;
  agents: string[];
}

export class MissionWorkflow extends WorkflowEntrypoint<Env, MissionParams> {
  async run(event: WorkflowEvent<MissionParams>, step: WorkflowStep): Promise<void> {
    const { missionId, goal, preset, agents } = event.payload;
    const groups = PARALLEL_GROUPS[preset] ?? [["pm"], ["core"]];
    const model = this.env.CLAUDE_MODEL || "claude-sonnet-4-6";

    // Helper: push a typed event into the live DO
    const push = async (type: WSEvent["type"], payload: unknown): Promise<void> => {
      const doId = this.env.MISSION_ROOM.idFromName(missionId);
      const stub = this.env.MISSION_ROOM.get(doId);
      await stub.fetch("http://internal/push", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type, payload }),
      });
    };

    const log = (agent: string, msg: string, kind: AgentLog["kind"] = "agent"): Promise<void> =>
      push("log", { ts: new Date().toISOString().slice(11, 19), agent, msg, kind });

    // Init the DO state
    await push("init", { missionId, goal, preset, agents });
    for (const a of agents) await push("agent_status", { agent: a, status: "ready" });
    await log("SYSTEM", `Mission ${missionId} launched. Preset: ${preset}`, "system");
    await log("SYSTEM", `Agents: ${agents.join(", ")} | Model: ${model}`, "system");

    const client = new Anthropic({ apiKey: this.env.ANTHROPIC_API_KEY });
    const outputs: Record<string, string> = {};
    let totalIn = 0, totalOut = 0, totalCost = 0;

    for (let pi = 0; pi < groups.length; pi++) {
      const group = groups[pi];
      await log("ORCHESTRATOR",
        `Phase ${pi + 1}/${groups.length}: [${group.join(" ∥ ")}]`, "system");

      for (const agentName of group) {
        await push("agent_status", { agent: agentName, status: "working" });

        const prior = Object.entries(outputs)
          .map(([a, o]) => `=== ${a.toUpperCase()} ===\n${o.slice(0, 1000)}`)
          .join("\n\n");

        const isCore = agentName === "core";
        const userMsg = isCore
          ? `MISSION: ${goal}\n\nPRESET: ${preset}\n\nALL SPECIALIST OUTPUTS:\n${prior}\n\nProvide your constitutional review and verdict now.`
          : `MISSION: ${goal}\n\nComplete your specialist role.${prior ? `\n\nPRIOR OUTPUTS:\n${prior}` : ""}`;

        // Each agent is a durable, retryable step
        const result = await step.do(
          `agent:${agentName}`,
          { retries: { limit: 2, delay: "8 seconds", backoff: "exponential" }, timeout: "4 minutes" },
          async () => {
            const res = await client.messages.create({
              model,
              max_tokens: 1000,
              system: AGENT_PROMPTS[agentName] ?? `You are the ${agentName} agent.`,
              messages: [{ role: "user", content: userMsg }],
            });
            const text = res.content[0].type === "text" ? res.content[0].text : "";
            return { text, inTok: res.usage.input_tokens, outTok: res.usage.output_tokens };
          }
        );

        outputs[agentName] = result.text;
        totalIn += result.inTok;
        totalOut += result.outTok;
        totalCost += (result.inTok / 1e6) * 3.0 + (result.outTok / 1e6) * 15.0;

        // Stream first lines of output to the live UI
        for (const line of result.text.split("\n").filter(l => l.trim()).slice(0, 5)) {
          await log(agentName.toUpperCase(), line, isCore ? "output" : "agent");
        }

        await push("agent_status", { agent: agentName, status: "done" });
        await push("metrics", {
          tokensIn: totalIn, tokensOut: totalOut,
          costUsd: totalCost.toFixed(4),
        });
      }
    }

    // Parse verdict from core output
    const coreOut = outputs["core"] ?? "";
    const vm = coreOut.match(/VERDICT\s*:\s*(GO|CONDITIONAL GO|NO-GO)/i);
    const verdict = vm
      ? vm[1].toUpperCase()
      : /no-go|no go/i.test(coreOut) ? "NO-GO"
      : /conditional/i.test(coreOut) ? "CONDITIONAL GO"
      : "GO";

    await log("CORE", `━━━ VERDICT: ${verdict} ━━━`, "verdict");
    await push("verdict", { verdict });

    // Persist to KV (Titans memory)
    const surprise = verdict === "NO-GO" ? 1.0 : verdict === "CONDITIONAL GO" ? 0.65 : 0.35;
    await this.env.AGENCY_KV.put(
      `mission:${missionId}`,
      JSON.stringify({
        missionId, goal: goal.slice(0, 300), preset, verdict, surprise,
        tokensIn: totalIn, tokensOut: totalOut, costUsd: totalCost.toFixed(4),
        ts: new Date().toISOString(),
      }),
      { expirationTtl: 60 * 60 * 24 * 30 }
    );
    const ledger: object[] = JSON.parse((await this.env.AGENCY_KV.get("titans:ledger")) ?? "[]");
    ledger.unshift({ missionId, goal: goal.slice(0, 80), verdict, surprise, ts: new Date().toISOString() });
    await this.env.AGENCY_KV.put("titans:ledger", JSON.stringify(ledger.slice(0, 100)));

    // Persist trace to D1
    await step.do("save-d1", async () => {
      await this.env.AGENCY_DB.prepare(`
        INSERT INTO mission_traces
          (mission_id, goal, preset, verdict, agents, tokens_in, tokens_out, cost_usd, surprise, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
      `).bind(
        missionId, goal.slice(0, 400), preset, verdict,
        agents.join(","), totalIn, totalOut,
        parseFloat(totalCost.toFixed(4)), surprise
      ).run();
    });

    await log("SYSTEM",
      `Complete. Verdict: ${verdict} | ${(totalIn + totalOut).toLocaleString()} tokens | $${totalCost.toFixed(4)}`,
      "system"
    );
  }
}

// ── Main Worker ───────────────────────────────────────────────────────────────

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const cors = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Upgrade, Connection",
    };
    if (request.method === "OPTIONS") return new Response(null, { headers: cors });

    // WebSocket → MissionRoom DO
    if (url.pathname.startsWith("/ws/") && request.headers.get("Upgrade") === "websocket") {
      const missionId = url.pathname.slice(4);
      const doId = env.MISSION_ROOM.idFromName(missionId);
      return env.MISSION_ROOM.get(doId).fetch(request);
    }

    // Launch a mission
    if (url.pathname === "/api/launch" && request.method === "POST") {
      const body = await request.json() as { goal?: string; preset?: string };
      const goal = (body.goal ?? "").trim();
      const preset = PARALLEL_GROUPS[body.preset ?? ""] ? (body.preset as string) : "full";
      if (!goal) return Response.json({ error: "goal required" }, { status: 400, headers: cors });

      const agents = [...new Set(PARALLEL_GROUPS[preset].flat())];
      const missionId = `m_${Date.now()}_${crypto.randomUUID().slice(0, 6)}`;
      await env.MISSION_WORKFLOW.create({ id: missionId, params: { missionId, goal, preset, agents } });
      return Response.json({ missionId, agents, preset }, { headers: cors });
    }

    // REST state
    if (url.pathname.startsWith("/api/state/")) {
      const missionId = url.pathname.slice(11);
      const res = await env.MISSION_ROOM.get(env.MISSION_ROOM.idFromName(missionId)).fetch("http://do/state");
      return new Response(res.body, { headers: { ...cors, "Content-Type": "application/json" } });
    }

    // History
    if (url.pathname === "/api/history") {
      const ledger = JSON.parse((await env.AGENCY_KV.get("titans:ledger")) ?? "[]");
      return Response.json({ history: ledger }, { headers: cors });
    }

    // D1 traces
    if (url.pathname === "/api/traces") {
      const result = await env.AGENCY_DB
        .prepare("SELECT * FROM mission_traces ORDER BY created_at DESC LIMIT 25")
        .all();
      return Response.json({ traces: result.results }, { headers: cors });
    }

    // Health
    if (url.pathname === "/api/health") {
      return Response.json({
        status: "ok", model: env.CLAUDE_MODEL || "claude-sonnet-4-6",
        agents: Object.keys(AGENT_PROMPTS).length,
        presets: Object.keys(PARALLEL_GROUPS), ts: new Date().toISOString(),
      }, { headers: cors });
    }

    // Serve UI
    return new Response(UI_HTML, { headers: { "Content-Type": "text/html;charset=UTF-8" } });
  },
} satisfies ExportedHandler<Env>;

// ── Full UI — canvas swarm + live WebSocket from Cloudflare DO ────────────────

const UI_HTML = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>The Agency — Mission Control</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@700;800&display=swap" rel="stylesheet">
<style>
:root{--bg:#05070d;--b:#1a2234;--b2:#243048;--gold:#c9a84c;--gold2:#f0cc6e;--blue:#4a9eff;--green:#3dd68c;--red:#ff5c5c;--amber:#ffaa33;--purple:#a78bfa;--cyan:#22d3ee;--mono:'Space Mono',monospace;--sans:'Syne',sans-serif}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:#e2e8f0;font-family:var(--sans);overflow:hidden;width:100vw;height:100vh}
canvas{position:fixed;inset:0;z-index:0}
.ui{position:fixed;inset:0;z-index:10;pointer-events:none;display:flex;flex-direction:column}
.top{height:52px;display:flex;align-items:center;justify-content:space-between;padding:0 24px;background:rgba(5,7,13,.93);backdrop-filter:blur(16px);border-bottom:1px solid rgba(201,168,76,.12);pointer-events:all;flex-shrink:0}
.logo{font-size:13px;font-weight:800;letter-spacing:.22em;color:var(--gold);text-transform:uppercase}
.logo-sub{font-family:var(--mono);font-size:10px;color:#4a5568;margin-left:10px}
.mid{display:flex;gap:8px;align-items:center}
.pill{font-family:var(--mono);font-size:10px;padding:3px 10px;border-radius:20px;border:1px solid rgba(255,255,255,.08);color:#4a5568;letter-spacing:.06em;transition:all .3s}
.pill.live{border-color:var(--green);color:var(--green)}.pill.live::before{content:"● ";animation:blink 1s step-end infinite}
.pill.error{border-color:var(--red);color:var(--red)}
@keyframes blink{50%{opacity:0}}
.badges{display:flex;gap:8px}.badge{font-family:var(--mono);font-size:10px;padding:3px 8px;border:1px solid var(--b);border-radius:4px;color:#4a5568}.badge span{color:var(--blue)}
.main{flex:1;display:flex;min-height:0}
.left{width:268px;border-right:1px solid rgba(255,255,255,.05);background:rgba(5,7,13,.75);backdrop-filter:blur(12px);padding:13px;overflow-y:auto;pointer-events:all;display:flex;flex-direction:column;gap:11px;flex-shrink:0}
.plabel{font-family:var(--mono);font-size:9px;letter-spacing:.2em;color:#4a5568;text-transform:uppercase;padding-bottom:5px;border-bottom:1px solid var(--b);margin-bottom:4px}
.form-box{background:rgba(0,0,0,.4);border:1px solid var(--b2);border-radius:8px;padding:12px;position:relative}
.form-box::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,var(--gold),transparent);opacity:.35}
textarea{width:100%;background:rgba(0,0,0,.5);border:1px solid var(--b2);border-radius:5px;padding:8px;font-family:var(--mono);font-size:11px;color:#e2e8f0;outline:none;resize:none;min-height:70px;transition:border-color .2s;line-height:1.6}
textarea:focus{border-color:var(--gold)}textarea::placeholder{color:#4a5568}
.presets{display:flex;gap:5px;margin:7px 0}
.pb{flex:1;padding:5px;background:transparent;border:1px solid var(--b);border-radius:4px;font-family:var(--mono);font-size:9px;color:#4a5568;cursor:pointer;transition:all .2s;text-transform:uppercase;letter-spacing:.05em}
.pb:hover,.pb.active{border-color:var(--gold);color:var(--gold)}
.launch{width:100%;margin-top:6px;padding:9px;background:linear-gradient(135deg,var(--gold),var(--gold2));border:none;border-radius:5px;font-family:var(--sans);font-size:11px;font-weight:800;letter-spacing:.12em;text-transform:uppercase;color:#05070d;cursor:pointer;transition:all .2s}
.launch:hover{transform:translateY(-1px);box-shadow:0 4px 18px rgba(201,168,76,.4)}.launch:disabled{background:var(--b);color:#4a5568;cursor:not-allowed;transform:none;box-shadow:none}
.agent-row{display:flex;align-items:center;gap:7px;padding:4px 0;border-bottom:1px solid rgba(255,255,255,.03)}.agent-row:last-child{border:none}
.adot{width:7px;height:7px;border-radius:50%;background:#1a2234;transition:all .4s;flex-shrink:0}
.adot.ready{background:#243048}.adot.working{background:var(--amber);animation:adp .8s ease-in-out infinite;box-shadow:0 0 7px var(--amber)}.adot.done{background:var(--green);box-shadow:0 0 5px rgba(61,214,140,.4)}.adot.error{background:var(--red)}
@keyframes adp{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.45;transform:scale(.8)}}
.aname{font-family:var(--mono);font-size:10px;color:#8899aa;flex:1}.astate{font-family:var(--mono);font-size:9px;color:#4a5568;text-transform:uppercase}
.hist-item{padding:7px 8px;background:rgba(0,0,0,.3);border:1px solid var(--b);border-radius:5px;margin-bottom:5px}
.hverd{font-family:var(--mono);font-size:8px;font-weight:700;padding:1px 5px;border-radius:3px}
.hverd.GO{background:rgba(61,214,140,.12);color:var(--green)}.hverd.COND{background:rgba(255,170,51,.12);color:var(--amber)}.hverd.NOGO{background:rgba(255,92,92,.12);color:var(--red)}
.hgoal{font-size:10px;color:#8899aa;line-height:1.4;margin-top:3px}.hmeta{font-family:var(--mono);font-size:9px;color:#4a5568;margin-top:2px}
.right{width:306px;border-left:1px solid rgba(255,255,255,.05);background:rgba(5,7,13,.75);backdrop-filter:blur(12px);pointer-events:all;display:flex;flex-direction:column;flex-shrink:0}
.log-head{padding:9px 12px;border-bottom:1px solid rgba(255,255,255,.05);display:flex;justify-content:space-between;align-items:center}
.log-title{font-family:var(--mono);font-size:9px;letter-spacing:.18em;color:#4a5568;text-transform:uppercase}
.log-ct{font-family:var(--mono);font-size:9px;color:var(--gold)}
.log-body{flex:1;overflow-y:auto;padding:9px 10px}.log-body::-webkit-scrollbar{width:3px}.log-body::-webkit-scrollbar-thumb{background:var(--b2);border-radius:2px}
.le{display:flex;gap:7px;margin-bottom:1px;animation:lein .15s ease;font-family:var(--mono);font-size:10px;line-height:1.75}
@keyframes lein{from{opacity:0;transform:translateX(5px)}to{opacity:1;transform:none}}
.lts{color:#4a5568;min-width:50px;flex-shrink:0}.lag{font-weight:700;min-width:72px;flex-shrink:0}
.lag.SYSTEM{color:#4a5568}.lag.ORCHESTRATOR{color:var(--gold)}.lag.PM{color:var(--purple)}.lag.BACKEND{color:var(--blue)}.lag.FRONTEND{color:var(--green)}.lag.SECURITY{color:var(--red)}.lag.QA{color:var(--amber)}.lag.CORE{color:var(--gold2)}.lag.COPYWRITER{color:#f0abfc}.lag.AI{color:var(--cyan)}
.lmsg{color:#4a5568;flex:1;word-break:break-word}.lmsg.agent{color:#8899aa}.lmsg.output{color:#c8d8e8}.lmsg.verdict{color:var(--gold2);font-weight:700}.lmsg.system{color:#4a5568}
.bottom{height:40px;border-top:1px solid rgba(255,255,255,.05);background:rgba(5,7,13,.93);backdrop-filter:blur(16px);display:flex;align-items:center;justify-content:space-between;padding:0 22px;pointer-events:all;flex-shrink:0}
.bm{font-family:var(--mono);font-size:10px;color:#4a5568}.bm span{color:var(--gold2)}
.voverlay{position:fixed;inset:0;z-index:100;display:flex;align-items:center;justify-content:center;background:rgba(5,7,13,.8);backdrop-filter:blur(6px);opacity:0;pointer-events:none;transition:opacity .5s}
.voverlay.show{opacity:1;pointer-events:all}
.vbox{text-align:center;padding:44px 60px;border:1px solid rgba(201,168,76,.2);border-radius:14px;background:rgba(5,7,13,.97);max-width:500px}
.vlabel{font-family:var(--mono);font-size:9px;letter-spacing:.28em;color:#4a5568;text-transform:uppercase;margin-bottom:10px}
.vword{font-size:52px;font-weight:800;line-height:1;letter-spacing:.04em}
.vword.GO{color:var(--green);text-shadow:0 0 50px rgba(61,214,140,.5)}.vword.COND{color:var(--amber);text-shadow:0 0 50px rgba(255,170,51,.4)}.vword.NOGO{color:var(--red);text-shadow:0 0 50px rgba(255,92,92,.4)}
.vsub{font-family:var(--mono);font-size:10px;color:#8899aa;margin-top:10px;line-height:1.7;max-width:360px;margin:10px auto 0}
.vmets{display:flex;gap:20px;justify-content:center;margin-top:14px;font-family:var(--mono);font-size:10px;color:#4a5568}.vmets span{color:var(--gold2)}
.vclose{margin-top:16px;font-family:var(--mono);font-size:10px;color:#4a5568;cursor:pointer;letter-spacing:.1em}.vclose:hover{color:var(--gold)}
</style>
</head>
<body>
<canvas id="c"></canvas>
<div class="ui">
  <div class="top">
    <div style="display:flex;align-items:center">
      <div class="logo">The Agency</div>
      <div class="logo-sub">Mission Control · Cloudflare Edge · Durable Objects</div>
    </div>
    <div class="mid">
      <div class="pill" id="sp">READY</div>
      <div class="pill" id="pp">—</div>
    </div>
    <div class="badges">
      <div class="badge">DO: <span>MissionRoom</span></div>
      <div class="badge">WF: <span>MissionWorkflow</span></div>
      <div class="badge">WS: <span id="wsb">—</span></div>
    </div>
  </div>
  <div class="main">
    <div class="left">
      <div>
        <div class="plabel">Mission</div>
        <div class="form-box">
          <textarea id="goal" rows="3" placeholder="e.g. Build a gold loan LTV calculator API for UAE lenders with tiered ratios per karat and CBUAE compliance..."></textarea>
          <div class="presets">
            <button class="pb active" onclick="sp('full',this)">Full</button>
            <button class="pb" onclick="sp('saas',this)">SaaS</button>
            <button class="pb" onclick="sp('research',this)">Research</button>
          </div>
          <button class="launch" id="lb" onclick="doLaunch()">⚡ LAUNCH</button>
        </div>
      </div>
      <div><div class="plabel">Agents</div><div id="al"></div></div>
      <div><div class="plabel">Mission History</div><div id="hl"><div style="font-family:var(--mono);font-size:10px;color:#4a5568">Loading...</div></div></div>
    </div>
    <div style="flex:1"></div>
    <div class="right">
      <div class="log-head"><div class="log-title">// Live · Cloudflare DO WebSocket</div><div class="log-ct" id="lct">0 lines</div></div>
      <div class="log-body" id="lb2">
        <div class="le"><span class="lts">--:--:--</span><span class="lag SYSTEM">SYSTEM</span><span class="lmsg system">Mission Control online. Connected to Cloudflare Edge. Enter a mission goal and press LAUNCH.</span></div>
      </div>
    </div>
  </div>
  <div class="bottom">
    <div class="bm">Mission: <span id="bmg">—</span></div>
    <div style="display:flex;gap:18px">
      <div class="bm">Tokens: <span id="bmt">0</span></div>
      <div class="bm">Cost: <span id="bmc">$0.0000</span></div>
      <div class="bm">Time: <span id="bms">—</span></div>
    </div>
  </div>
</div>
<div class="voverlay" id="vo">
  <div class="vbox">
    <div class="vlabel">// Claude Reasoning Core · Cloudflare Workers Edge</div>
    <div class="vword" id="vw">—</div>
    <div class="vsub" id="vs"></div>
    <div class="vmets"><div>Tokens: <span id="vmt">—</span></div><div>Cost: <span id="vmc">—</span></div><div>Time: <span id="vms">—</span></div></div>
    <div class="vclose" onclick="document.getElementById('vo').classList.remove('show')">[ DISMISS ]</div>
  </div>
</div>
<script>
const PA={full:['pm','backend','frontend','security','qa','core'],saas:['pm','copywriter','frontend','qa','core'],research:['pm','ai','qa','core']};
const CO={pm:'#a78bfa',backend:'#4a9eff',frontend:'#3dd68c',security:'#ff5c5c',qa:'#ffaa33',core:'#f0cc6e',copywriter:'#f0abfc',ai:'#22d3ee',orchestrator:'#c9a84c'};
const EM={pm:'📋',backend:'⚙️',frontend:'🎨',security:'🔒',qa:'🧪',core:'🧠',copywriter:'✍️',ai:'🤖',orchestrator:'🧠'};
let preset='full',ws=null,mid=null,sat=null,ll=0;
let W,H,nodes={},pkts=[],parts=[],ambs=[];
const cv=document.getElementById('c'),cx=cv.getContext('2d');

function ha(h,a){const r=parseInt(h.slice(1,3),16),g=parseInt(h.slice(3,5),16),b=parseInt(h.slice(5,7),16);return \`rgba(\${r},\${g},\${b},\${a})\`;}
class Nd{constructor(n,x,y,c){this.n=n;this.x=x;this.y=y;this.c=c;this.st='idle';this.p=0;this.gl=0;this.sz=n==='orchestrator'?46:34;}
set(s){this.st=s;this.gl=s==='working'?1:s==='done'?.4:0;}
upd(dt){this.p=(this.p+dt*2.2)%(Math.PI*2);if(this.st==='working')this.gl=.58+Math.sin(this.p)*.38;}
draw(){const{x,y,sz,c,st,gl}=this;
if(gl>0){const g=cx.createRadialGradient(x,y,0,x,y,sz*2.8);g.addColorStop(0,ha(c,gl*.27));g.addColorStop(1,'transparent');cx.fillStyle=g;cx.beginPath();cx.arc(x,y,sz*2.8,0,Math.PI*2);cx.fill();}
if(st==='working'){cx.strokeStyle=ha(c,.3);cx.lineWidth=1.5;cx.beginPath();cx.arc(x,y,sz+9+Math.sin(this.p)*5,0,Math.PI*2);cx.stroke();}
const gr=cx.createRadialGradient(x-sz*.2,y-sz*.2,0,x,y,sz);const al=st==='idle'?.1:st==='done'?.42:.62;
gr.addColorStop(0,ha(c,al+.15));gr.addColorStop(1,ha(c,al*.3));
cx.fillStyle=gr;cx.strokeStyle=ha(c,st==='idle'?.18:.72);cx.lineWidth=st==='working'?2:1.5;
cx.beginPath();cx.arc(x,y,sz,0,Math.PI*2);cx.fill();cx.stroke();
cx.fillStyle=ha(c,st==='idle'?.27:1);cx.beginPath();cx.arc(x,y,3.5,0,Math.PI*2);cx.fill();
cx.font=\`\${sz*.5}px serif\`;cx.textAlign='center';cx.textBaseline='middle';cx.globalAlpha=st==='idle'?.32:1;cx.fillText(EM[this.n]||'🤖',x,y-3);cx.globalAlpha=1;
cx.font='bold 10px monospace';cx.fillStyle=ha(c,st==='idle'?.36:.88);cx.textBaseline='top';cx.fillText(this.n.toUpperCase(),x,y+sz+5);}}
class Pk{constructor(f,t,c){this.f=f;this.t=t;this.c=c;this.p=0;this.sp=.3+Math.random()*.28;this.done=false;this.tr=[];this.sz=3.5+Math.random()*3;}
upd(dt){this.p=Math.min(1,this.p+dt*this.sp);const fn=nodes[this.f],tn=nodes[this.t];if(!fn||!tn)return;
const bcx=(fn.x+tn.x)/2+(tn.y-fn.y)*.27,bcy=(fn.y+tn.y)/2-Math.abs(tn.x-fn.x)*.2,t=this.p;
this.x=(1-t)*(1-t)*fn.x+2*(1-t)*t*bcx+t*t*tn.x;this.y=(1-t)*(1-t)*fn.y+2*(1-t)*t*bcy+t*t*tn.y;
this.tr.push({x:this.x,y:this.y});if(this.tr.length>14)this.tr.shift();
if(this.p>=1){this.done=true;burst(this.x,this.y,this.c);}}
draw(){if(!this.x)return;
for(let i=1;i<this.tr.length;i++){cx.strokeStyle=ha(this.c,(i/this.tr.length)*.5);cx.lineWidth=(i/this.tr.length)*this.sz*.7;cx.lineCap='round';cx.beginPath();cx.moveTo(this.tr[i-1].x,this.tr[i-1].y);cx.lineTo(this.tr[i].x,this.tr[i].y);cx.stroke();}
const g=cx.createRadialGradient(this.x,this.y,0,this.x,this.y,this.sz*2.4);g.addColorStop(0,ha(this.c,.9));g.addColorStop(1,'transparent');cx.fillStyle=g;cx.beginPath();cx.arc(this.x,this.y,this.sz*2.4,0,Math.PI*2);cx.fill();cx.fillStyle='rgba(255,255,255,.9)';cx.beginPath();cx.arc(this.x,this.y,this.sz*.4,0,Math.PI*2);cx.fill();}}
class Pr{constructor(x,y,c){this.x=x;this.y=y;this.vx=(Math.random()-.5)*95;this.vy=(Math.random()-.5)*95;this.life=1;this.dc=2+Math.random();this.sz=2+Math.random()*3;this.c=c;}
upd(dt){this.x+=this.vx*dt;this.y+=this.vy*dt;this.vx*=.93;this.vy*=.93;this.life-=this.dc*dt;}
draw(){cx.fillStyle=ha(this.c,this.life*.7);cx.beginPath();cx.arc(this.x,this.y,this.sz*this.life,0,Math.PI*2);cx.fill();}}
function burst(x,y,c){for(let i=0;i<9;i++)parts.push(new Pr(x,y,c));}

function layoutNodes(){nodes={};const bcx=W/2,bcy=H/2;nodes.orchestrator=new Nd('orchestrator',bcx,bcy,CO.orchestrator);nodes.orchestrator.set('ready');const s=PA[preset],r=Math.min(W,H)*.31;s.forEach((n,i)=>{const a=-Math.PI/2+(i/s.length)*Math.PI*2;nodes[n]=new Nd(n,bcx+Math.cos(a)*r,bcy+Math.sin(a)*r,CO[n]||'#8899aa');});}
function initAmbs(){ambs=[];for(let i=0;i<52;i++)ambs.push({x:Math.random()*W,y:Math.random()*H,vx:(Math.random()-.5)*7,vy:(Math.random()-.5)*7,r:Math.random()*1.4,a:Math.random()*.11});}
function drawGrid(){cx.strokeStyle='rgba(255,255,255,.017)';cx.lineWidth=1;const s=60;for(let x=0;x<W;x+=s){cx.beginPath();cx.moveTo(x,0);cx.lineTo(x,H);cx.stroke();}for(let y=0;y<H;y+=s){cx.beginPath();cx.moveTo(0,y);cx.lineTo(W,y);cx.stroke();}}
let last=0;
function loop(ts){const dt=Math.min((ts-last)/1000,.05);last=ts;
cx.clearRect(0,0,W,H);const bg=cx.createRadialGradient(W/2,H/2,0,W/2,H/2,Math.max(W,H)*.7);bg.addColorStop(0,'#070b14');bg.addColorStop(1,'#05070d');cx.fillStyle=bg;cx.fillRect(0,0,W,H);
drawGrid();ambs.forEach(p=>{p.x=(p.x+p.vx*dt+W)%W;p.y=(p.y+p.vy*dt+H)%H;cx.fillStyle=\`rgba(201,168,76,\${p.a})\`;cx.beginPath();cx.arc(p.x,p.y,p.r,0,Math.PI*2);cx.fill();});
PA[preset].forEach(s=>{const fn=nodes.orchestrator,tn=nodes[s];if(!fn||!tn)return;const ac=tn.st==='working'||tn.st==='done';cx.strokeStyle=ac?ha(tn.c,.18):'rgba(255,255,255,.025)';cx.lineWidth=ac?1.5:1;cx.setLineDash(ac?[]:[3,8]);cx.beginPath();cx.moveTo(fn.x,fn.y);cx.lineTo(tn.x,tn.y);cx.stroke();cx.setLineDash([]);});
Object.values(nodes).forEach(n=>n.upd(dt));pkts=pkts.filter(p=>{p.upd(dt);return!p.done;});parts=parts.filter(p=>{p.upd(dt);return p.life>0;});pkts.forEach(p=>p.draw());parts.forEach(p=>p.draw());Object.values(nodes).forEach(n=>n.draw());
if(mid&&Math.random()<.03){const wn=Object.keys(nodes).filter(k=>nodes[k].st==='working');if(wn.length)pkts.push(new Pk('orchestrator',wn[Math.floor(Math.random()*wn.length)],CO.orchestrator));}
if(sat)document.getElementById('bms').textContent=(((Date.now()-sat)/1000).toFixed(1))+'s';
requestAnimationFrame(loop);}
function resize(){W=cv.width=window.innerWidth;H=cv.height=window.innerHeight;layoutNodes();initAmbs();}
window.addEventListener('resize',resize);resize();last=performance.now();requestAnimationFrame(loop);

function sp(p,btn){preset=p;document.querySelectorAll('.pb').forEach(b=>b.classList.remove('active'));btn.classList.add('active');renderAg();layoutNodes();}
function renderAg(){const el=document.getElementById('al');el.innerHTML=PA[preset].map(a=>\`<div class="agent-row"><div class="adot" id="ad-\${a}"></div><div class="aname">\${EM[a]||'🤖'} \${a}</div><div class="astate" id="as-\${a}">idle</div></div>\`).join('');}
renderAg();
function setAg(a,s){const d=document.getElementById('ad-'+a),l=document.getElementById('as-'+a);if(!d)return;d.className='adot '+s;l.textContent=s;l.style.color=s==='working'?'var(--amber)':s==='done'?'var(--green)':s==='error'?'var(--red)':'#4a5568';if(nodes[a])nodes[a].set(s);}
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function addLog(agent,msg,kind='agent'){const el=document.getElementById('lb2');const d=document.createElement('div');d.className='le';const ts=new Date().toTimeString().slice(0,8);d.innerHTML=\`<span class="lts">\${ts}</span><span class="lag \${agent.toUpperCase()}">\${agent.toUpperCase()}</span><span class="lmsg \${kind}">\${esc(msg)}</span>\`;el.appendChild(d);el.scrollTop=el.scrollHeight;ll++;document.getElementById('lct').textContent=ll+' lines';}

async function loadHistory(){try{const r=await fetch('/api/history');const{history}=await r.json();const el=document.getElementById('hl');if(!history?.length){el.innerHTML='<div style="font-family:var(--mono);font-size:10px;color:#4a5568">No missions yet.</div>';return;}el.innerHTML=history.slice(0,5).map(h=>{const vc=h.verdict==='GO'?'GO':h.verdict?.includes('COND')?'COND':'NOGO';return\`<div class="hist-item"><div style="display:flex;justify-content:space-between"><span class="hverd \${vc}">\${h.verdict||'?'}</span><span style="font-family:var(--mono);font-size:9px;color:#4a5568">\${(h.ts||'').slice(0,10)}</span></div><div class="hgoal">\${esc((h.goal||'').slice(0,55))}</div><div class="hmeta">surprise=\${(h.surprise||0).toFixed(2)}</div></div>\`;}).join('');}catch(e){}}
loadHistory();

function connectWS(missionId){
if(ws)ws.close();
const proto=location.protocol==='https:'?'wss':'ws';
ws=new WebSocket(\`\${proto}://\${location.host}/ws/\${missionId}\`);
document.getElementById('wsb').textContent='connecting...';
ws.onopen=()=>{document.getElementById('wsb').textContent='live ●';document.getElementById('sp').className='pill live';document.getElementById('sp').textContent='RUNNING';};
ws.onmessage=e=>{
const ev=JSON.parse(e.data);
if(ev.type==='snapshot'){if(ev.payload.logs)ev.payload.logs.forEach(l=>addLog(l.agent,l.msg,l.kind||'agent'));if(ev.payload.agentStatuses)Object.entries(ev.payload.agentStatuses).forEach(([a,s])=>setAg(a,s));if(ev.payload.metrics){const m=ev.payload.metrics;if(m.tokensIn)document.getElementById('bmt').textContent=((+m.tokensIn||0)+(+m.tokensOut||0)).toLocaleString();if(m.costUsd)document.getElementById('bmc').textContent='$'+m.costUsd;}return;}
if(ev.type==='log'){const l=ev.payload;addLog(l.agent,l.msg,l.kind||'agent');if(l.msg.includes('Phase'))document.getElementById('pp').textContent='PHASE '+(l.msg.match(/Phase (\\d+)/)?.[1]||'');}
if(ev.type==='agent_status')setAg(ev.payload.agent,ev.payload.status);
if(ev.type==='metrics'){const m=ev.payload;if(m.tokensIn!=null)document.getElementById('bmt').textContent=((+m.tokensIn||0)+(+m.tokensOut||0)).toLocaleString();if(m.costUsd)document.getElementById('bmc').textContent='$'+m.costUsd;}
if(ev.type==='verdict'){
const v=ev.payload.verdict;const vc=v==='GO'?'GO':v.includes('COND')?'COND':'NOGO';
document.getElementById('vw').textContent=v;document.getElementById('vw').className='vword '+vc;
const subs={GO:'Mission cleared by Claude Reasoning Core. All outputs aligned. Ship to staging.',COND:'Conditional approval issued. Review blockers before launch.','NO-GO':'Mission blocked. Critical issues must be resolved first.'};
document.getElementById('vs').textContent=subs[v]||subs.COND;
document.getElementById('vmt').textContent=document.getElementById('bmt').textContent;document.getElementById('vmc').textContent=document.getElementById('bmc').textContent;document.getElementById('vms').textContent=document.getElementById('bms').textContent;
document.getElementById('vo').classList.add('show');
document.getElementById('sp').textContent='COMPLETE';document.getElementById('lb').disabled=false;document.getElementById('lb').textContent='⚡ LAUNCH';
PA[preset].forEach(a=>setAg(a,'done'));if(nodes.orchestrator)nodes.orchestrator.set('done');loadHistory();ws.close();}};
ws.onerror=()=>{document.getElementById('wsb').textContent='error';document.getElementById('sp').className='pill error';};
ws.onclose=()=>{if(document.getElementById('wsb').textContent==='live ●')document.getElementById('wsb').textContent='closed';};}

async function doLaunch(){
const goal=document.getElementById('goal').value.trim();
if(!goal){addLog('SYSTEM','Please enter a mission goal.','system');return;}
document.getElementById('lb').disabled=true;document.getElementById('lb').textContent='⏳ LAUNCHING...';
document.getElementById('lb2').innerHTML='';ll=0;
PA[preset].forEach(a=>setAg(a,'ready'));if(nodes.orchestrator)nodes.orchestrator.set('working');
sat=Date.now();document.getElementById('bmg').textContent=goal.slice(0,36)+'...';
try{
const r=await fetch('/api/launch',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({goal,preset})});
const data=await r.json();
if(data.error)throw new Error(data.error);
mid=data.missionId;
addLog('SYSTEM',\`Launched \${mid} on Cloudflare Edge\`,'system');
addLog('SYSTEM',\`Agents: \${data.agents.join(', ')}\`,'system');
connectWS(mid);
}catch(err){addLog('SYSTEM','Launch failed: '+err.message,'system');document.getElementById('lb').disabled=false;document.getElementById('lb').textContent='⚡ LAUNCH';}}
</script>
</body>
</html>`;
