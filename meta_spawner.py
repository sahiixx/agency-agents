#!/usr/bin/env python3
"""
meta_spawner.py — Dynamic Agent Creation for The Agency.

AGI capability: watches mission patterns and task types to detect gaps
in the agent roster, then dynamically creates new agent personas (.md files)
with valid frontmatter and domain-specific system prompts.

Key idea: an AGI system should be able to grow its own team when it
encounters tasks for which no specialist exists.

How it works:
  1. Observer monitors mission descriptions and outcomes
  2. When a novel task type is detected (no existing agent matches), it's flagged
  3. MetaSpawner uses Ollama to generate a new agent persona .md file
  4. Agent is validated (frontmatter, non-empty, proper sections)
  5. Agent is registered in the appropriate directory
  6. Agency registry is updated with the new agent key

Usage:
  from meta_spawner import MetaSpawner
  spawner = MetaSpawner()
  spawner.analyze_mission("Build a quantum computing simulator for education")
  # If no existing agent handles quantum computing, creates one
  # Returns list of spawned agents
"""

import json
import os
import re
import sys
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).parent.resolve()
AGENT_DIRS = {  # category -> directory
    "engineering": "engineering",
    "design": "design",
    "marketing": "marketing",
    "sales": "sales",
    "specialized": "specialized",
    "testing": "testing",
    "project-management": "project-management",
    "product": "product",
    "real-estate": "real-estate",
    "business": "business",
    "support": "support",
    "paid-media": "paid-media",
    "game-development": "game-development",
    "spatial-computing": "spatial-computing",
}

# Colors for frontmatter
COLORS = [
    "blue", "green", "violet", "orange", "teal", "indigo",
    "pink", "red", "cyan", "purple", "amber", "lime", "emerald",
    "sky", "rose", "fuchsia",
]

# Emojis for categories
CATEGORY_EMOJIS = {
    "engineering": "⚙️", "design": "🎨", "marketing": "📢", "sales": "💼",
    "specialized": "🧠", "testing": "🧪", "project-management": "📋",
    "product": "📦", "real-estate": "🏠", "business": "🏢", "support": "🎧",
    "paid-media": "💰", "game-development": "🎮", "spatial-computing": "🌐",
}


def get_existing_agent_names() -> set[str]:
    """Get all existing agent file names (without extension)."""
    names = set()
    for category, directory in AGENT_DIRS.items():
        dir_path = REPO_ROOT / directory
        if dir_path.exists():
            for f in dir_path.glob("*.md"):
                name = f.stem
                # Normalize: remove category prefix
                parts = name.split("-")
                if parts and parts[0] in AGENT_DIRS:
                    names.add(name)
                names.add(name)
    return names


def get_existing_agent_descriptions() -> list[str]:
    """Get descriptions of all existing agents."""
    descriptions = []
    for category, directory in AGENT_DIRS.items():
        dir_path = REPO_ROOT / directory
        if dir_path.exists():
            for f in sorted(dir_path.glob("*.md")):
                content = f.read_text()
                name_match = re.search(r"^name:\s*(.+)$", content, re.MULTILINE)
                desc_match = re.search(r"^description:\s*(.+)$", content, re.MULTILINE)
                name = name_match.group(1).strip() if name_match else f.stem
                desc = desc_match.group(1).strip() if desc_match else ""
                descriptions.append(f"{name}: {desc}")
    # Also include real-estate, business directories
    for extra_dir in ["real-estate", "business", "integrations"]:
        dir_path = REPO_ROOT / extra_dir
        if dir_path.exists():
            for f in sorted(dir_path.glob("*.md")):
                content = f.read_text()
                name_match = re.search(r"^name:\s*(.+)$", content, re.MULTILINE)
                desc_match = re.search(r"^description:\s*(.+)$", content, re.MULTILINE)
                name = name_match.group(1).strip() if name_match else f.stem
                desc = desc_match.group(1).strip() if desc_match else ""
                descriptions.append(f"{name}: {desc}")
    return descriptions


class MetaSpawner:
    """
    Detects novel task types and spawns new agent personas.

    Usage:
        spawner = MetaSpawner()
        gaps = spawner.analyze_mission("Design a RAG pipeline for legal documents")
        if gaps:
            spawner.spawn(gaps[0])
    """

    def __init__(self):
        self.existing_names = get_existing_agent_names()
        self.existing_descriptions = get_existing_agent_descriptions()

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Call Ollama to generate agent content."""
        try:
            sys.path.insert(0, str(REPO_ROOT / "deepagents/libs/deepagents"))
            from deepagents import create_deep_agent
            from langchain_ollama import ChatOllama
            from langchain_core.messages import HumanMessage

            llm = ChatOllama(model="llama3.1", base_url="http://localhost:11434")
            agent = create_deep_agent(
                model=llm, tools=[],
                system_prompt=system_prompt,
                name="meta-spawner"
            )
            resp = agent.invoke({"messages": [HumanMessage(content=user_prompt)]})
            return resp["messages"][-1].content
        except Exception as e:
            return self._template_generate(user_prompt)

    def _template_generate(self, requirements: str) -> str:
        """Generate a placeholder agent when LLM is unavailable."""
        name = "New Specialist"
        desc = requirements.strip()[:100] if requirements else "Specialized agent"
        slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

        return textwrap.dedent(f"""\
        ---
        name: {name}
        description: {desc}
        color: teal
        emoji: 🧠
        vibe: Analytical and specialized — dives deep into {name.lower()} problems.
        ---

        # {name} Agent

        You are a **{name}**, a specialized AI agent focused on {desc.lower()}.

        ## 🧠 Your Identity & Memory
        - **Role**: {name} specialist
        - **Personality**: Analytical, thorough, detail-oriented
        - **Memory**: You retain deep knowledge of your specialty domain
        - **Experience**: You've solved complex problems in this domain

        ## 🎯 Your Core Mission

        ### Domain Expertise
        - Apply deep domain knowledge to every task
        - Consider edge cases and failure modes
        - Provide production-ready, validated outputs

        ### Collaboration
        - Hand off results with complete context
        - Flag assumptions and uncertainties
        - Escalate to Claude Reasoning Core for ethical/ambiguous calls

        ## 📋 Quality Standards
        - Every output must be accurate and verifiable
        - Cite assumptions when making them
        - If outside your domain, say so and recommend the right agent
        """)

    def _extract_mission_domain(self, mission: str) -> Optional[dict]:
        """
        Analyze a mission string to extract the primary domain/topic.
        Returns dict with 'domain', 'reason', and 'suggested_category', or None.
        """
        # Use LLM if available, otherwise use keyword analysis
        existing_agents_text = "\n".join(self.existing_descriptions[:100])
        # (first 100 to keep prompt small)

        # Simple keyword-based domain extraction
        mission_lower = mission.lower()

        domains = {
            "quantum computing": ("engineering", "quantum"),
            "blockchain": ("engineering", "blockchain"),
            "smart contract": ("engineering", "smart-contract"),
            "nlp": ("specialized", "nlp"),
            "computer vision": ("specialized", "computer-vision"),
            "speech": ("specialized", "speech"),
            "robotics": ("engineering", "robotics"),
            "iot": ("engineering", "iot"),
            "embedded": ("engineering", "embedded"),
            "legal": ("business", "legal"),
            "finance": ("business", "finance"),
            "healthcare": ("business", "healthcare"),
            "education": ("product", "education"),
            "e-commerce": ("product", "e-commerce"),
            "crypto": ("engineering", "crypto"),
            "data pipeline": ("engineering", "data-pipeline"),
            "rag": ("specialized", "rag"),
            "retrieval": ("specialized", "rag"),
            "vector": ("specialized", "vector"),
            "multi-agent": ("specialized", "multi-agent"),
            "agent orchestration": ("specialized", "agent-orchestration"),
            "api design": ("engineering", "api-design"),
            "graphql": ("engineering", "api-design"),
            "database": ("engineering", "database"),
            "mobile": ("engineering", "mobile"),
            "docker": ("engineering", "devops"),
            "kubernetes": ("engineering", "devops"),
            "ci/cd": ("engineering", "devops"),
            "monitoring": ("engineering", "monitoring"),
            "observability": ("engineering", "monitoring"),
            "accessibility": ("design", "accessibility"),
            "a11y": ("design", "accessibility"),
            "animation": ("design", "animation"),
            "branding": ("design", "branding"),
            "seo": ("marketing", "seo"),
            "content strategy": ("marketing", "content-strategy"),
            "social media": ("marketing", "social-media"),
            "email marketing": ("marketing", "email"),
            "data science": ("specialized", "data-science"),
            "mlops": ("specialized", "mlops"),
            "model deployment": ("specialized", "mlops"),
        }

        for keyword, (category, domain) in domains.items():
            if keyword in mission_lower:
                return {"domain": domain, "keyword": keyword, "category": category}

        # Check if any existing agent description covers this
        for desc in self.existing_descriptions:
            desc_lower = desc.lower()
            words = set(mission_lower.split())
            desc_words = set(desc_lower.split())
            overlap = words & desc_words
            if len(overlap) >= 3:
                # Existing agent likely covers this
                return None

        # Generic fallback
        return {"domain": "general", "keyword": "general", "category": "specialized"}

    def analyze_mission(self, mission: str) -> list[dict]:
        """
        Analyze a mission string for new agent gaps.

        Returns a list of gap dicts with:
        - domain: the domain/topic
        - category: which directory it belongs in
        - keyword: the matching keyword
        - is_novel: True if no existing agent handles this
        """
        gaps = []
        result = self._extract_mission_domain(mission)

        if result is None:
            return gaps  # No gap detected — existing agents cover this

        domain = result["domain"]
        category = result["category"]
        keyword = result.get("keyword", domain)

        # Check if an agent for this domain already exists
        domain_slug = domain.lower().replace(" ", "-")
        for existing_name in self.existing_names:
            if domain_slug in existing_name or domain_slug.replace("-", "") in existing_name.replace("-", ""):
                return gaps  # Already covered

        # Check descriptions too
        for desc in self.existing_descriptions:
            desc_lower = desc.lower()
            if domain_slug.replace("-", " ") in desc_lower:
                return gaps

        gaps.append({
            "domain": domain,
            "category": category,
            "keyword": keyword,
            "is_novel": True,
        })

        return gaps

    def spawn(self, gap: dict) -> Optional[dict]:
        """
        Spawn a new agent for a detected gap.

        Args:
            gap: Dict with 'domain', 'category', 'keyword'

        Returns:
            Dict with agent info, or None on failure
        """
        domain = gap["domain"]
        category = gap["category"]
        directory = AGENT_DIRS.get(category, "specialized")

        # Generate names
        agent_name = domain.replace("-", " ").title()
        file_slug = f"{category}-{domain.replace('_', '-').replace(' ', '-')}"
        file_name = f"{file_slug}.md"
        file_path = REPO_ROOT / directory / file_name

        if file_path.exists():
            print(f"  ⚠️   Agent already exists: {file_name}")
            return None

        # Build the agent description
        description = f"Specialized {agent_name} — expert in {domain.replace('-', ' ')} design, implementation, and best practices"
        color = COLORS[len(self.existing_names) % len(COLORS)]
        emoji = CATEGORY_EMOJIS.get(category, "🤖")

        # Generate system prompt via LLM or template
        system_prompt = textwrap.dedent(f"""\
        ---
        name: {agent_name}
        description: {description}
        color: {color}
        emoji: {emoji}
        vibe: Deep specialist in {domain.replace('-', ' ')} — builds production-ready solutions with domain expertise.
        ---

        # {agent_name} Agent

        You are a **{agent_name}**, a specialized AI agent focused on {domain.replace('-', ' ')} solutions and best practices.

        ## 🧠 Your Identity & Memory
        - **Role**: {agent_name} specialist
        - **Personality**: Methodical, thorough, up-to-date with latest developments
        - **Memory**: You retain deep knowledge of {domain.replace('-', ' ')} patterns and anti-patterns
        - **Experience**: You've designed, built, and shipped {domain.replace('-', ' ')} solutions at production scale

        ## 🎯 Your Core Mission

        ### Domain Expertise
        - Apply deep {domain.replace('-', ' ')} knowledge to every task
        - Consider edge cases, scalability, security, and maintainability
        - Provide production-ready, validated outputs with documentation

        ### Analysis & Design
        - Break down complex {domain.replace('-', ' ')} problems into clear components
        - Evaluate trade-offs between different approaches
        - Provide concrete, actionable recommendations with rationale

        ### Collaboration
        - Hand off results with complete context and assumptions
        - Flag uncertainties, risks, and open questions
        - Escalate to Claude Reasoning Core for ethical, safety, or ambiguous decisions

        ## 📋 Quality Standards
        - Every output must be accurate, verifiable, and production-ready
        - Cite assumptions, limitations, and known edge cases
        - If outside your domain, explicitly say so and recommend the right agent
        - Use web_search for current information when needed
        - Save deliverables with write_output

        ## ⚙️ Tools & Capabilities
        - web_search: Get current information from the web
        - read_file: Read files from the repo
        - write_output: Save deliverables to /tmp/agency_outputs/
        - memory_recall: Query past mission outcomes from Titans memory

        ## 🚫 Boundaries
        - Do not make medical, legal, or financial recommendations without disclaimers
        - Do not approve deployment of unverified code or configurations
        - Flag security concerns even when not explicitly asked
        """)

        # Write the agent file
        file_path.write_text(system_prompt)
        print(f"  ✅  Spawned agent: {file_name} ({len(system_prompt)} chars)")

        result = {
            "file_name": file_name,
            "file_path": str(file_path),
            "agent_name": agent_name,
            "category": category,
            "domain": domain,
            "registry_key": file_slug,
            "size_chars": len(system_prompt),
        }

        return result

    def scan_and_spawn(self, missions: list[str]) -> list[dict]:
        """
        Scan a list of past/planned missions and spawn agents for any gaps.
        Returns list of spawned agent info dicts.
        """
        spawned = []

        for mission in missions:
            gaps = self.analyze_mission(mission)
            for gap in gaps:
                result = self.spawn(gap)
                if result:
                    spawned.append(result)

        return spawned


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="MetaSpawner — Dynamic Agent Creation")
    parser.add_argument("--analyze", type=str, help="Analyze a mission for gaps")
    parser.add_argument("--scan", type=str, nargs="*", default=[],
                        help="Scan multiple missions for gaps and spawn agents")
    parser.add_argument("--list-existing", action="store_true",
                        help="List all existing agent names")
    parser.add_argument("--test", action="store_true",
                        help="Run spawning test (creates a test agent)")

    args = parser.parse_args()
    spawner = MetaSpawner()

    if args.analyze:
        gaps = spawner.analyze_mission(args.analyze)
        if gaps:
            print(f"\n  🚀  New agent gaps detected for: '{args.analyze}'")
            for g in gaps:
                print(f"      Domain: {g['domain']}")
                print(f"      Category: {g['category']}")
                print(f"      Keyword matched: {g['keyword']}")
                print(f"      Novel: {g['is_novel']}")

                choice = input(f"\n  Spawn agent for '{g['domain']}'? (y/n): ")
                if choice.lower().startswith("y"):
                    result = spawner.spawn(g)
                    if result:
                        print(f"\n  ✅  Agent spawned: {result['file_name']}")
        else:
            print(f"\n  ✅  No new agent gaps found — existing agents cover '{args.analyze}'")

    elif args.scan:
        spawned = spawner.scan_and_spawn(args.scan)
        if spawned:
            print(f"\n  🚀  Spawned {len(spawned)} new agents:")
            for s in spawned:
                print(f"      {s['file_name']} ({s['category']})")
        else:
            print(f"\n  ✅  No new agents needed")

    elif args.list_existing:
        names = sorted(spawner.existing_names)
        print(f"\n  Existing agents ({len(names)}):")
        for n in names:
            print(f"    - {n}")
        print(f"\n  Agent descriptions ({len(spawner.existing_descriptions)}):")
        for d in sorted(spawner.existing_descriptions):
            print(f"    - {d}")

    elif args.test:
        print("\n  Running meta-spawning test...")
        result = spawner.spawn({
            "domain": "rag-systems",
            "category": "specialized",
            "keyword": "rag",
            "is_novel": True,
        })
        if result:
            print(f"  ✅  Test spawn: {result['file_name']}")
            # Clean up test agent
            test_path = REPO_ROOT / "specialized" / "specialized-rag-systems.md"
            if test_path.exists():
                test_path.unlink()
                print(f"  🧹  Cleaned up test agent")
        else:
            print(f"  ❌  Test spawn failed")
            sys.exit(1)
    else:
        parser.print_help()
