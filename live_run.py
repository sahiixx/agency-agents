#!/usr/bin/env python3
"""
live_run.py — One command to run Claude live inside The Agency.

Usage:
  ANTHROPIC_API_KEY=sk-ant-... python3 live_run.py

What happens:
  1. Claude Sonnet 4.6 receives the mission
  2. Orchestrator delegates to pm → backend → frontend (parallel) → qa → core
  3. Each agent calls real Claude API with its specialist system prompt
  4. MCP tools available: web_search, read_file, write_output, memory_recall
  5. A2A servers start — each agent is a live HTTP endpoint
  6. Observability prints per-agent latency, tokens, and cost
  7. Titans memory records the verdict
  8. Full trace saved to /tmp/agency_outputs/
"""

import os
import sys
import warnings
warnings.filterwarnings("ignore")

# ── Check key before anything ─────────────────────────────────────────────────
api_key = os.environ.get("ANTHROPIC_API_KEY", "")
if not api_key or not api_key.startswith("sk-ant-"):
    print("""
╔══════════════════════════════════════════════════════════════╗
║  THE AGENCY — Live Run                                       ║
║  One thing needed: your Anthropic API key                    ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  export ANTHROPIC_API_KEY="sk-ant-..."                       ║
║  python3 live_run.py                                         ║
║                                                              ║
║  Or in one line:                                             ║
║  ANTHROPIC_API_KEY="sk-ant-..." python3 live_run.py          ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")
    sys.exit(1)

# ── Paths ─────────────────────────────────────────────────────────────────────
from pathlib import Path
REPO = Path(__file__).parent.resolve()
sys.path.insert(0, str(REPO / "deepagents/libs/deepagents"))
sys.path.insert(0, str(REPO))

# ── Imports ───────────────────────────────────────────────────────────────────
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from memory.titans_memory import TitansMemory
from mcp_tools import MCP_TOOLS
from observability import AgencyTracer
from a2a_protocol import start_agency_a2a_servers, make_a2a_tools
import agency
import time

# ── Mission ───────────────────────────────────────────────────────────────────
MISSION = (
    sys.argv[1] if len(sys.argv) > 1
    else "Design a production-ready gold loan LTV calculator API for UAE lenders "
         "with tiered LTV ratios for 18K/21K/22K/24K gold, real-time gold price "
         "feed integration, and CBUAE compliance checks."
)
PRESET = "full"

print(f"""
╔══════════════════════════════════════════════════════════════╗
║  THE AGENCY — LIVE RUN                                       ║
║  Claude Sonnet 4.6 · deepagents · LangGraph                  ║
╠══════════════════════════════════════════════════════════════╣
║  Mission: {MISSION[:52]:<52} ║
║  Preset:  {PRESET:<52} ║
╚══════════════════════════════════════════════════════════════╝
""")

# ── Setup ─────────────────────────────────────────────────────────────────────
llm    = ChatAnthropic(model="claude-sonnet-4-6", api_key=api_key)
tracer = AgencyTracer(mission=MISSION, preset=PRESET)
groups = agency.PARALLEL_GROUPS[PRESET]
agents = [a for g in groups for a in g]

# ── A2A servers ───────────────────────────────────────────────────────────────
print("Starting A2A servers...")
port_map  = start_agency_a2a_servers(agents, agency.AGENT_REGISTRY, REPO)
time.sleep(0.5)
a2a_tools = make_a2a_tools([f"http://localhost:{p}" for p in port_map.values()])
all_tools = MCP_TOOLS + a2a_tools
print(f"  {len(port_map)} A2A servers live | {len(all_tools)} total tools\n")

# ── Subagents ─────────────────────────────────────────────────────────────────
specialist_names = [n for n in agents if n != "core"]
subagents = []
for name in specialist_names:
    path, desc = agency.AGENT_REGISTRY[name]
    sp = (REPO / path).read_text() if (REPO / path).exists() else f"# {name}"
    subagents.append({"name": name, "description": desc,
                      "system_prompt": sp, "tools": all_tools, "model": llm})
    print(f"  [OK] {name:12} {len(sp):,} chars  [{len(all_tools)} tools]")

# ── Graph ─────────────────────────────────────────────────────────────────────
print("\nBuilding orchestrator graph...")
fs = FilesystemBackend(root_dir=str(REPO), virtual_mode=False)
core_sp = (REPO / agency.AGENT_REGISTRY["core"][0]).read_text()
orch = create_deep_agent(
    model=llm, tools=all_tools, system_prompt=core_sp,
    subagents=subagents, memory=[agency.MEMORY_FILE],
    backend=fs, name="live-agency-orchestrator",
)
print(f"  Graph ready — {len(orch.nodes)} nodes: {list(orch.nodes.keys())}\n")

# ── Brief ─────────────────────────────────────────────────────────────────────
group_plan = "\n".join(
    f"  Phase {i+1}: [{' ∥ '.join(g) if len(g)>1 else g[0]}]"
    for i, g in enumerate(groups)
)
a2a_map = "\n".join(f"  {n:12} → http://localhost:{p}" for n, p in port_map.items())

brief = f"""MISSION: {MISSION}

PARALLEL EXECUTION PLAN:
{group_plan}

A2A SERVERS (each agent is a live HTTP endpoint):
{a2a_map}

MCP TOOLS: web_search, read_file, write_output, code_lint, memory_recall, get_datetime

Instructions:
1. Follow the parallel phase plan — run agents in each phase simultaneously
2. Use web_search for current gold prices, CBUAE regulations, or any live data
3. Use memory_recall to check past mission context
4. Use write_output to save the final deliverable
5. Constitutional review: accuracy, safety, UAE compliance, completeness
6. Return final verdict: GO / CONDITIONAL GO / NO-GO with full rationale

Delegate everything. You are the orchestrator and final judge."""

# ── Run ───────────────────────────────────────────────────────────────────────
print(f"{'='*65}")
print("  ORCHESTRATING — Claude Sonnet 4.6 is live")
print(f"{'='*65}\n")

with tracer.span("full-mission"):
    try:
        response = orch.invoke(
            {"messages": [HumanMessage(content=brief)]},
            config={"recursion_limit": 50},
        )
        final = response["messages"][-1].content
        tracer.add_tokens(
            input_tokens=sum(
                len(m.content) // 4
                for m in response["messages"]
                if hasattr(m, "content") and isinstance(m.content, str)
            ),
            output_tokens=len(final) // 4,
        )
    except KeyboardInterrupt:
        print("\nMission interrupted.")
        sys.exit(0)
    except Exception as e:
        print(f"\nMission failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

# ── Verdict ───────────────────────────────────────────────────────────────────
verdict = (
    "NO-GO"          if "no-go"       in final.lower() and "conditional" not in final.lower() else
    "CONDITIONAL GO" if "conditional" in final.lower() else
    "GO"
)

print(f"\n{'='*65}")
print("  VERDICT — CLAUDE REASONING CORE")
print(f"{'='*65}")
print(final)
print(f"{'='*65}\n")

# ── Observability ─────────────────────────────────────────────────────────────
tracer.finish(verdict=verdict)
tracer.print_summary()
trace_path = tracer.save_trace()
print(f"  Trace saved: {trace_path}")

# ── Titans memory ─────────────────────────────────────────────────────────────
mem     = TitansMemory()
outcome = mem.record_outcome(MISSION, verdict)
mem.inject_into_agents_md()
print(f"  Memory: {verdict} (surprise={outcome.surprise:.2f}) — {mem.summary()}\n")

print(f"{'='*65}")
print("  DONE — The Agency ran live. Real Claude. Real outputs.")
print(f"{'='*65}")
