#!/usr/bin/env python3
"""
mcp_tools.py — MCP tool layer for The Agency.

Wraps external capabilities as LangChain-compatible tools so any agent
can call them via the standard tool interface. No MCP server required —
these are local MCP-style tool definitions that follow the protocol schema.

Tools available:
  web_search      — fetch live search results (via DuckDuckGo, no key needed)
  read_file       — read any file in the repo
  write_file      — write structured output to /tmp/agency_outputs/
  summarize_url   — fetch and summarize a URL
  code_lint       — run ruff lint on a code snippet
  memory_recall   — query Titans memory for past mission insights
"""

import json
import subprocess
import tempfile
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Optional

from langchain_core.tools import tool

OUTPUTS_DIR = Path("/tmp/agency_outputs")
OUTPUTS_DIR.mkdir(exist_ok=True)

REPO_ROOT = Path(__file__).parent.resolve()


# ── Tool 1: Web Search (DuckDuckGo instant answer, no API key) ─────────────
@tool
def web_search(query: str) -> str:
    """Search the web for current information. Returns top results as text."""
    try:
        encoded = urllib.parse.quote_plus(query)
        url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
        req = urllib.request.Request(url, headers={"User-Agent": "TheAgency/1.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode())

        results = []
        if data.get("AbstractText"):
            results.append(f"Summary: {data['AbstractText']}")
        for t in data.get("RelatedTopics", [])[:4]:
            if isinstance(t, dict) and t.get("Text"):
                results.append(f"• {t['Text']}")

        return "\n".join(results) if results else f"No instant answer found for: {query}"
    except Exception as e:
        return f"Search error: {e}"


# ── Tool 2: Read File ───────────────────────────────────────────────────────
@tool
def read_file(path: str) -> str:
    """Read any file in the agency repo. Path is relative to repo root."""
    try:
        full = REPO_ROOT / path
        if not full.exists():
            return f"File not found: {path}"
        content = full.read_text(encoding="utf-8", errors="replace")
        if len(content) > 4000:
            content = content[:4000] + f"\n\n... (truncated, {len(content)} total chars)"
        return content
    except Exception as e:
        return f"Read error: {e}"


# ── Tool 3: Write Output ────────────────────────────────────────────────────
@tool
def write_output(filename: str, content: str) -> str:
    """Write structured output to /tmp/agency_outputs/. Returns confirmation."""
    try:
        safe = "".join(c for c in filename if c.isalnum() or c in "._-")
        if not safe:
            safe = f"output_{datetime.now().strftime('%H%M%S')}.txt"
        path = OUTPUTS_DIR / safe
        path.write_text(content, encoding="utf-8")
        return f"Written: {path} ({len(content)} chars)"
    except Exception as e:
        return f"Write error: {e}"


# ── Tool 4: Code Lint ───────────────────────────────────────────────────────
@tool
def code_lint(code: str, language: str = "python") -> str:
    """Lint a code snippet. Returns issues found or 'No issues'."""
    if language != "python":
        return f"Lint support: python only (got {language})"
    try:
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write(code)
            fname = f.name
        result = subprocess.run(
            ["ruff", "check", "--select=E,F,W", fname],
            capture_output=True, text=True, timeout=10
        )
        out = result.stdout.strip() or result.stderr.strip()
        return out if out else "No issues found."
    except FileNotFoundError:
        return "ruff not installed — pip install ruff"
    except Exception as e:
        return f"Lint error: {e}"


# ── Tool 5: Memory Recall ───────────────────────────────────────────────────
@tool
def memory_recall(topic: str) -> str:
    """Query Titans memory for past mission outcomes related to a topic."""
    try:
        import sys
        if str(REPO_ROOT) not in sys.path:
            sys.path.insert(0, str(REPO_ROOT))
        from memory.titans_memory import TitansMemory
        mem = TitansMemory()
        if not mem.ledger:
            return "No missions recorded in memory yet."
        topic_lower = topic.lower()
        matches = [
            e for e in mem.ledger
            if topic_lower in getattr(e, 'mission', str(e)).lower()
        ]
        entries = matches[:5] if matches else mem.ledger[-5:]
        lines = [f"Past missions (Titans memory — {len(mem.ledger)} total):"]
        for e in entries:
            mission = getattr(e, 'mission', '?')
            verdict = getattr(e, 'verdict', '?')
            surprise = getattr(e, 'surprise', 0)
            weight   = getattr(e, 'weight', 0)
            lines.append(f"  [{verdict}] {str(mission)[:60]} (surprise={surprise:.2f}, weight={weight:.2f})")
        return "\n".join(lines)
    except Exception as e:
        return f"Memory recall error: {e}"


# ── Tool 6: Get Current DateTime ────────────────────────────────────────────
@tool
def get_datetime(timezone: str = "UTC") -> str:
    """Return the current date and time. Timezone label only, always returns UTC."""
    return f"Current datetime: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"


# ── Tool 7: Scrape UAE Real Estate Leads ────────────────────────────────────
@tool
def scrape_ae_leads(community: str = "Springs", max_listings: int = 20) -> str:
    """
    Scrape owner-direct real estate leads from Dubizzle for a Dubai community.

    Args:
        community: Dubai community name to search (e.g. 'Springs', 'Arabian Ranches 3',
                   'Al Waha', 'Dubai Hills', 'JVC', 'Business Bay', 'Creek Harbour').
                   Default: 'Springs'.
        max_listings: Maximum number of listings to scrape (default: 20, max: 50).

    Returns:
        JSON string with leads: community, title, price, phones, is_owner, whatsapp_link,
        hot_deal flag (owner + price < AED 140k).
    """
    import re
    import time
    import random
    import json as _json

    max_listings = min(max_listings, 50)

    # Build Dubizzle URL from community name
    slug = community.lower().replace(" ", "-").replace("_", "-")
    url = f"https://dubai.dubizzle.com/en/property-for-rent/residential/villahouse/in/{slug}/"

    try:
        import urllib.request as _req
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        request = _req.Request(url, headers=headers)
        with _req.urlopen(request, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return _json.dumps({"error": f"Failed to fetch {url}: {e}", "leads": []})

    # Extract phone numbers (UAE mobile: 05X XXX XXXX)
    phone_patterns = [
        r'\+971\s*5[0-9]\s*\d{3}\s*\d{4}',
        r'971\s*5[0-9]\s*\d{3}\s*\d{4}',
        r'05[0-9][\s\-]?\d{3}[\s\-]?\d{4}',
    ]

    def normalize_phone(raw: str) -> str:
        digits = re.sub(r'\D', '', raw)
        if digits.startswith('971'):
            return digits
        if digits.startswith('0'):
            return '971' + digits[1:]
        if digits.startswith('5') and len(digits) >= 9:
            return '971' + digits
        return digits

    def extract_phones(text: str) -> list:
        found = set()
        for pat in phone_patterns:
            for m in re.findall(pat, text):
                n = normalize_phone(m)
                if len(n) == 12 and n.startswith('9715'):
                    found.add(n)
        return list(found)

    owner_keywords = ['owner', 'direct', 'no commission', 'landlord', 'private', 'مالك', 'بدون عمولة']

    def is_owner(text: str) -> bool:
        tl = text.lower()
        return any(kw in tl for kw in owner_keywords)

    # Simple HTML parsing — extract listing blocks by finding price patterns
    price_pattern = re.compile(r'([\d,]{3,})\s*AED', re.IGNORECASE)
    listing_blocks = re.split(r'(?=data-testid="listing|class="listing-card|<article)', html)

    leads = []
    seen_phones: set = set()

    for block in listing_blocks[:max_listings * 3]:
        phones = extract_phones(block)
        if not phones:
            continue
        new_phones = [p for p in phones if p not in seen_phones]
        if not new_phones:
            continue
        seen_phones.update(new_phones)

        price_match = price_pattern.search(block)
        price_str = price_match.group(0) if price_match else "N/A"
        try:
            price_num = int(price_match.group(1).replace(',', '')) if price_match else 0
        except (ValueError, AttributeError):
            price_num = 0

        owner_flag = is_owner(block)
        hot = price_num > 0 and price_num < 140_000 and owner_flag

        # Best-effort title extraction
        title_match = re.search(r'<(?:h2|h3)[^>]*>([^<]{10,80})</(?:h2|h3)>', block)
        title = title_match.group(1).strip() if title_match else "Listing"

        leads.append({
            "community": community,
            "title": title[:80],
            "price": price_str,
            "price_aed": price_num,
            "phones": ", ".join(new_phones),
            "is_owner": owner_flag,
            "whatsapp": f"https://wa.me/{new_phones[0]}",
            "hot_deal": hot,
        })

        if len(leads) >= max_listings:
            break

    summary = {
        "community": community,
        "url": url,
        "total_leads": len(leads),
        "owner_direct": sum(1 for l in leads if l["is_owner"]),
        "hot_deals": sum(1 for l in leads if l["hot_deal"]),
        "leads": leads,
    }
    return _json.dumps(summary, indent=2)


# ── Registry ─────────────────────────────────────────────────────────────────
MCP_TOOLS = [
    web_search,
    read_file,
    write_output,
    code_lint,
    memory_recall,
    get_datetime,
    scrape_ae_leads,
]

MCP_TOOL_NAMES = [t.name for t in MCP_TOOLS]


if __name__ == "__main__":
    print("MCP Tools available:")
    for t in MCP_TOOLS:
        print(f"  {t.name:20} — {t.description.split('.')[0]}")
    print(f"\nTesting memory_recall...")
    print(memory_recall.invoke({"topic": "auth"}))
    print(f"\nTesting get_datetime...")
    print(get_datetime.invoke({}))
