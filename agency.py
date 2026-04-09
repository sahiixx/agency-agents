#!/usr/bin/env python3
"""
agency.py — The Agency unified entry point.

Fully-wired orchestrator using the deepagents SDK:
  - MemoryMiddleware + FilesystemBackend: shared AGENTS.md loaded at startup
  - SubAgentMiddleware: Claude Core spawns specialists via the `task` tool
  - TitansMemory: surprise-weighted memory persists lessons across runs
  - Claude Reasoning Core: final gate — GO / CONDITIONAL GO / NO-GO

Usage:
  python3 agency.py --list-agents
  python3 agency.py --mission "Build a REST API for user auth"
  python3 agency.py --mission "Design a SaaS landing page" --preset saas
  python3 agency.py --mission "Research AI trends" --preset research
  python3 agency.py --mission "Audit our security" --agents security,qa,core
  python3 agency.py --mission "Qualify these Dubai leads" --preset dubai
  python3 agency.py --mission "Run this mission" --provider ollama --ollama-model llama3.1
"""

import os
import sys
import warnings
import argparse
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.resolve()
SDK_PATH  = REPO_ROOT / "deepagents" / "libs" / "deepagents"

for p in (str(SDK_PATH), str(REPO_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

# ── Imports ───────────────────────────────────────────────────────────────────
try:
    from deepagents import create_deep_agent, SubAgent
    from deepagents.backends import FilesystemBackend
except ImportError as e:
    print(f"❌  deepagents SDK not found: {e}")
    print("    Run: pip install -e deepagents/libs/deepagents")
    sys.exit(1)

try:
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage
except ImportError as e:
    print(f"❌  langchain-anthropic not found: {e}")
    print("    Run: pip install langchain-anthropic")
    sys.exit(1)

from memory.titans_memory import TitansMemory
from mcp_tools import MCP_TOOLS
from observability import AgencyTracer
from providers import get_provider
from a2a_protocol import (
    start_agency_a2a_servers,
    register_servers,
    make_a2a_tools,
    A2AClient,
    BASE_PORT,
)

# ── Config ────────────────────────────────────────────────────────────────────
CLAUDE_MODEL = "claude-sonnet-4-6"
MEMORY_FILE  = "memory/AGENTS.md"  # relative to REPO_ROOT

# ── Agent registry ────────────────────────────────────────────────────────────
AGENT_REGISTRY = {
    "pm":        ("project-management/project-manager-senior.md",    "Senior project manager — planning, task decomposition, timelines"),
    "frontend":  ("engineering/engineering-frontend-developer.md",    "Frontend developer — React, Next.js, UI implementation"),
    "backend":   ("engineering/engineering-backend-architect.md",     "Backend architect — APIs, databases, system design"),
    "ai":        ("engineering/engineering-ai-engineer.md",           "AI engineer — ML models, LLM integration, RAG"),
    "security":  ("engineering/engineering-security-engineer.md",     "Security engineer — threat modeling, vulnerability review"),
    "devops":    ("engineering/engineering-devops-automator.md",      "DevOps — CI/CD, infrastructure, deployment automation"),
    "qa":        ("testing/testing-reality-checker.md",               "QA engineer — testing, auditing, quality gates"),
    "design":    ("design/design-ux-architect.md",                    "UX architect — user experience, information architecture"),
    "growth":    ("marketing/marketing-growth-hacker.md",             "Growth hacker — acquisition, conversion, metrics"),
    "copywriter":("marketing/marketing-content-creator.md",           "Content creator — copy, messaging, brand voice"),
    "sales":     ("sales/sales-deal-strategist.md",                   "Deal strategist — sales strategy, proposals, negotiation"),
    "core":      ("specialized/specialized-claude-reasoning-core.md", "Claude Reasoning Core — judgment, ethics, final verdicts"),
    "prompt-arch":("specialized/specialized-prompt-architect.md",     "Prompt Architect — designs and audits agent prompts using 26 universal patterns"),
    "spy":       ("specialized/specialized-ai-tools-reverse-engineer.md", "AI Tools Reverse Engineer — competitive intel on 31+ AI tools (Cursor, Devin, Windsurf, Manus, Kiro…)"),
    "docs":      ("specialized/specialized-mintlify-docs-publisher.md",   "Mintlify Docs Publisher — converts outputs into MDX docs for mintlify-docs + docs repos"),
    "wpscan":    ("engineering/engineering-wpscan-penetration-tester.md", "WPScan Penetration Tester — WordPress vuln scanning, plugin/theme enum, brute force"),
    "linux":     ("specialized/specialized-linux-sysadmin.md",        "Linux Sysadmin — filesystem, services, hardening, runbooks across major distros"),
    "learn":     ("specialized/specialized-ai-learning-curator.md",   "AI Learning Curator — curated AI/ML/CS courses, repos, books, and study paths"),
    "cloudflare":("integrations/cloudflare-deployment-templates.md",  "Cloudflare Deployment — Workers, Pages, D1, R2, Containers; react-router + containers templates"),
    "trust":     ("specialized/specialized-trust-graph-operator.md",  "Trust Graph Operator — Neo4j entity trust scores, UAE reputation, AML/RERA flags"),
    # Real estate agents
    "re-leads":  ("real-estate/real-estate-lead-qualification-specialist.md", "Lead qualification — scoring, pipeline prioritization, buyer readiness"),
    "re-match":  ("real-estate/real-estate-property-matching-engine.md",      "Property matching — buyer-to-listing pairing, market data analysis"),
    "re-copy":   ("real-estate/real-estate-outreach-copywriter.md",           "Outreach copywriter — WhatsApp, email, SMS campaigns for lead conversion"),
    "re-deal":   ("real-estate/real-estate-deal-negotiation-strategist.md",   "Deal negotiation — offer structuring, counter-offers, closing"),
    "re-intel":  ("real-estate/real-estate-market-intelligence-analyst.md",   "Market intelligence — DLD data, price trends, area analysis"),
    "re-comply": ("real-estate/real-estate-compliance-rera-guardian.md",       "RERA compliance — regulation, AML, data protection, advertising"),
    "re-crm":    ("real-estate/real-estate-crm-pipeline-orchestrator.md",     "CRM pipeline — lead lifecycle, routing, stage management, reporting"),
    "re-pitch":  ("real-estate/real-estate-investor-pitch-specialist.md",     "Investor pitch — HNW proposals, ROI analysis, golden visa"),
    "re-refer":  ("real-estate/real-estate-post-sale-referral-engine.md",     "Post-sale — client retention, referral generation, repeat business"),
    # NOWHERE.AI business agents (Dubai/UAE digital services)
    "biz-sales":     ("business/business-sales-agent.md",       "B2B sales — lead qualification, proposals, pipeline management, AED pricing"),
    "biz-mkt":       ("business/business-marketing-agent.md",   "Digital marketing — bilingual campaigns, UAE channels, Ramadan/seasonal strategy"),
    "biz-content":   ("business/business-content-agent.md",     "Bilingual content — English + Arabic copy, SEO, social media, email campaigns"),
    "biz-analytics": ("business/business-analytics-agent.md",   "Business intelligence — KPIs, forecasting, anomaly detection, AED benchmarks"),
    "biz-ops":       ("business/business-operations-agent.md",  "Operations — workflow automation, invoicing, HR, UAE compliance, onboarding"),
}

PRESETS = {
    "full":       ["pm", "backend", "frontend", "qa", "security", "core"],
    "saas":       ["pm", "copywriter", "frontend", "qa", "core"],
    "research":   ["pm", "ai", "qa", "core"],
    "realestate": ["re-leads", "re-match", "re-copy", "re-deal", "re-intel", "re-comply", "re-crm", "re-pitch", "re-refer", "core"],
    # Dubai full-stack: NOWHERE.AI business agents (B2B sales/mkt/content/analytics/ops)
    # combined with core RE agents (leads, intel, compliance) for UAE market missions
    "dubai":      ["biz-sales", "biz-mkt", "biz-content", "biz-analytics", "biz-ops",
                   "re-leads", "re-intel", "re-comply", "core"],
    # Security & infrastructure — uses airecon + trufflehog + shannon tools automatically
    "security":   ["security", "wpscan", "linux", "devops", "core"],
    # Competitive intelligence — study & improve agent prompts using tool patterns from 31+ AI tools
    "intel":      ["spy", "prompt-arch", "core"],
    # Docs — generate and publish Mintlify documentation from any mission output
    "docs":       ["pm", "docs", "core"],
    # Moltbot — fire mission and deliver results via Telegram/Discord/Slack/Web
    "moltbot":    ["pm", "backend", "frontend", "core"],  # results pushed via trigger_moltbot_mission MCP tool
    # Trust vetting — UAE entity trust screening for sales, RE, compliance
    "trust":      ["trust", "re-comply", "core"],
    # Voice — lean pipeline for voice-driven missions (fast, focused)
    "voice":      ["pm", "backend", "core"],
    # n8n automation — workflow generation and automation bus missions
    "n8n":        ["pm", "devops", "backend", "core"],
    # Sovereign — full ecosystem with all business + RE + security agents
    "sovereign":  ["pm", "backend", "frontend", "security", "devops", "ai",
                   "biz-sales", "biz-mkt", "biz-ops", "re-leads", "re-intel", "core"],
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_llm(provider: str = "anthropic", ollama_model: str = "llama3.1",
            ollama_base_url: str = "http://localhost:11434",
            openai_model: str = "gpt-4o",
            adk_model: str = "gemini-2.0-flash",
            autogen_model: str = "gpt-4o") -> object:
    """Return the configured LLM.

    Supported providers: anthropic (default), ollama, openai, adk, autogen, rasa, n8n.
    rasa and n8n do not currently provide a LangChain-compatible LLM here, so
    selecting them still uses Claude/Anthropic as the orchestration backbone.
    """
    p = get_provider(provider)

    if provider in ("anthropic", "claude"):
        print(f"  Provider: Anthropic ({CLAUDE_MODEL})")
        return p.get_llm(model=CLAUDE_MODEL)

    if provider == "ollama":
        print(f"  Provider: Ollama ({ollama_model} @ {ollama_base_url})")
        return p.get_llm(model=ollama_model, base_url=ollama_base_url)

    if provider == "openai":
        print(f"  Provider: OpenAI ({openai_model})")
        return p.get_llm(model=openai_model)

    if provider == "adk":
        print(f"  Provider: Google ADK ({adk_model})")
        return p.get_llm(model=adk_model)

    if provider == "autogen":
        print(f"  Provider: AutoGen ({autogen_model})")
        # AutoGen manages its own LLM; return Anthropic LLM as orchestrator backbone
        from providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider().get_llm(model=CLAUDE_MODEL)

    if provider in ("rasa", "n8n"):
        print(f"  Provider: {provider} (external service — Claude used for orchestration)")
        from providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider().get_llm(model=CLAUDE_MODEL)

    raise ValueError(f"Unknown provider '{provider}'")


def load_agent(path: str) -> str:
    f = REPO_ROOT / path
    if not f.exists():
        print(f"  ⚠️   Agent file missing: {path}")
        return ""
    return f.read_text()


def build_subagent(name: str, llm: ChatAnthropic) -> SubAgent:
    path, description = AGENT_REGISTRY[name]
    return {
        "name":          name,
        "description":   description,
        "system_prompt": load_agent(path),
        "tools":         MCP_TOOLS,      # ← all agents get MCP tools
        "model":         llm,
    }


# ── Parallel execution groups ─────────────────────────────────────────────────
# Agents in the same group run concurrently; groups run sequentially.
# Core always runs last as the verdict gate.

PARALLEL_GROUPS = {
    "full":       [["pm"], ["backend", "frontend", "security"], ["qa"], ["core"]],
    "saas":       [["pm"], ["copywriter", "frontend"],          ["qa"], ["core"]],
    "research":   [["pm", "ai"],                                ["qa"], ["core"]],
    "realestate": [["re-leads", "re-intel"], ["re-match", "re-copy"], ["re-deal", "re-comply"], ["re-crm", "re-pitch", "re-refer"], ["core"]],
    # Dubai: business intelligence + RE context run first, then content/ops, then core verdict
    "dubai":      [["biz-analytics", "re-intel"], ["biz-sales", "biz-mkt", "re-leads"], ["biz-content", "biz-ops", "re-comply"], ["core"]],
    # Voice: fast 2-phase pipeline
    "voice":      [["pm", "backend"], ["core"]],
    # n8n: devops + backend build the workflow, core approves
    "n8n":        [["pm", "devops", "backend"], ["core"]],
    # Sovereign: full ecosystem — business + RE + security all run in parallel phases
    "sovereign":  [["pm", "biz-analytics", "re-intel"], ["backend", "frontend", "biz-sales", "biz-mkt", "re-leads"], ["security", "devops", "ai", "biz-ops", "re-intel"], ["core"]],
}


def _parallel_group_label(group: list[str]) -> str:
    return " ∥ ".join(group) if len(group) > 1 else group[0]


# ── Core mission runner ───────────────────────────────────────────────────────

def run_mission(goal: str, agent_names: list, preset: str = "full",
                provider: str = "anthropic", ollama_model: str = "llama3.1",
                ollama_base_url: str = "http://localhost:11434",
                openai_model: str = "gpt-4o",
                adk_model: str = "gemini-2.0-flash",
                autogen_model: str = "gpt-4o",
                extra_tools: list | None = None,
                dry_run: bool = False) -> str:
    invalid = [n for n in agent_names if n not in AGENT_REGISTRY]
    if invalid:
        print(f"❌  Unknown agents: {invalid}")
        print(f"   Available: {list(AGENT_REGISTRY.keys())}")
        sys.exit(1)

    llm = get_llm(
        provider=provider,
        ollama_model=ollama_model,
        ollama_base_url=ollama_base_url,
        openai_model=openai_model,
        adk_model=adk_model,
        autogen_model=autogen_model,
    )
    tracer  = AgencyTracer(mission=goal, preset=preset)
    groups  = PARALLEL_GROUPS.get(preset, [[a] for a in agent_names])
    base_tools = MCP_TOOLS + (extra_tools or [])

    print(f"\n{'='*65}")
    print(f"  MISSION: {goal}")
    print(f"  Provider: {provider}  |  MCP tools: {len(base_tools)}")
    print(f"  Agents:  {', '.join(agent_names)}")
    print(f"  Groups:  {' → '.join(_parallel_group_label(g) for g in groups)}")
    if dry_run:
        print(f"\n  [DRY RUN] Pipeline printed — no API calls made.")
        print(f"  Tools loaded: {len(base_tools)} MCP tools")
        print(f"  Execution plan:")
        for i, g in enumerate(groups):
            mode = "concurrently" if len(g) > 1 else "sequential"
            print(f"    Phase {i+1}: [{_parallel_group_label(g)}] ({mode})")
        print(f"{'='*65}\n")
        return "[DRY RUN] No mission executed."
    print(f"{'='*65}\n")

    # Start A2A servers for this mission's agents
    print(f"  Starting A2A servers...")
    port_map = start_agency_a2a_servers(agent_names, AGENT_REGISTRY, REPO_ROOT)
    register_servers(port_map)
    a2a_urls  = [f"http://localhost:{p}" for p in port_map.values()]
    a2a_tools = make_a2a_tools(a2a_urls)
    all_tools  = base_tools + a2a_tools
    print(f"  A2A: {len(a2a_tools)} agent servers live | Total tools: {len(all_tools)}\n")

    # Build subagents (all except core) — give each MCP + A2A tools
    specialist_names = [n for n in agent_names if n != "core"]
    subagents = [build_subagent(n, llm) for n in specialist_names]
    for sa in subagents:
        sa["tools"] = all_tools   # override with full tool set
        status      = "OK" if sa["system_prompt"] else "MISSING"
        prompt_len  = len(sa["system_prompt"])
        print(f"  [{status}]  {sa['name']} ({prompt_len:,} chars)  "
              f"[{len(all_tools)} tools: MCP+A2A]")

    # FilesystemBackend so MemoryMiddleware reads from local disk
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        fs_backend = FilesystemBackend(root_dir=str(REPO_ROOT), virtual_mode=False)

    # Build orchestrator graph
    print(f"\n  Building orchestrator...")
    try:
        orchestrator = create_deep_agent(
            model=llm,
            tools=all_tools,             # ← MCP + A2A tools
            system_prompt=load_agent(AGENT_REGISTRY["core"][0]),
            subagents=subagents,
            memory=[MEMORY_FILE],
            backend=fs_backend,
            name="claude-agency-orchestrator",
        )
        print(f"  Graph ready ({len(orchestrator.nodes)} nodes)\n")
    except Exception as e:
        print(f"  ERROR building graph: {type(e).__name__}: {e}")
        return None

    # Describe parallel groups to the orchestrator
    group_desc = "\n".join(
        f"  Phase {i+1}: [{_parallel_group_label(g)}] — run {'concurrently' if len(g)>1 else 'sequentially'}"
        for i, g in enumerate(groups)
    )
    a2a_desc = "\n".join(
        f"  {name:12} → http://localhost:{port}"
        for name, port in port_map.items()
    )

    brief = f"""MISSION: {goal}

You have specialist subagents via `task` tool, MCP tools, and A2A agent servers.

MCP TOOLS: web_search, read_file, write_output, code_lint, memory_recall, get_datetime
A2A SERVERS (call any external or internal agent via A2A protocol):
{a2a_desc}

PARALLEL EXECUTION PLAN:
{group_desc}

Instructions:
1. Follow the phase plan — delegate parallel agents simultaneously
2. Use web_search for current data, memory_recall for past mission context
3. A2A servers let you call agents from any external framework too
4. Synthesize all outputs into one cohesive deliverable
5. Use write_output to save the final deliverable as a file
6. Constitutional review — accuracy, safety, completeness, consistency
7. Return final verdict: GO / CONDITIONAL GO / NO-GO with clear rationale

Delegate everything. You are the orchestrator and final judge."""

    print(f"  Orchestrating...\n")

    with tracer.span("orchestrator"):
        try:
            response = orchestrator.invoke(
                {"messages": [HumanMessage(content=brief)]},
                config={"recursion_limit": 50},
            )
            final = response["messages"][-1].content
            # Estimate tokens from response length (no callback needed)
            tracer.add_tokens(
                input_tokens=len(brief) // 4,
                output_tokens=len(final) // 4,
            )
        except KeyboardInterrupt:
            print("\n  Mission interrupted.")
            return None
        except Exception as e:
            print(f"\n  Mission failed: {type(e).__name__}: {e}")
            return None

    print(f"\n{'='*65}")
    print(f"  VERDICT — CLAUDE REASONING CORE")
    print(f"{'='*65}")
    print(final)
    print(f"{'='*65}\n")

    # Record in Titans memory
    verdict = (
        "NO-GO"          if "no-go"       in final.lower() and "conditional" not in final.lower() else
        "CONDITIONAL GO" if "conditional" in final.lower() else
        "GO"
    )

    # Finish tracing + print observability report
    tracer.finish(verdict=verdict)
    tracer.print_summary()
    trace_path = tracer.save_trace()
    print(f"  Trace: {trace_path}")

    try:
        mem = TitansMemory()
        outcome = mem.record_outcome(goal, verdict)
        mem.inject_into_agents_md()
        print(f"  Memory: {verdict} (surprise={outcome.surprise:.2f}) — {mem.summary()}")
    except Exception as e:
        print(f"  Memory update failed (non-fatal): {e}")

    return final


# ── CLI ───────────────────────────────────────────────────────────────────────

def list_agents():
    print(f"\n{'-'*65}")
    print(f"  Agency Agent Registry — {len(AGENT_REGISTRY)} agents")
    print(f"{'-'*65}")
    for name, (path, desc) in AGENT_REGISTRY.items():
        exists = "OK  " if (REPO_ROOT / path).exists() else "MISS"
        print(f"  [{exists}]  {name:<12} {desc}")
    print(f"\n  Presets:")
    for preset, agents in PRESETS.items():
        print(f"    --preset {preset:<10} -> {', '.join(agents)}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="The Agency — unified multi-agent orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 agency.py --list-agents
  python3 agency.py --mission "Write a technical spec for user auth"
  python3 agency.py --mission "Design a SaaS landing page" --preset saas
  python3 agency.py --mission "Research AI memory techniques" --preset research
  python3 agency.py --mission "Audit security posture" --agents security,qa,core
  python3 agency.py --mission "Qualify these Dubai B2B leads" --preset dubai
  python3 agency.py --mission "Run offline" --provider ollama --ollama-model llama3.1
  python3 agency.py --mission "Build API" --provider openai --openai-model gpt-4o
  python3 agency.py --mission "Plan sprint" --provider adk --adk-model gemini-2.0-flash
  python3 agency.py --mission "Automate email" --provider n8n
  python3 agency.py --mission "Scout targets" --tools airecon,trufflehog
  python3 agency.py --mission "Ship feature" --dry-run
  python3 agency.py --serve --ui nextjs
  python3 agency.py --evolve
        """,
    )
    # ── Mission
    parser.add_argument("--mission", "-m", type=str, help="Mission goal")
    parser.add_argument("--agents",        type=str, help="Comma-separated agent keys")
    parser.add_argument("--preset",        choices=list(PRESETS), default="full",
                        help="Agent preset (default: full)")
    parser.add_argument("--list-agents",   action="store_true", help="List available agents and presets")
    parser.add_argument("--dry-run",       action="store_true",
                        help="Print pipeline without making API calls (useful for testing)")

    # ── Provider
    parser.add_argument("--provider",
                        choices=["anthropic", "claude", "ollama", "openai", "adk", "autogen", "rasa", "n8n"],
                        default="anthropic",
                        help="LLM/agent provider (default: anthropic)")
    parser.add_argument("--ollama-model",  default="llama3.1",
                        help="Ollama model name (default: llama3.1)")
    parser.add_argument("--ollama-url",    default="http://localhost:11434",
                        help="Ollama server URL (default: http://localhost:11434)")
    parser.add_argument("--openai-model",  default="gpt-4o",
                        help="OpenAI model name (default: gpt-4o)")
    parser.add_argument("--adk-model",     default="gemini-2.0-flash",
                        help="Google ADK / Gemini model (default: gemini-2.0-flash)")
    parser.add_argument("--autogen-model", default="gpt-4o",
                        help="AutoGen model name (default: gpt-4o)")

    # ── Extra tools
    parser.add_argument("--tools", type=str, default="",
                        help=("Comma-separated extra tool groups to activate: "
                              "mcp, perplexica, sqlbot, airecon, trufflehog, shannon, n8n"))

    # ── Serve modes
    parser.add_argument("--serve",  action="store_true",
                        help="Start a service (combine with --ui or --voice)")
    parser.add_argument("--ui",     choices=["nextjs", "html"], default="html",
                        help="Dashboard UI to launch with --serve (default: html)")
    parser.add_argument("--voice",  choices=["twilio", "local"], default="local",
                        help="Voice pipeline backend to launch with --serve (default: local)")

    # ── Evolve
    parser.add_argument("--evolve", action="store_true",
                        help="Run the evolution_scheduler to self-improve one agent")

    args = parser.parse_args()

    if args.list_agents:
        list_agents()
        return

    # ── Serve mode ─────────────────────────────────────────────────────────────
    if args.serve:
        if args.ui == "nextjs":
            import subprocess
            dash = REPO_ROOT / "dashboard"
            if not dash.exists():
                print("❌  dashboard/ not found. Run the setup first:\n"
                      "    cd dashboard && npm install && npm run dev")
                return
            print(f"  Starting Next.js dashboard at http://localhost:3000 …")
            subprocess.run(["npm", "run", "dev"], cwd=str(dash))
        else:
            import webbrowser
            ui_path = REPO_ROOT / "agency_ui.html"
            url = f"file://{ui_path}"
            print(f"  Opening Agency UI: {url}")
            webbrowser.open(url)
        if args.voice == "twilio":
            print("  Launching voice pipeline (Twilio mode) …")
            import subprocess
            subprocess.Popen(["python3", str(REPO_ROOT / "voice_agency.py"), "--mode", "twilio"])
        elif args.voice == "local":
            try:
                import subprocess
                subprocess.Popen(["python3", str(REPO_ROOT / "voice_agency.py"), "--mode", "local"])
                print("  Launching voice pipeline (local mode) …")
            except Exception:
                pass
        return

    # ── Evolve mode ────────────────────────────────────────────────────────────
    if args.evolve:
        print("  Running evolution_scheduler …")
        import subprocess
        result = subprocess.run(
            ["python3", str(REPO_ROOT / "evolution_scheduler.py")],
            capture_output=False,
        )
        sys.exit(result.returncode)

    if not args.mission:
        parser.print_help()
        return

    # ── Resolve extra tools ────────────────────────────────────────────────────
    extra_tools: list = []
    if args.tools:
        from mcp_tools import (
            perplexica_search, sql_query, api_lookup,
            airecon_scan, scan_secrets, web_pentest, n8n_trigger,
        )
        tool_map = {
            "perplexica": perplexica_search,
            "sqlbot":     sql_query,
            "api_lookup": api_lookup,
            "airecon":    airecon_scan,
            "trufflehog": scan_secrets,
            "shannon":    web_pentest,
            "n8n":        n8n_trigger,
        }
        for tag in args.tools.split(","):
            tag = tag.strip().lower()
            if tag == "mcp":
                pass  # all MCP_TOOLS are already included
            elif tag in tool_map:
                t = tool_map[tag]
                if t not in extra_tools:
                    extra_tools.append(t)
            else:
                print(f"  ⚠️   Unknown tool group '{tag}' — skipped")

    agent_names = (
        [a.strip() for a in args.agents.split(",")]
        if args.agents
        else list(PRESETS[args.preset])
    )

    # Always put core last
    if "core" in agent_names:
        agent_names = [a for a in agent_names if a != "core"] + ["core"]

    run_mission(
        args.mission,
        agent_names,
        preset=args.preset,
        provider=args.provider,
        ollama_model=args.ollama_model,
        ollama_base_url=args.ollama_url,
        openai_model=args.openai_model,
        adk_model=args.adk_model,
        autogen_model=args.autogen_model,
        extra_tools=extra_tools,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
