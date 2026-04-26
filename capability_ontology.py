#!/usr/bin/env python3
"""
capability_ontology.py — Unified Capability Registry for the SAHIIXX Ecosystem

Scans all projects (agency-agents, friday-os, goose-aios, sovereign-swarm-v2,
sahiixx-bus, omni-workspace) and normalizes their capabilities into a single
queryable ontology.

Each capability record carries:
  - name + description (unified vocabulary)
  - source_project + source_file (traceability)
  - capability_type: agent | tool | service | skill | role
  - keywords (extracted + manually curated)
  - raw_text (for re-scanning)

Matching is done via simple TF-weighted cosine similarity using only stdlib
+ numpy (no sentence-transformers, no API calls).

Usage:
  # Refresh the registry from disk
  python3 capability_ontology.py --refresh

  # Resolve a goal
  python3 capability_ontology.py --resolve "Build a reverse-engineering pipeline"

  # Show top capabilities across all projects
  python3 capability_ontology.py --list --limit 20
"""

from __future__ import annotations

import argparse
import ast
import json
import math
import os
import re
import sqlite3
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# numpy is optional — falls back to pure Python cosine
try:
    import numpy as np
except Exception:
    np = None  # type: ignore

REPO_ROOT = Path(__file__).parent.resolve()
ECOSYSTEM_ROOT = REPO_ROOT.parent
DB_PATH = REPO_ROOT / "memory" / "capability_registry.db"

# ── Stopwords ────────────────────────────────────────────────────────────────
STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "must", "shall", "can", "need", "dare",
    "ought", "used", "to", "of", "in", "for", "on", "with", "at", "by",
    "from", "as", "into", "through", "during", "before", "after", "above",
    "below", "between", "under", "and", "but", "or", "yet", "so", "if",
    "because", "although", "though", "while", "where", "when", "that",
    "which", "who", "whom", "whose", "what", "this", "these", "those",
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her",
    "us", "them", "my", "your", "his", "its", "our", "their",
}


# ── Data Class ───────────────────────────────────────────────────────────────

@dataclass
class CapabilityRecord:
    name: str
    description: str
    source_project: str
    source_file: str
    source_entity: str
    capability_type: str  # agent | tool | service | skill | role | subsystem
    keywords: list[str]
    raw_text: str

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "source_project": self.source_project,
            "source_file": self.source_file,
            "source_entity": self.source_entity,
            "capability_type": self.capability_type,
            "keywords": self.keywords,
            "raw_text": self.raw_text,
        }


# ── Tokenization ─────────────────────────────────────────────────────────────

def tokenize(text: str) -> list[str]:
    """Lowercase, strip punctuation, remove stopwords."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9_\s]", " ", text)
    tokens = [t for t in text.split() if len(t) > 2 and t not in STOPWORDS]
    return tokens


def compute_tf(text: str) -> dict[str, float]:
    tokens = tokenize(text)
    if not tokens:
        return {}
    counts = Counter(tokens)
    max_count = max(counts.values())
    return {term: 0.5 + 0.5 * (c / max_count) for term, c in counts.items()}


def cosine_similarity(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    if not vec_a or not vec_b:
        return 0.0
    keys = set(vec_a.keys()) & set(vec_b.keys())
    if not keys:
        return 0.0
    if np is not None:
        a = np.array([vec_a[k] for k in keys])
        b = np.array([vec_b[k] for k in keys])
        norm = np.linalg.norm(a) * np.linalg.norm(b)
        return float(np.dot(a, b) / norm) if norm else 0.0
    # Pure Python fallback
    dot = sum(vec_a[k] * vec_b[k] for k in keys)
    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


# ── Registry Database ────────────────────────────────────────────────────────

class CapabilityRegistry:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS capabilities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    source_project TEXT,
                    source_file TEXT,
                    source_entity TEXT,
                    capability_type TEXT,
                    keywords TEXT,  -- JSON list
                    raw_text TEXT,
                    vector TEXT     -- JSON dict of term->weight
                );
                CREATE INDEX IF NOT EXISTS idx_cap_project ON capabilities(source_project);
                CREATE INDEX IF NOT EXISTS idx_cap_type ON capabilities(capability_type);
                CREATE INDEX IF NOT EXISTS idx_cap_name ON capabilities(name);
            """)

    def clear_project(self, project: str):
        with self._conn() as conn:
            conn.execute("DELETE FROM capabilities WHERE source_project = ?", (project,))

    def insert(self, rec: CapabilityRecord):
        vec = compute_tf(f"{rec.name} {rec.description} {' '.join(rec.keywords)} {rec.raw_text}")
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO capabilities
                (name, description, source_project, source_file, source_entity, capability_type, keywords, raw_text, vector)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rec.name, rec.description, rec.source_project, rec.source_file,
                rec.source_entity, rec.capability_type,
                json.dumps(rec.keywords), rec.raw_text, json.dumps(vec),
            ))

    def count(self) -> int:
        with self._conn() as conn:
            row = conn.execute("SELECT COUNT(*) FROM capabilities").fetchone()
            return row[0] if row else 0

    def list_all(self, limit: int = 100, project: Optional[str] = None, cap_type: Optional[str] = None) -> list[dict]:
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            where = []
            params = []
            if project:
                where.append("source_project = ?")
                params.append(project)
            if cap_type:
                where.append("capability_type = ?")
                params.append(cap_type)
            sql = "SELECT * FROM capabilities"
            if where:
                sql += " WHERE " + " AND ".join(where)
            sql += f" LIMIT {limit}"
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    def resolve(self, goal: str, top_n: int = 5) -> list[dict]:
        """Find the best capabilities for a goal using TF-weighted cosine similarity."""
        goal_vec = compute_tf(goal)
        if not goal_vec:
            return []
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM capabilities").fetchall()
        scored = []
        for r in rows:
            try:
                cap_vec = json.loads(r["vector"] or "{}")
            except Exception:
                continue
            score = cosine_similarity(goal_vec, cap_vec)
            if score > 0.01:
                scored.append((score, dict(r)))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{"score": round(s, 4), **rec} for s, rec in scored[:top_n]]


# ── Crawler Helpers ──────────────────────────────────────────────────────────

EXCLUDED_DIRS = {'.venv', 'venv', 'node_modules', '__pycache__', '.git', '.pytest_cache', '.ruff_cache', 'build', 'dist'}
MAX_FILE_BYTES = 500_000


def should_skip_path(path: Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in path.parts)


# ── Crawlers ─────────────────────────────────────────────────────────────────

class Crawler:
    def __init__(self, registry: CapabilityRegistry):
        self.registry = registry

    # ── agency-agents ────────────────────────────────────────────────────────

    def crawl_agency_agents(self):
        proj = "agency-agents"
        self.registry.clear_project(proj)

        # 1. Agent markdown files
        agent_dirs = [
            "engineering", "design", "marketing", "specialized", "sales",
            "product", "testing", "support", "strategy", "project-management",
            "paid-media", "game-development", "spatial-computing", "business",
            "real-estate",
        ]
        for d in agent_dirs:
            dir_path = REPO_ROOT / d
            if not dir_path.exists():
                continue
            for md_file in dir_path.rglob("*.md"):
                content = md_file.read_text(errors="ignore")
                name = md_file.stem
                # Extract frontmatter description
                desc = ""
                if content.startswith("---"):
                    fm = content.split("---")[1] if len(content.split("---")) > 1 else ""
                    for line in fm.splitlines():
                        if line.lower().startswith("description:"):
                            desc = line.split(":", 1)[1].strip().strip('"')
                if not desc:
                    desc = content[:200].replace("\n", " ")
                keywords = tokenize(f"{name} {desc} {content[:500]}")
                self.registry.insert(CapabilityRecord(
                    name=name, description=desc, source_project=proj,
                    source_file=str(md_file.relative_to(REPO_ROOT)),
                    source_entity=name, capability_type="agent",
                    keywords=keywords, raw_text=content[:1000],
                ))

        # 2. MCP Tools from mcp_tools.py
        mcp_file = REPO_ROOT / "mcp_tools.py"
        if mcp_file.exists():
            text = mcp_file.read_text(errors="ignore")
            # Find @tool decorated functions
            for match in re.finditer(r'@tool\s*\n(?:@[^\n]+\n)*def\s+(\w+)\s*\([^)]*\)\s*(?:->\s*\w+\s*)?:\s*\n\s*"""(.*?)"""', text, re.DOTALL):
                func_name, doc = match.groups()
                desc = doc.strip().split("\n")[0][:300]
                keywords = tokenize(f"{func_name} {desc}")
                self.registry.insert(CapabilityRecord(
                    name=func_name, description=desc, source_project=proj,
                    source_file="mcp_tools.py", source_entity=func_name,
                    capability_type="tool", keywords=keywords,
                    raw_text=doc.strip()[:500],
                ))

        # 3. Subsystems
        for subsys, meta in {
            "claude_agency": "High-stakes Claude-powered missions with A2A messaging and safety",
            "ollama_swarm": "Local fast dev swarm using Ollama llama3.1 pipeline",
            "omni_analysis": "Reverse engineering, binary analysis, CRM sync, Frida sensing",
            "tool_fabrication": "Runtime synthesis of new LangChain-compatible tools",
            "agent_spawn": "Dynamic creation of new specialist agent personas",
            "self_evolution": "Autonomous prompt improvement and agent quality scoring",
        }.items():
            keywords = tokenize(f"{subsys} {meta}")
            self.registry.insert(CapabilityRecord(
                name=subsys, description=meta, source_project=proj,
                source_file="agi_director.py", source_entity=subsys,
                capability_type="subsystem", keywords=keywords,
                raw_text=meta,
            ))

        print(f"  ✅  {proj}: {self.registry.count()} capabilities")

    # ── friday-os ────────────────────────────────────────────────────────────

    def crawl_friday_os(self):
        proj = "friday-os"
        self.registry.clear_project(proj)
        tools_dir = ECOSYSTEM_ROOT / proj / "friday" / "tools"
        if not tools_dir.exists():
            print(f"  ⚠️  {proj}: tools dir not found")
            return
        for py_file in tools_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            text = py_file.read_text(errors="ignore")
            # Extract Tool subclass name and description
            for match in re.finditer(r'class\s+(\w+)\s*\(\s*Tool\s*\):\s*\n\s*name\s*=\s*["\']([^"\']+)["\']\s*\n\s*description\s*=\s*["\']([^"\']+)["\']', text):
                cls_name, name, desc = match.groups()
                keywords = tokenize(f"{name} {desc}")
                self.registry.insert(CapabilityRecord(
                    name=name, description=desc, source_project=proj,
                    source_file=f"friday/tools/{py_file.name}", source_entity=cls_name,
                    capability_type="tool", keywords=keywords,
                    raw_text=text[:500],
                ))
        print(f"  ✅  {proj}: {self.registry.count()} total capabilities")

    # ── goose-aios ───────────────────────────────────────────────────────────

    def crawl_goose_aios(self):
        proj = "goose-aios"
        self.registry.clear_project(proj)
        agent_file = ECOSYSTEM_ROOT / proj / "agent.py"
        if agent_file.exists():
            text = agent_file.read_text(errors="ignore")
            # Extract GOOSE tool descriptions from docstrings or class defs
            for match in re.finditer(r'def\s+(\w+)\s*\([^)]*\)\s*(?:->\s*\w+\s*)?:\s*\n\s*"""(.*?)"""', text, re.DOTALL):
                func_name, doc = match.groups()
                desc = doc.strip().split("\n")[0][:300]
                keywords = tokenize(f"{func_name} {desc}")
                self.registry.insert(CapabilityRecord(
                    name=func_name, description=desc, source_project=proj,
                    source_file="agent.py", source_entity=func_name,
                    capability_type="tool", keywords=keywords,
                    raw_text=doc.strip()[:500],
                ))
        print(f"  ✅  {proj}: {self.registry.count()} total capabilities")

    # ── sovereign-swarm-v2 ───────────────────────────────────────────────────

    def crawl_sovereign_swarm(self):
        proj = "sovereign-swarm-v2"
        self.registry.clear_project(proj)
        swarm_dir = ECOSYSTEM_ROOT / proj / "sovereign_swarm"
        if not swarm_dir.exists():
            print(f"  ⚠️  {proj}: dir not found")
            return
        # Scan Python files for class definitions that look like agents/capabilities
        for py_file in swarm_dir.rglob("*.py"):
            if py_file.name.startswith("_") or should_skip_path(py_file):
                continue
            if py_file.stat().st_size > MAX_FILE_BYTES:
                continue
            text = py_file.read_text(errors="ignore")
            for match in re.finditer(r'class\s+(\w+)\s*\([^)]*\):', text):
                cls_name = match.group(1)
                # Extract docstring if present — use simple slicing to avoid backtracking
                desc = ""
                cls_pos = text.find(f"class {cls_name}")
                if cls_pos != -1:
                    after = text[cls_pos:cls_pos+800]
                    for quote in ('"""', "'''"):
                        qpos = after.find(quote)
                        if qpos != -1:
                            end = after.find(quote, qpos+3)
                            if end != -1:
                                desc = after[qpos+3:end].strip().split("\n")[0][:300]
                                break
                if not desc:
                    desc = f"{cls_name} capability"
                keywords = tokenize(f"{cls_name} {desc}")
                cap_type = "agent" if "agent" in cls_name.lower() else "service"
                self.registry.insert(CapabilityRecord(
                    name=cls_name, description=desc, source_project=proj,
                    source_file=str(py_file.relative_to(ECOSYSTEM_ROOT / proj)),
                    source_entity=cls_name, capability_type=cap_type,
                    keywords=keywords, raw_text=text[:500],
                ))
        print(f"  ✅  {proj}: {self.registry.count()} total capabilities")

    # ── sahiixx-bus ──────────────────────────────────────────────────────────

    def crawl_sahiixx_bus(self):
        proj = "sahiixx-bus"
        self.registry.clear_project(proj)
        bus_dir = ECOSYSTEM_ROOT / proj / "sahiixx_bus"
        if not bus_dir.exists():
            print(f"  ⚠️  {proj}: dir not found")
            return
        for py_file in bus_dir.rglob("*.py"):
            if py_file.name.startswith("_") or should_skip_path(py_file):
                continue
            if py_file.stat().st_size > MAX_FILE_BYTES:
                continue
            text = py_file.read_text(errors="ignore")
            for match in re.finditer(r'class\s+(\w+)\s*\([^)]*\):', text):
                cls_name = match.group(1)
                desc = ""
                cls_pos = text.find(f"class {cls_name}")
                if cls_pos != -1:
                    after = text[cls_pos:cls_pos+800]
                    for quote in ('"""', "'''"):
                        qpos = after.find(quote)
                        if qpos != -1:
                            end = after.find(quote, qpos+3)
                            if end != -1:
                                desc = after[qpos+3:end].strip().split("\n")[0][:300]
                                break
                if not desc:
                    desc = f"{cls_name} bus primitive"
                keywords = tokenize(f"{cls_name} {desc}")
                self.registry.insert(CapabilityRecord(
                    name=cls_name, description=desc, source_project=proj,
                    source_file=str(py_file.relative_to(ECOSYSTEM_ROOT / proj)),
                    source_entity=cls_name, capability_type="service",
                    keywords=keywords, raw_text=text[:500],
                ))
        print(f"  ✅  {proj}: {self.registry.count()} total capabilities")

    # ── omni-workspace ───────────────────────────────────────────────────────

    def crawl_omni(self):
        proj = "omni-workspace"
        self.registry.clear_project(proj)
        omni_dir = ECOSYSTEM_ROOT / "workspace"
        if not omni_dir.exists():
            print(f"  ⚠️  {proj}: dir not found")
            return
        for py_file in omni_dir.rglob("*.py"):
            if py_file.name.startswith("_") or should_skip_path(py_file):
                continue
            if py_file.stat().st_size > MAX_FILE_BYTES:
                continue
            text = py_file.read_text(errors="ignore")
            for match in re.finditer(r'class\s+(\w+)\s*\([^)]*\):', text):
                cls_name = match.group(1)
                desc = ""
                cls_pos = text.find(f"class {cls_name}")
                if cls_pos != -1:
                    after = text[cls_pos:cls_pos+800]
                    for quote in ('"""', "'''"):
                        qpos = after.find(quote)
                        if qpos != -1:
                            end = after.find(quote, qpos+3)
                            if end != -1:
                                desc = after[qpos+3:end].strip().split("\n")[0][:300]
                                break
                if not desc:
                    desc = f"{cls_name} OMNI capability"
                keywords = tokenize(f"{cls_name} {desc}")
                cap_type = "tool" if "Client" in cls_name or "Analyzer" in cls_name or "Actuator" in cls_name else "service"
                self.registry.insert(CapabilityRecord(
                    name=cls_name, description=desc, source_project=proj,
                    source_file=str(py_file.relative_to(omni_dir)),
                    source_entity=cls_name, capability_type=cap_type,
                    keywords=keywords, raw_text=text[:500],
                ))
        print(f"  ✅  {proj}: {self.registry.count()} total capabilities")

    def crawl_all(self):
        print("\n  🕷️  Crawling SAHIIXX Ecosystem for capabilities...\n")
        self.crawl_agency_agents()
        self.crawl_friday_os()
        self.crawl_goose_aios()
        self.crawl_sovereign_swarm()
        self.crawl_sahiixx_bus()
        self.crawl_omni()
        total = self.registry.count()
        print(f"\n  📊  Total capabilities in registry: {total}")


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Unified Capability Registry")
    parser.add_argument("--refresh", action="store_true", help="Re-crawl all projects")
    parser.add_argument("--resolve", type=str, help="Resolve a goal to capabilities")
    parser.add_argument("--list", action="store_true", help="List capabilities")
    parser.add_argument("--project", type=str, help="Filter by project")
    parser.add_argument("--type", type=str, help="Filter by capability type")
    parser.add_argument("--limit", type=int, default=20, help="Limit results")
    args = parser.parse_args()

    registry = CapabilityRegistry()
    crawler = Crawler(registry)

    if args.refresh:
        crawler.crawl_all()
        return

    if args.resolve:
        results = registry.resolve(args.resolve, top_n=args.limit)
        print(f"\n  🎯  Goal: {args.resolve}\n")
        if not results:
            print("  No matching capabilities found.")
        for i, r in enumerate(results, 1):
            print(f"  {i}. [{r['score']:.3f}] {r['name']} ({r['capability_type']}) — {r['source_project']}")
            print(f"     {r['description'][:100]}")
        print()
        return

    if args.list:
        rows = registry.list_all(limit=args.limit, project=args.project, cap_type=args.type)
        print(f"\n  📋  Capabilities ({len(rows)} shown)\n")
        for r in rows:
            print(f"  • [{r['capability_type']:12s}] {r['name']:30s}  {r['source_project']:20s}  {r['description'][:60]}")
        print()
        return

    # Default: show count + hint
    count = registry.count()
    print(f"\n  📊  Registry has {count} capabilities.")
    print("  Run with --refresh to populate, --resolve 'goal' to match, or --list to browse.\n")


if __name__ == "__main__":
    main()
