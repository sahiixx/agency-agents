#!/usr/bin/env python3
"""
live_server.py — Watch The Agency run live in your browser.

Starts a local HTTP server on port 7777 that:
  - Serves the live viewer UI at http://localhost:7777
  - Streams real Claude output via Server-Sent Events (SSE)
  - Runs actual missions via agency.py with your API key
  - Shows per-agent status, token counts, cost, A2A activity in real time

Usage:
  ANTHROPIC_API_KEY="sk-ant-..." python3 live_server.py
  Then open: http://localhost:7777
"""

import os, sys, json, time, threading, queue, traceback
from pathlib import Path
from datetime import datetime, timezone

# ── Path setup ────────────────────────────────────────────────────────────────
REPO = Path(__file__).parent.resolve()
sys.path.insert(0, str(REPO / "deepagents/libs/deepagents"))
sys.path.insert(0, str(REPO))

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, StreamingResponse, JSONResponse
from starlette.routing import Route
from starlette.staticfiles import StaticFiles
import uvicorn

# ── Event bus (thread-safe) ───────────────────────────────────────────────────
_clients: list[queue.Queue] = []
_lock = threading.Lock()

def broadcast(event_type: str, data: dict):
    msg = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
    with _lock:
        dead = []
        for q in _clients:
            try:
                q.put_nowait(msg)
            except queue.Full:
                dead.append(q)
        for q in dead:
            _clients.remove(q)

def log(agent: str, msg: str, kind: str = "log"):
    broadcast("log", {
        "ts":    datetime.now(timezone.utc).strftime("%H:%M:%S"),
        "agent": agent,
        "msg":   msg,
        "kind":  kind,
    })
    print(f"  [{agent}] {msg}")

def status(agent: str, state: str):
    broadcast("status", {"agent": agent, "state": state})

def metric(key: str, value):
    broadcast("metric", {"key": key, "value": value})

def verdict_event(v: str, text: str):
    broadcast("verdict", {"verdict": v, "text": text[:600]})

# ── Mission runner (background thread) ────────────────────────────────────────
_mission_running = False

def run_mission_live(mission: str, preset: str, api_key: str):
    global _mission_running
    if _mission_running:
        log("SYSTEM", "Mission already running — please wait", "warn")
        return
    _mission_running = True

    try:
        import warnings; warnings.filterwarnings("ignore")
        os.environ["ANTHROPIC_API_KEY"] = api_key

        from deepagents import create_deep_agent
        from deepagents.backends import FilesystemBackend
        from langchain_anthropic import ChatAnthropic
        from langchain_core.messages import HumanMessage
        from memory.titans_memory import TitansMemory
        from mcp_tools import MCP_TOOLS
        from observability import AgencyTracer
        from a2a_protocol import start_agency_a2a_servers, make_a2a_tools
        import agency

        log("SYSTEM", f"Mission: {mission[:80]}", "system")
        log("SYSTEM", f"Preset: {preset} | Model: claude-sonnet-4-6", "system")
        broadcast("mission_start", {"mission": mission, "preset": preset})

        llm    = ChatAnthropic(model="claude-sonnet-4-6", api_key=api_key,
                               streaming=True)
        tracer = AgencyTracer(mission=mission, preset=preset)
        groups = agency.PARALLEL_GROUPS.get(preset, [["pm"], ["core"]])
        agents = [a for g in groups for a in g]

        # A2A servers
        log("SYSTEM", "Starting A2A servers...", "system")
        port_map  = start_agency_a2a_servers(agents, agency.AGENT_REGISTRY, REPO)
        time.sleep(0.5)
        a2a_tools = make_a2a_tools([f"http://localhost:{p}" for p in port_map.values()])
        all_tools  = MCP_TOOLS + a2a_tools
        for name, port in port_map.items():
            log("A2A", f"{name} → http://localhost:{port}", "a2a")
        metric("a2a_count", len(port_map))
        metric("tool_count", len(all_tools))

        # Subagents
        specialist_names = [n for n in agents if n != "core"]
        subagents = []
        for name in specialist_names:
            path, desc = agency.AGENT_REGISTRY[name]
            sp = (REPO / path).read_text() if (REPO / path).exists() else f"# {name}"
            subagents.append({"name": name, "description": desc,
                               "system_prompt": sp, "tools": all_tools, "model": llm})
            status(name, "ready")
            log(name, f"Loaded — {len(sp):,} chars | {len(all_tools)} tools", "agent")

        # Graph
        log("SYSTEM", "Building LangGraph orchestrator...", "system")
        fs = FilesystemBackend(root_dir=str(REPO), virtual_mode=False)
        core_sp = (REPO / agency.AGENT_REGISTRY["core"][0]).read_text()
        orch = create_deep_agent(
            model=llm, tools=all_tools, system_prompt=core_sp,
            subagents=subagents, memory=[agency.MEMORY_FILE],
            backend=fs, name="live-agency",
        )
        log("SYSTEM", f"Graph ready — {len(orch.nodes)} nodes wired", "system")
        metric("graph_nodes", len(orch.nodes))

        # Brief
        group_plan = " → ".join(
            f"[{' ∥ '.join(g)}]" if len(g) > 1 else g[0]
            for g in groups
        )
        a2a_map = "\n".join(f"  {n} → http://localhost:{p}" for n, p in port_map.items())
        brief = f"""MISSION: {mission}

PARALLEL PLAN: {group_plan}
A2A SERVERS:\n{a2a_map}
MCP TOOLS: web_search, read_file, write_output, code_lint, memory_recall, get_datetime

Instructions:
1. Follow the parallel phase plan
2. Use web_search for current data
3. Use memory_recall for past missions
4. Use write_output to save deliverable
5. Constitutional review: accuracy, safety, completeness
6. Return final verdict: GO / CONDITIONAL GO / NO-GO

Delegate everything. You are the orchestrator and final judge."""

        # Run
        log("SYSTEM", "Firing orchestrator — Claude is live ⚡", "system")
        for g in groups:
            for a in g:
                status(a, "working")

        t0 = time.time()
        with tracer.span("full"):
            response = orch.invoke(
                {"messages": [HumanMessage(content=brief)]},
                config={"recursion_limit": 50},
            )
            final = response["messages"][-1].content
            tracer.add_tokens(
                input_tokens=sum(len(getattr(m, "content", "") or "") // 4
                               for m in response["messages"]),
                output_tokens=len(final) // 4,
            )

        elapsed = time.time() - t0
        metric("elapsed", round(elapsed, 1))

        # Stream final output line by line
        log("CORE", "━━━ REASONING CORE OUTPUT ━━━", "verdict_header")
        for line in final.split("\n"):
            if line.strip():
                log("CORE", line, "output")
                time.sleep(0.03)

        # Verdict
        v = (
            "NO-GO"          if "no-go"       in final.lower() and "conditional" not in final.lower() else
            "CONDITIONAL GO" if "conditional" in final.lower() else
            "GO"
        )
        verdict_event(v, final)
        for a in agents:
            status(a, "done")

        # Observability
        tracer.finish(v)
        tin, tout = tracer.total_tokens
        metric("tokens_in",  tin)
        metric("tokens_out", tout)
        metric("cost_usd",   round(tracer.total_cost_usd, 4))
        metric("verdict",    v)

        log("SYSTEM", f"Verdict: {v} | {elapsed:.1f}s | ${tracer.total_cost_usd:.4f} | {tin+tout:,} tokens", "system")

        # Titans memory
        mem     = TitansMemory()
        outcome = mem.record_outcome(mission, v)
        mem.inject_into_agents_md()
        log("MEMORY", f"Titans updated — surprise={outcome.surprise:.2f} | {mem.summary()}", "memory")

        trace_path = tracer.save_trace()
        log("SYSTEM", f"Trace saved: {trace_path}", "system")
        broadcast("mission_end", {"verdict": v, "elapsed": elapsed})

    except Exception as e:
        log("SYSTEM", f"ERROR: {type(e).__name__}: {e}", "error")
        broadcast("error", {"message": str(e), "trace": traceback.format_exc()})
    finally:
        _mission_running = False

# ── HTTP handlers ─────────────────────────────────────────────────────────────

async def sse_stream(request: Request):
    q: queue.Queue = queue.Queue(maxsize=200)
    with _lock:
        _clients.append(q)

    async def generate():
        yield "data: {\"type\":\"connected\"}\n\n"
        while True:
            try:
                msg = q.get(timeout=20)
                yield msg
            except queue.Empty:
                yield ": keepalive\n\n"
            except GeneratorExit:
                break

    return StreamingResponse(generate(), media_type="text/event-stream",
                              headers={"Cache-Control": "no-cache",
                                       "X-Accel-Buffering": "no"})


async def launch(request: Request):
    body     = await request.json()
    mission  = body.get("mission", "").strip()
    preset   = body.get("preset",  "full")
    api_key  = body.get("api_key", os.environ.get("ANTHROPIC_API_KEY", ""))

    if not mission:
        return JSONResponse({"error": "Mission required"}, status_code=400)
    if not api_key or not api_key.startswith("sk-ant-"):
        return JSONResponse({"error": "Valid ANTHROPIC_API_KEY required"}, status_code=400)

    t = threading.Thread(
        target=run_mission_live,
        args=(mission, preset, api_key),
        daemon=True,
    )
    t.start()
    return JSONResponse({"status": "launched", "mission": mission})


async def health(request: Request):
    return JSONResponse({
        "status":   "ok",
        "running":  _mission_running,
        "clients":  len(_clients),
        "model":    "claude-sonnet-4-6",
    })


async def index(request: Request):
    return HTMLResponse(HTML)


# ── UI HTML ───────────────────────────────────────────────────────────────────

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>The Agency — Live</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@700;800&display=swap" rel="stylesheet">
<style>
:root {
  --bg:#060810; --s:#0c1018; --b:#1a2234; --b2:#243048;
  --gold:#c9a84c; --gold2:#f0cc6e; --blue:#4a9eff; --green:#3dd68c;
  --red:#ff5c5c; --amber:#ffaa33; --muted:#4a5568; --text:#e2e8f0; --text2:#8899aa;
  --mono:'Space Mono',monospace; --sans:'Syne',sans-serif;
}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--text);font-family:var(--sans);min-height:100vh;overflow-x:hidden}

/* noise */
body::after{content:'';position:fixed;inset:0;background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.035'/%3E%3C/svg%3E");pointer-events:none;z-index:999;opacity:.4}

/* topbar */
.top{display:flex;align-items:center;justify-content:space-between;padding:0 28px;height:52px;border-bottom:1px solid var(--b);background:rgba(6,8,16,.96);backdrop-filter:blur(12px);position:sticky;top:0;z-index:100}
.logo{font-size:13px;font-weight:800;letter-spacing:.25em;color:var(--gold);text-transform:uppercase}
.logo-tag{font-family:var(--mono);font-size:10px;color:var(--text2);letter-spacing:.08em}
.live-badge{display:flex;align-items:center;gap:6px;padding:3px 10px;border:1px solid var(--red);border-radius:20px;font-family:var(--mono);font-size:10px;color:var(--red);letter-spacing:.1em}
.live-dot{width:6px;height:6px;border-radius:50%;background:var(--red);animation:pulse 1s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.4;transform:scale(.8)}}
.top-right{display:flex;gap:12px;align-items:center}
.badge{font-family:var(--mono);font-size:10px;color:var(--text2);padding:3px 8px;border:1px solid var(--b);border-radius:4px}
.badge span{color:var(--blue)}

/* layout */
.layout{display:grid;grid-template-columns:260px 1fr 280px;min-height:calc(100vh - 52px)}

/* left */
.left{border-right:1px solid var(--b);padding:20px 0;overflow-y:auto}
.sec{padding:0 16px 20px}
.sec-label{font-family:var(--mono);font-size:9px;letter-spacing:.2em;color:var(--muted);text-transform:uppercase;padding-bottom:8px;margin-bottom:10px;border-bottom:1px solid var(--b)}

/* mission form */
.form-area{background:var(--s);border:1px solid var(--b2);border-radius:8px;padding:16px;position:relative;overflow:hidden}
.form-area::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,var(--gold),transparent);opacity:.5}
.form-label{font-family:var(--mono);font-size:9px;letter-spacing:.15em;color:var(--muted);text-transform:uppercase;margin-bottom:8px}
textarea{width:100%;background:var(--bg);border:1px solid var(--b2);border-radius:5px;padding:10px;font-family:var(--mono);font-size:11px;color:var(--text);outline:none;resize:none;min-height:70px;transition:border-color .2s;line-height:1.6}
textarea:focus{border-color:var(--gold)}
textarea::placeholder{color:var(--muted)}

.key-input{width:100%;background:var(--bg);border:1px solid var(--b2);border-radius:5px;padding:8px 10px;font-family:var(--mono);font-size:11px;color:var(--text);outline:none;margin-top:8px;transition:border-color .2s}
.key-input:focus{border-color:var(--gold)}
.key-input::placeholder{color:var(--muted)}

.presets{display:flex;gap:6px;margin:8px 0}
.preset-btn{flex:1;padding:6px 4px;background:var(--bg);border:1px solid var(--b);border-radius:4px;font-family:var(--mono);font-size:9px;color:var(--text2);cursor:pointer;transition:all .2s;text-transform:uppercase;letter-spacing:.05em}
.preset-btn:hover,.preset-btn.active{border-color:var(--gold);color:var(--gold)}
.launch-btn{width:100%;margin-top:8px;padding:10px;background:linear-gradient(135deg,var(--gold),var(--gold2));border:none;border-radius:5px;font-family:var(--sans);font-size:12px;font-weight:800;letter-spacing:.12em;text-transform:uppercase;color:var(--bg);cursor:pointer;transition:all .2s}
.launch-btn:hover{transform:translateY(-1px);box-shadow:0 4px 20px rgba(201,168,76,.4)}
.launch-btn:disabled{background:var(--b);color:var(--muted);cursor:not-allowed;transform:none;box-shadow:none}

/* agent status */
.agent-row{display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid var(--b)}
.agent-row:last-child{border:none}
.agent-dot{width:8px;height:8px;border-radius:50%;background:var(--muted);transition:all .4s;flex-shrink:0}
.agent-dot.ready{background:var(--b2)}
.agent-dot.working{background:var(--amber);animation:pulse .8s ease-in-out infinite;box-shadow:0 0 8px var(--amber)}
.agent-dot.done{background:var(--green)}
.agent-dot.error{background:var(--red)}
.agent-name{font-family:var(--mono);font-size:10px;color:var(--text2);flex:1}
.agent-state{font-family:var(--mono);font-size:9px;color:var(--muted);text-transform:uppercase}

/* center — terminal */
.center{padding:20px 24px;display:flex;flex-direction:column;gap:16px}
.terminal{background:var(--s);border:1px solid var(--b);border-radius:10px;flex:1;min-height:0;overflow:hidden;display:flex;flex-direction:column}
.term-bar{display:flex;align-items:center;gap:8px;padding:9px 14px;border-bottom:1px solid var(--b);background:rgba(0,0,0,.3);flex-shrink:0}
.td{width:10px;height:10px;border-radius:50%}
.term-label{font-family:var(--mono);font-size:10px;color:var(--muted);margin-left:6px;letter-spacing:.1em;flex:1}
.term-count{font-family:var(--mono);font-size:9px;color:var(--muted)}
.term-body{padding:14px;font-family:var(--mono);font-size:12px;line-height:1.8;color:var(--text2);overflow-y:auto;flex:1;max-height:calc(100vh - 280px)}
.term-body::-webkit-scrollbar{width:3px}
.term-body::-webkit-scrollbar-thumb{background:var(--b2);border-radius:2px}

.log{display:flex;gap:10px;margin-bottom:1px;animation:fadeIn .15s ease}
@keyframes fadeIn{from{opacity:0;transform:translateX(-4px)}to{opacity:1;transform:none}}
.log-ts{color:var(--muted);min-width:58px;font-size:11px}
.log-ag{min-width:80px;font-weight:700;font-size:11px}
.log-ag.SYSTEM{color:var(--muted)}
.log-ag.CORE{color:var(--gold2)}
.log-ag.A2A{color:var(--blue)}
.log-ag.MEMORY{color:#a78bfa}
.log-ag.pm{color:#a78bfa}
.log-ag.backend{color:var(--blue)}
.log-ag.frontend{color:var(--green)}
.log-ag.security{color:var(--red)}
.log-ag.qa{color:var(--amber)}
.log-msg{flex:1;font-size:11px}
.log-msg.system{color:#5a6a80}
.log-msg.a2a{color:var(--blue)}
.log-msg.memory{color:#a78bfa}
.log-msg.output{color:var(--text)}
.log-msg.error{color:var(--red)}
.log-msg.warn{color:var(--amber)}
.log-msg.verdict_header{color:var(--gold);font-weight:700}
.cursor{display:inline-block;width:7px;height:13px;background:var(--gold);margin-left:2px;vertical-align:middle;animation:blink 1s step-end infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:0}}

/* right */
.right{border-left:1px solid var(--b);padding:20px;overflow-y:auto;display:flex;flex-direction:column;gap:18px}

/* verdict */
.verdict-box{text-align:center;padding:18px 0}
.verdict-label{font-family:var(--mono);font-size:9px;letter-spacing:.2em;color:var(--muted);text-transform:uppercase;margin-bottom:10px}
.verdict-text{font-family:var(--sans);font-size:32px;font-weight:800;letter-spacing:.05em}
.verdict-text.GO{color:var(--green);text-shadow:0 0 30px rgba(61,214,140,.4)}
.verdict-text.CONDITIONAL{color:var(--amber);text-shadow:0 0 30px rgba(255,170,51,.3)}
.verdict-text.NO-GO{color:var(--red);text-shadow:0 0 30px rgba(255,92,92,.3)}
.verdict-text.PENDING{color:var(--muted)}

/* metrics */
.metric-row{display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid var(--b)}
.metric-row:last-child{border:none}
.metric-k{font-size:11px;color:var(--text2)}
.metric-v{font-family:var(--mono);font-size:11px;font-weight:700;color:var(--green)}
.metric-v.amber{color:var(--amber)}
.metric-v.blue{color:var(--blue)}

/* a2a map */
.a2a-row{font-family:var(--mono);font-size:10px;color:var(--text2);padding:4px 0;border-bottom:1px solid var(--b);display:flex;justify-content:space-between}
.a2a-row:last-child{border:none}
.a2a-port{color:var(--blue)}

/* scrollbar */
::-webkit-scrollbar{width:3px;height:3px}
::-webkit-scrollbar-thumb{background:var(--b2);border-radius:2px}
</style>
</head>
<body>

<div class="top">
  <div style="display:flex;align-items:center;gap:12px">
    <div class="logo">The Agency</div>
    <div class="logo-tag">Live Watch · Claude Sonnet 4.6</div>
  </div>
  <div class="live-badge"><div class="live-dot"></div><span id="live-label">OFFLINE</span></div>
  <div class="top-right">
    <div class="badge">Model: <span>claude-sonnet-4-6</span></div>
    <div class="badge">A2A: <span id="a2a-badge">—</span></div>
    <div class="badge">Tools: <span id="tools-badge">—</span></div>
  </div>
</div>

<div class="layout">

  <!-- LEFT -->
  <aside class="left">
    <div class="sec">
      <div class="sec-label">Mission</div>
      <div class="form-area">
        <div class="form-label">// Goal</div>
        <textarea id="mission-input" rows="3" placeholder="Describe the mission...">Design a production-ready gold loan LTV calculator API for UAE lenders with tiered ratios for 18K/21K/22K/24K gold, real-time price feed, and CBUAE compliance checks.</textarea>
        <input class="key-input" id="key-input" type="password" placeholder="sk-ant-... (your Anthropic API key)">
        <div class="presets">
          <button class="preset-btn active" onclick="setPreset('full',this)">Full</button>
          <button class="preset-btn" onclick="setPreset('saas',this)">SaaS</button>
          <button class="preset-btn" onclick="setPreset('research',this)">Research</button>
        </div>
        <button class="launch-btn" id="launch-btn" onclick="launch()">⚡ LAUNCH LIVE</button>
      </div>
    </div>

    <div class="sec">
      <div class="sec-label">Agent Status</div>
      <div id="agent-statuses"></div>
    </div>
  </aside>

  <!-- CENTER -->
  <main class="center">
    <div class="terminal" style="flex:1">
      <div class="term-bar">
        <div class="td" style="background:#ff5f57"></div>
        <div class="td" style="background:#febc2e"></div>
        <div class="td" style="background:#28c840"></div>
        <div class="term-label">LIVE STREAM — Real Claude Output</div>
        <div class="term-count" id="log-count">0 lines</div>
      </div>
      <div class="term-body" id="terminal">
        <div class="log">
          <span class="log-ts">--:--:--</span>
          <span class="log-ag SYSTEM">SYSTEM</span>
          <span class="log-msg system">Agency Live Watch ready. Enter your API key and mission above, then press LAUNCH.<span class="cursor"></span></span>
        </div>
      </div>
    </div>
  </main>

  <!-- RIGHT -->
  <aside class="right">

    <div>
      <div class="sec-label">Verdict</div>
      <div class="verdict-box">
        <div class="verdict-label">// Claude Reasoning Core</div>
        <div class="verdict-text PENDING" id="verdict-text">WAITING</div>
      </div>
    </div>

    <div>
      <div class="sec-label">Metrics</div>
      <div class="metric-row"><span class="metric-k">Elapsed</span><span class="metric-v amber" id="m-elapsed">—</span></div>
      <div class="metric-row"><span class="metric-k">Tokens in</span><span class="metric-v blue" id="m-tin">—</span></div>
      <div class="metric-row"><span class="metric-k">Tokens out</span><span class="metric-v blue" id="m-tout">—</span></div>
      <div class="metric-row"><span class="metric-k">Est. cost</span><span class="metric-v" id="m-cost">—</span></div>
      <div class="metric-row"><span class="metric-k">Graph nodes</span><span class="metric-v" id="m-nodes">—</span></div>
      <div class="metric-row"><span class="metric-k">Log lines</span><span class="metric-v" id="m-lines">0</span></div>
    </div>

    <div>
      <div class="sec-label">A2A Servers</div>
      <div id="a2a-map"></div>
    </div>

  </aside>
</div>

<script>
const AGENT_EMOJIS = {pm:'📋',backend:'⚙️',frontend:'🎨',security:'🔒',qa:'🧪',core:'🧠',copywriter:'✍️',ai:'🤖'};
const PRESETS = {
  full:     ['pm','backend','frontend','qa','security','core'],
  saas:     ['pm','copywriter','frontend','qa','core'],
  research: ['pm','ai','qa','core'],
};
let preset = 'full';
let logCount = 0;
let metricsMap = {};

function setPreset(p, btn) {
  preset = p;
  document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  renderAgentStatus();
}

function renderAgentStatus() {
  const el = document.getElementById('agent-statuses');
  el.innerHTML = PRESETS[preset].map(a => `
    <div class="agent-row" id="arow-${a}">
      <div class="agent-dot" id="adot-${a}"></div>
      <div class="agent-name">${AGENT_EMOJIS[a]||'🤖'} ${a}</div>
      <div class="agent-state" id="astate-${a}">idle</div>
    </div>
  `).join('');
}
renderAgentStatus();

function setAgentState(agent, state) {
  const dot   = document.getElementById('adot-'+agent);
  const label = document.getElementById('astate-'+agent);
  if (!dot) return;
  dot.className = 'agent-dot ' + state;
  label.textContent = state;
  label.style.color = state==='working'?'var(--amber)':state==='done'?'var(--green)':state==='error'?'var(--red)':'var(--muted)';
}

function addLog(ts, agent, msg, kind) {
  const term = document.getElementById('terminal');
  term.querySelectorAll('.cursor').forEach(c=>c.remove());
  const d = document.createElement('div');
  d.className = 'log';
  const agClass = ['SYSTEM','CORE','A2A','MEMORY'].includes(agent) ? agent : agent.toLowerCase();
  d.innerHTML = `
    <span class="log-ts">${ts}</span>
    <span class="log-ag ${agClass}">${agent}</span>
    <span class="log-msg ${kind||''}">${escHtml(msg)}</span>
  `;
  term.appendChild(d);
  term.scrollTop = term.scrollHeight;
  logCount++;
  document.getElementById('log-count').textContent = logCount + ' lines';
  document.getElementById('m-lines').textContent = logCount;
}

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ── SSE ───────────────────────────────────────────────────────
function connect() {
  const es = new EventSource('/stream');

  es.addEventListener('log', e => {
    const d = JSON.parse(e.data);
    addLog(d.ts, d.agent.toUpperCase(), d.msg, d.kind);
  });

  es.addEventListener('status', e => {
    const d = JSON.parse(e.data);
    setAgentState(d.agent, d.state);
  });

  es.addEventListener('metric', e => {
    const d = JSON.parse(e.data);
    metricsMap[d.key] = d.value;
    if (d.key==='elapsed')    document.getElementById('m-elapsed').textContent = d.value+'s';
    if (d.key==='tokens_in')  document.getElementById('m-tin').textContent = Number(d.value).toLocaleString();
    if (d.key==='tokens_out') document.getElementById('m-tout').textContent = Number(d.value).toLocaleString();
    if (d.key==='cost_usd')   document.getElementById('m-cost').textContent = '$'+d.value;
    if (d.key==='graph_nodes')document.getElementById('m-nodes').textContent = d.value;
    if (d.key==='a2a_count')  document.getElementById('a2a-badge').textContent = d.value+' live';
    if (d.key==='tool_count') document.getElementById('tools-badge').textContent = d.value;
  });

  es.addEventListener('verdict', e => {
    const d = JSON.parse(e.data);
    const el = document.getElementById('verdict-text');
    el.textContent = d.verdict;
    const cls = d.verdict==='GO'?'GO':d.verdict.includes('COND')?'CONDITIONAL':'NO-GO';
    el.className = 'verdict-text ' + cls;
    document.getElementById('launch-btn').disabled = false;
    document.getElementById('launch-btn').textContent = '⚡ LAUNCH LIVE';
    document.getElementById('live-label').textContent = 'DONE';
  });

  es.addEventListener('mission_start', e => {
    document.getElementById('live-label').textContent = 'LIVE';
    document.getElementById('verdict-text').textContent = 'RUNNING';
    document.getElementById('verdict-text').className = 'verdict-text PENDING';
  });

  es.addEventListener('mission_end', e => {});

  es.addEventListener('error', e => {
    const d = JSON.parse(e.data || '{}');
    addLog(new Date().toTimeString().slice(0,8), 'SYSTEM', 'ERROR: '+(d.message||'Unknown'), 'error');
    document.getElementById('launch-btn').disabled = false;
    document.getElementById('launch-btn').textContent = '⚡ LAUNCH LIVE';
    document.getElementById('live-label').textContent = 'ERROR';
  });

  es.addEventListener('message', e => {
    if (JSON.parse(e.data).type === 'connected') {
      document.getElementById('live-label').textContent = 'CONNECTED';
    }
  });

  es.onerror = () => {
    document.getElementById('live-label').textContent = 'RECONNECTING';
    setTimeout(connect, 2000);
    es.close();
  };
}
connect();

// ── A2A map ───────────────────────────────────────────────────
function updateA2AMap(portMap) {
  const el = document.getElementById('a2a-map');
  el.innerHTML = Object.entries(portMap).map(([n,p])=>`
    <div class="a2a-row">
      <span>${AGENT_EMOJIS[n]||'🤖'} ${n}</span>
      <span class="a2a-port">:${p}</span>
    </div>
  `).join('');
}

// ── Launch ────────────────────────────────────────────────────
async function launch() {
  const mission = document.getElementById('mission-input').value.trim();
  const key     = document.getElementById('key-input').value.trim()
                  || (window.__INJECTED_KEY||'');
  if (!mission) { addLog(new Date().toTimeString().slice(0,8),'SYSTEM','Mission required','warn'); return; }
  if (!key)     { addLog(new Date().toTimeString().slice(0,8),'SYSTEM','API key required — paste sk-ant-... above','warn'); return; }

  document.getElementById('launch-btn').disabled = true;
  document.getElementById('launch-btn').textContent = '⏳ RUNNING...';
  document.getElementById('terminal').innerHTML = '';
  logCount = 0;
  PRESETS[preset].forEach(a => setAgentState(a, 'ready'));

  const res = await fetch('/launch', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({mission, preset, api_key: key}),
  });
  const data = await res.json();
  if (data.error) {
    addLog(new Date().toTimeString().slice(0,8),'SYSTEM','Launch error: '+data.error,'error');
    document.getElementById('launch-btn').disabled = false;
    document.getElementById('launch-btn').textContent = '⚡ LAUNCH LIVE';
  }
}

// Enter key
document.getElementById('mission-input').addEventListener('keydown', e => {
  if (e.key==='Enter' && e.metaKey) launch();
});
</script>
</body>
</html>"""

# ── App ───────────────────────────────────────────────────────────────────────
app = Starlette(routes=[
    Route("/",        index),
    Route("/stream",  sse_stream),
    Route("/launch",  launch,  methods=["POST"]),
    Route("/health",  health),
])

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║  THE AGENCY — Live Watch Server                              ║
╠══════════════════════════════════════════════════════════════╣
║  Open in browser:  http://localhost:7777                     ║
║  API key:          {'SET ✓' if api_key else 'NOT SET — paste in browser UI':<44} ║
║  Model:            claude-sonnet-4-6                         ║
║  Press Ctrl+C to stop                                        ║
╚══════════════════════════════════════════════════════════════╝
""")
    uvicorn.run(app, host="0.0.0.0", port=7777, log_level="warning")
