#!/usr/bin/env python3
"""
explorer_loop.py — Autonomous Exploration Loop for The Agency.

AGI capability: when the agency is idle, this loop dispatches exploration
missions to discover new knowledge, technologies, and integration opportunities.

Key idea: an AGI system should actively seek out new knowledge rather than
waiting to be told what to do — this is the difference between a tool and
an agent.

How it works per cycle:
  1. Load exploration topics from the exploration ledger
  2. Select a topic to explore (priority queue — least-recently explored first)
  3. Dispatch the Autonomous Explorer agent with the topic
  4. Synthesize findings
  5. Store findings in the exploration ledger
  6. Check for integration opportunities (new agents, new tools, new repos)

Usage:
  # Single exploration
  python3 explorer_loop.py --topic "MCP protocol updates 2026"

  # Explore the ecosystem (scan sahiixx repos for integration opportunities)
  python3 explorer_loop.py --ecosystem

  # Daemon mode (explores N new topics per cycle)
  python3 explorer_loop.py --daemon --interval 120

  # List past explorations
  python3 explorer_loop.py --history
"""

import json
import os
import subprocess
import sys
import time
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).parent.resolve()
EXPLORATION_LEDGER = REPO_ROOT / "memory" / "exploration_ledger.json"
OUTPUTS_DIR = Path("/tmp/agency_outputs")
OUTPUTS_DIR.mkdir(exist_ok=True)

# Default exploration topics (rotating — explores one per cycle)
DEFAULT_TOPICS = [
    "Latest MCP (Model Context Protocol) updates and tool implementations",
    "New agent frameworks and multi-agent architectures (2026)",
    "RAG techniques: advanced chunking, routing, and re-ranking innovations",
    "LLM evaluation best practices and emerging benchmarks",
    "Vector database comparison: Qdrant, Pinecone, Weaviate, Milvus",
    "AI agent safety and alignment research updates",
    "Latest in LLM fine-tuning: LoRA variants, quantization, distillation",
    "Edge AI and on-device inference advances",
    "AI coding assistants: new capabilities, system prompts, patterns",
    "A2A (Agent-to-Agent) protocol ecosystem growth",
    "Self-hosted AI infrastructure: Ollama, vLLM, TGI updates",
    "AI agent observability and tracing tools",
]

# Topic categories for the sahiixx ecosystem scan
ECOSYSTEM_TOPICS = [
    "Cross-repo integration patterns for multi-agent AI ecosystems",
    "Cloudflare Workers and edge compute for AI agent gateways",
    "Real estate AI: property matching, lead scoring, market intelligence",
    "Voice AI: real-time voice agents and voice-first interfaces",
    "UAE/Dubai AI market: regulatory landscape and business opportunities",
    "AI documentation: automated docs generation with Mintlify and MDX",
    "CrewAI vs AutoGen vs LangGraph vs deepagents comparison",
]


def load_ledger() -> dict:
    """Load the exploration ledger."""
    if EXPLORATION_LEDGER.exists():
        try:
            return json.loads(EXPLORATION_LEDGER.read_text())
        except (json.JSONDecodeError, Exception):
            return {"explorations": [], "topics": {}}
    return {"explorations": [], "topics": {}}


def save_ledger(ledger: dict):
    """Save the exploration ledger atomically."""
    tmp = EXPLORATION_LEDGER.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(ledger, indent=2))
    tmp.replace(EXPLORATION_LEDGER)


def select_topic(ledger: dict, custom_topic: str = None, ecosystem_mode: bool = False) -> str:
    """
    Select the next topic to explore.

    Priority: custom_topic > ecosystem > least-recently-explored default topic.
    """
    if custom_topic:
        return custom_topic

    if ecosystem_mode:
        # Pick a random ecosystem topic
        import random
        explored = set(ledger.get("topics", {}).keys())
        available = [t for t in ECOSYSTEM_TOPICS if t not in explored]
        if not available:
            available = ECOSYSTEM_TOPICS
        return random.choice(available)

    # Default topics — pick least-recently explored
    topics = ledger.get("topics", {})
    now = datetime.now().timestamp()

    topic_scores = []
    for topic in DEFAULT_TOPICS:
        info = topics.get(topic, {"count": 0, "last": 0})
        days_since = (now - info["last"]) / 86400 if info["last"] else 999
        score = days_since * (1 + info["count"])  # Penalize high-count topics
        topic_scores.append((score, topic))

    topic_scores.sort(key=lambda x: x[0])
    return topic_scores[0][1]


def explore(topic: str, use_llm: bool = True) -> dict:
    """
    Explore a topic using web_search and LLM synthesis.

    Args:
        topic: The topic to explore
        use_llm: If True, uses Ollama for synthesis. If False, uses web_search only.

    Returns:
        Dict with findings, sources, and recommendations.
    """
    print(f"\n  🌐  Exploring: {topic[:80]}")
    print(f"  {'─'*60}")

    findings = []
    sources = []
    recommendations = []

    # Step 1: Search web for topic
    print(f"  🔍  Searching the web...")

    try:
        import urllib.request, urllib.parse, json as _json
        encoded = urllib.parse.quote_plus(topic)
        url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
        req = urllib.request.Request(url, headers={"User-Agent": "TheAgency/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = _json.loads(r.read().decode())
    except Exception as e:
        print(f"  ⚠️   Web search failed: {e}")
        data = {}

    # Extract results
    if data.get("AbstractText"):
        findings.append(f"Summary: {data['AbstractText']}")
        sources.append(data.get("AbstractURL", "DuckDuckGo"))

    for topic_data in data.get("RelatedTopics", [])[:8]:
        if isinstance(topic_data, dict):
            text = topic_data.get("Text", "")
            url_link = topic_data.get("FirstURL", "")
            if text:
                findings.append(text)
                if url_link:
                    sources.append(url_link)

    # Step 2: LLM synthesis (if available)
    if use_llm:
        try:
            sys.path.insert(0, str(REPO_ROOT / "deepagents/libs/deepagents"))
            from deepagents import create_deep_agent
            from langchain_ollama import ChatOllama
            from langchain_core.messages import HumanMessage

            explorer_prompt = (REPO_ROOT / "specialized/specialized-autonomous-explorer.md").read_text()
            llm = ChatOllama(model="llama3.1", base_url="http://localhost:11434")

            search_results = "\n".join(findings[:10]) if findings else "No search results found."
            query = textwrap.dedent(f"""\
            EXPLORATION TOPIC: {topic}

            WEB SEARCH RESULTS:
            {search_results}

            Based on the search results (if any) and your own knowledge:

            1. Provide a structured exploration report covering:
               - Domain overview and key concepts
               - 3-5 concrete findings with details
               - Current state and trends

            2. Integration opportunities for the agency:
               - Could we spawn a new agent for this?
               - Could we fabricate a new tool?
               - How does this connect to our existing capabilities?

            3. Recommendations for next steps

            Save the report using write_output.
            Format as markdown per the explorer report template.
            """)

            agent = create_deep_agent(
                model=llm, tools=[],
                system_prompt=explorer_prompt,
                name="explorer"
            )
            response = agent.invoke({"messages": [HumanMessage(content=query)]})
            synthesis = response["messages"][-1].content

            # Save the full exploration report
            safe_topic = "".join(c if c.isalnum() or c in " _-" else "_" for c in topic)[:50]
            report_path = OUTPUTS_DIR / f"exploration_{safe_topic}_{datetime.now().strftime('%H%M%S')}.md"
            report_path.write_text(synthesis)
            print(f"  ✅  Exploration report saved: {report_path}")
        except Exception as e:
            print(f"  ⚠️   LLM synthesis failed: {e}")
            synthesis = "\n".join(findings[:5]) if findings else f"Explored: {topic}"
    else:
        synthesis = "\n".join(findings[:5]) if findings else f"Explored: {topic}"

    result = {
        "topic": topic,
        "timestamp": datetime.now().isoformat(),
        "findings_count": len(findings),
        "sources_count": len(sources),
        "findings": findings[:5],  # Top 5 for the ledger
        "sources": sources[:5],    # Top 5 sources
        "synthesis_preview": synthesis[:500] if len(synthesis) > 500 else synthesis,
        "report_saved": True,
    }

    print(f"  ✅  Exploration complete: {len(findings)} findings, {len(sources)} sources")
    return result


def explore_ecosystem() -> dict:
    """
    Explore the sahiixx GitHub ecosystem for integration opportunities.
    Scans repos, identifies patterns, and suggests integrations.
    """
    print(f"\n  🌐  Exploring sahiixx ecosystem...")
    print(f"  {'─'*60}")

    # Try to list repos via gh CLI
    repos = []
    try:
        result = subprocess.run(
            ["gh", "repo", "list", "sahiixx", "--limit", "50", "--json", "name,description,updatedAt"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            repos = json.loads(result.stdout)
        else:
            # Fall back to GitHub API
            import urllib.request, json as _json
            url = "https://api.github.com/users/sahiixx/repos?per_page=50&sort=updated"
            with urllib.request.urlopen(url, timeout=10) as r:
                repos = _json.loads(r.read().decode())
    except Exception as e:
        print(f"  ⚠️   GitHub scan failed: {e}")

    if not repos:
        return {
            "topic": "ecosystem_scan",
            "timestamp": datetime.now().isoformat(),
            "error": "Could not fetch repos",
            "repos_found": 0,
        }

    print(f"  📦  Found {len(repos)} repos")

    # Categorize repos
    categories = {
        "agent_frameworks": [],
        "docs": [],
        "deployment": [],
        "frontend": [],
        "tools": [],
        "empty": [],
    }

    for repo in repos:
        name = repo.get("name", "unknown")
        desc = repo.get("description", "") or ""
        desc_lower = desc.lower()

        if not desc:
            categories["empty"].append(name)
        elif "agent" in desc_lower or "swarm" in desc_lower:
            categories["agent_frameworks"].append(name)
        elif "doc" in desc_lower:
            categories["docs"].append(name)
        elif "deploy" in desc_lower or "cloudflare" in desc_lower:
            categories["deployment"].append(name)
        elif "frontend" in desc_lower or "ui" in desc_lower or "app" in desc_lower:
            categories["frontend"].append(name)
        else:
            categories["tools"].append(name)

    # Generate integration recommendations
    recommendations = []

    # Cross-repo integration suggestions
    if categories["agent_frameworks"]:
        agent_repos = categories["agent_frameworks"]
        recommendations.append(f"Cross-integrate agent repos: {', '.join(agent_repos[:5])}")

    if categories["docs"]:
        doc_repos = categories["docs"]
        recommendations.append(f"Unified docs from: {', '.join(doc_repos[:3])}")

    # Check for repos that could be managed by specific agency presets
    if categories["deployment"]:
        recommendations.append("Use 'security' preset for deployment repos")
    if categories["frontend"]:
        recommendations.append("Use 'full' or 'saas' preset for frontend projects")
    if categories["empty"]:
        empty_list = categories["empty"][:5]
        recommendations.append(f"Empty/stale repos that could be revived: {', '.join(empty_list)}")

    result = {
        "topic": "ecosystem_scan",
        "timestamp": datetime.now().isoformat(),
        "repos_found": len(repos),
        "categories": {k: len(v) for k, v in categories.items()},
        "agent_repos": categories["agent_frameworks"][:10],
        "doc_repos": categories["docs"][:10],
        "deployment_repos": categories["deployment"][:10],
        "empty_repos": categories["empty"][:10],
        "recommendations": recommendations,
    }

    # Save report
    report = f"""# Ecosystem Scan Report
**Date**: {datetime.now().isoformat()[:10]}
**Repos Found**: {len(repos)}

## Categories
- Agent Frameworks: {len(categories['agent_frameworks'])}
- Documentation: {len(categories['docs'])}
- Deployment: {len(categories['deployment'])}
- Frontend: {len(categories['frontend'])}
- Tools: {len(categories['tools'])}
- Empty/Stale: {len(categories['empty'])}

## Agent Framework Repos
{chr(10).join('- ' + r for r in categories['agent_frameworks'][:10])}

## Documentation Repos
{chr(10).join('- ' + r for r in categories['docs'][:10])}

## Empty/Stale (needs revival)
{chr(10).join('- ' + r for r in categories['empty'][:10])}

## Recommendations
{chr(10).join(f'{i+1}. {r}' for i, r in enumerate(recommendations))}

## Integration Opportunities
1. **Cross-swarm communication**: Wire agency-agents to sovereign-swarm via orchestration_bridge
2. **Unified docs**: Use docs agent to generate Mintlify docs for all active repos
3. **MCP ecosystem**: Add MCP servers for each agent framework repo
4. **Deployment automation**: Use devops agent + Cloudflare templates for auto-deploy
"""
    report_path = OUTPUTS_DIR / f"ecosystem_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    report_path.write_text(report)

    print(f"  ✅  Ecosystem scan saved: {report_path}")
    print(f"  💡  Recommendations:")
    for r in recommendations:
        print(f"      • {r}")

    return result


def run_exploration_cycle(
    custom_topic: str = None,
    ecosystem_mode: bool = False,
    use_llm: bool = True,
) -> dict:
    """
    Run one exploration cycle:

    1. Select a topic
    2. Explore it
    3. Record results in the ledger
    4. Return stats
    """
    ledger = load_ledger()
    topic = select_topic(ledger, custom_topic, ecosystem_mode)

    print(f"\n{'═'*65}")
    print(f"  🌐  Exploration Cycle — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  🎯  Topic: {topic[:60]}")
    print(f"{'═'*65}")

    # Explore
    if ecosystem_mode:
        result = explore_ecosystem()
    else:
        result = explore(topic, use_llm=use_llm)

    # Record in ledger
    topics = ledger.get("topics", {})
    topic_info = topics.get(topic, {"count": 0, "last": 0})
    topic_info["count"] += 1
    topic_info["last"] = time.time()
    topic_info["last_result"] = {
        "findings": result.get("findings_count", 0),
        "sources": result.get("sources_count", 0),
        "timestamp": result["timestamp"],
    }
    topics[topic] = topic_info

    explorations = ledger.get("explorations", [])
    explorations.append({
        "topic": topic,
        "timestamp": result["timestamp"],
        "findings": result.get("findings_count", 0),
    })

    # Keep last 50 explorations
    if len(explorations) > 50:
        explorations = explorations[-50:]

    ledger["topics"] = topics
    ledger["explorations"] = explorations
    save_ledger(ledger)

    result["explored_count"] = sum(t["count"] for t in topics.values())
    result["total_topics"] = len(topics)

    print(f"\n{'═'*65}")
    print(f"  📊  Ledger: {result['explored_count']} total explorations across {result['total_topics']} topics")
    print(f"{'═'*65}")

    return result


def show_history(limit: int = 10):
    """Show exploration history."""
    ledger = load_ledger()
    explorations = ledger.get("explorations", [])

    if not explorations:
        print("\n  No explorations recorded yet.")
        return

    print(f"\n  Exploration History ({len(explorations)} total):")
    print(f"  {'#':<4} {'Date':<12} {'Findings':<10} {'Topic'}")
    print(f"  {'─'*60}")

    for i, exp in enumerate(explorations[-limit:], 1):
        ts = exp.get("timestamp", "")[:10]
        findings = exp.get("findings", 0)
        topic = exp.get("topic", "")[:50]
        print(f"  {i:<4} {ts:<12} {findings:<10} {topic}")

    topics = ledger.get("topics", {})
    if topics:
        print(f"\n  Topic coverage ({len(topics)} topics):")
        for topic, info in sorted(topics.items(), key=lambda x: x[1]["last"], reverse=True)[:limit]:
            count = info["count"]
            last = datetime.fromtimestamp(info["last"]).strftime("%m/%d %H:%M") if info["last"] else "never"
            print(f"    [{count}x] {topic[:55]} (last: {last})")


# ── Daemon Mode ───────────────────────────────────────────────────────────────

def daemon_loop(interval_minutes: int = 120, ecosystem_first: bool = True):
    """Run exploration cycles in an infinite loop with given interval."""
    print(f"\n  ⏰  Exploration Daemon starting (every {interval_minutes} min)")
    print(f"      First cycle: ecosystem scan")

    cycle_num = 0
    ecosystem_done = False

    while True:
        cycle_num += 1
        print(f"\n{'='*65}")
        print(f"  Exploration Cycle #{cycle_num}")
        print(f"{'='*65}")

        try:
            if not ecosystem_done and ecosystem_first:
                run_exploration_cycle(ecosystem_mode=True, use_llm=True)
                ecosystem_done = True
            else:
                run_exploration_cycle(use_llm=True)
        except KeyboardInterrupt:
            print(f"\n  Daemon interrupted. Exiting cleanly.")
            break
        except Exception as e:
            print(f"\n  ❌  Cycle error: {e}")
            import traceback
            traceback.print_exc()

        print(f"\n  Sleeping for {interval_minutes} minutes...")
        print(f"  Next exploration at: {datetime.now().strftime('%H:%M')} +{interval_minutes}min")

        try:
            time.sleep(interval_minutes * 60)
        except KeyboardInterrupt:
            print(f"\n  Daemon interrupted. Exiting cleanly.")
            break

    print(f"\n  Daemon stopped after {cycle_num} cycles.")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Explorer Loop — Autonomous Knowledge Discovery")
    parser.add_argument("--topic", type=str, help="Custom exploration topic")
    parser.add_argument("--ecosystem", action="store_true", help="Scan sahiixx GitHub ecosystem")
    parser.add_argument("--daemon", action="store_true", help="Run in daemon mode")
    parser.add_argument("--interval", type=int, default=120, help="Minutes between cycles (default: 120)")
    parser.add_argument("--history", action="store_true", help="Show exploration history")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM synthesis (web_search only)")

    args = parser.parse_args()

    if args.history:
        show_history()

    elif args.daemon:
        daemon_loop(
            interval_minutes=args.interval,
            ecosystem_first=not args.no_llm,
        )

    elif args.topic:
        run_exploration_cycle(
            custom_topic=args.topic,
            use_llm=not args.no_llm,
        )

    elif args.ecosystem:
        run_exploration_cycle(
            ecosystem_mode=True,
            use_llm=not args.no_llm,
        )

    else:
        run_exploration_cycle(use_llm=not args.no_llm)
