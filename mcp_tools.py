#!/usr/bin/env python3
"""
mcp_tools.py — MCP tool layer for The Agency.

Wraps external capabilities as LangChain-compatible tools so any agent
can call them via the standard tool interface. No MCP server required —
these are local MCP-style tool definitions that follow the protocol schema.

Tools available:
  web_search              — fetch live search results (via DuckDuckGo, no key needed)
  read_file               — read any file in the repo
  write_file              — write structured output to /tmp/agency_outputs/
  summarize_url           — fetch and summarize a URL
  code_lint               — run ruff lint on a code snippet
  memory_recall           — query Titans memory for past mission insights
  trigger_moltbot_mission — fire a mission via Moltbot gateway (Telegram/Discord/Slack/Web)
  query_trust_graph       — look up entity trust score from Neo4j trust graph
  qualify_lead_nowhere    — score a B2B lead via NOWHERE.AI platform API
  analyze_dubai_market    — run Dubai/UAE market intelligence via NOWHERE.AI
  create_campaign_nowhere — generate a marketing campaign via NOWHERE.AI
  n8n_trigger             — fire an n8n workflow via webhook (automation bus)
  perplexica_search       — AI-powered search via Perplexica (replaces DuckDuckGo)
  sql_query               — natural-language SQL via SQLBot (Text-to-SQL)
  api_lookup              — discover public APIs for a topic (public-apis catalogue)
  airecon_scan            — autonomous OSINT/recon scan (airecon)
  scan_secrets            — secret scanning via TruffleHog
  web_pentest             — web app penetration test via Shannon
"""

import json
import subprocess
import tempfile
import urllib.request
import urllib.parse
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from langchain_core.tools import tool

OUTPUTS_DIR = Path("/tmp/agency_outputs")
OUTPUTS_DIR.mkdir(exist_ok=True)

REPO_ROOT = Path(__file__).parent.resolve()

# ── scrape_ae_leads constants ───────────────────────────────────────────────
# Maximum listings the scraper will return in a single call (caps user input)
MAX_SCRAPE_LISTINGS = 50
# AED price ceiling for flagging a listing as a "hot deal" (owner-direct + below market).
# 140,000 AED ≈ typical below-market threshold for Springs/Meadows 3BR units; adjust per community.
HOT_DEAL_PRICE_THRESHOLD_AED = 140_000

# ── Data tool constants ───────────────────────────────────────────────────────
# Maximum source citations returned by perplexica_search
PERPLEXICA_MAX_SOURCES  = int(os.getenv("PERPLEXICA_MAX_SOURCES", "5"))
# Maximum TruffleHog findings included in scan_secrets output (caps response size)
TRUFFLEHOG_MAX_FINDINGS = int(os.getenv("TRUFFLEHOG_MAX_FINDINGS", "20"))

# ── Cross-repo integration constants ─────────────────────────────────────────
# Moltbot gateway (sahiixx/moltworker — Cloudflare Worker)
MOLTBOT_GATEWAY_URL   = os.getenv("MOLTBOT_GATEWAY_URL",   "http://localhost:8787")
MOLTBOT_GATEWAY_TOKEN = os.getenv("MOLTBOT_GATEWAY_TOKEN", "")

# NOWHERE.AI platform (sahiixx/Fixfizx — FastAPI backend)
NOWHERE_AI_URL = os.getenv("NOWHERE_AI_URL", "http://localhost:8001")
NOWHERE_AI_JWT = os.getenv("NOWHERE_AI_JWT", "")

# Trust Graph API (sahiixx/Trust-graph- — Neo4j service)
TRUST_GRAPH_URL      = os.getenv("TRUST_GRAPH_URL",      "http://localhost:8080")
TRUST_GRAPH_API_KEY  = os.getenv("TRUST_GRAPH_API_KEY",  "")


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
        JSON string with leads containing: community, title, price, phones
        (comma-joined string), is_owner, whatsapp, and hot_deal
        (owner + price < AED 140k).
    """
    import re
    import json as _json

    if isinstance(max_listings, bool) or not isinstance(max_listings, int):
        raise TypeError("max_listings must be an integer")
    max_listings = max(0, min(max_listings, MAX_SCRAPE_LISTINGS))

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
        hot = price_num > 0 and price_num < HOT_DEAL_PRICE_THRESHOLD_AED and owner_flag

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


# ── Tool 8: Trigger Moltbot Mission ─────────────────────────────────────────
@tool
def trigger_moltbot_mission(mission: str, channel: str = "web", preset: str = "full") -> str:
    """Fire an Agency mission via the Moltbot Cloudflare gateway (sahiixx/moltworker).
    Delivers results to Telegram, Discord, Slack, or Web UI.
    Args:
        mission: The mission description to execute.
        channel: Delivery channel — 'web', 'telegram', 'discord', or 'slack'.
        preset:  Agency preset — 'full', 'saas', 'research', 'dubai', 'realestate'.
    Returns JSON with trigger status and delivery info.
    """
    import json as _json
    try:
        payload = _json.dumps({
            "mission": mission,
            "channel": channel,
            "preset":  preset,
        }).encode()
        headers = {
            "Content-Type":  "application/json",
            "Authorization": f"Bearer {MOLTBOT_GATEWAY_TOKEN}",
            "User-Agent":    "TheAgency/1.0",
        }
        req = urllib.request.Request(
            f"{MOLTBOT_GATEWAY_URL}/api/gateway/trigger",
            data=payload,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            result = _json.loads(r.read().decode())
            return _json.dumps({
                "status":   "triggered",
                "channel":  channel,
                "preset":   preset,
                "gateway":  MOLTBOT_GATEWAY_URL,
                "response": result,
            }, indent=2)
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        return _json.dumps({"error": f"HTTP {e.code}: {body[:200]}"})
    except Exception as e:
        return _json.dumps({"error": str(e), "note": "Ensure MOLTBOT_GATEWAY_URL is set and gateway is running"})


# ── Tool 9: Query Trust Graph ────────────────────────────────────────────────
@tool
def query_trust_graph(entity_id: str, include_network: bool = False) -> str:
    """Query the Neo4j trust graph (sahiixx/Trust-graph-) for an entity's trust score,
    flags, and relationship network. Used by sales, compliance, and RE agents.
    Args:
        entity_id:       Unique ID of the entity (company, person, or domain).
        include_network: If True, return 1-hop trust network details.
    Returns a trust profile with score, band (Excellent/Good/Caution/Poor/Critical), and flags.
    """
    import json as _json
    try:
        params = urllib.parse.urlencode({
            "entity_id":       entity_id,
            "include_network": str(include_network).lower(),
        })
        headers = {
            "Authorization": f"Bearer {TRUST_GRAPH_API_KEY}",
            "User-Agent":    "TheAgency/1.0",
        }
        req = urllib.request.Request(
            f"{TRUST_GRAPH_URL}/api/trust/{urllib.parse.quote(entity_id)}?{params}",
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = _json.loads(r.read().decode())
            score = data.get("trust_score", 0)
            band  = (
                "Excellent" if score >= 85 else
                "Good"      if score >= 70 else
                "Caution"   if score >= 50 else
                "Poor"      if score >= 25 else
                "Critical"
            )
            data["band"] = band
            return _json.dumps(data, indent=2)
    except Exception as e:
        return _json.dumps({
            "error":     str(e),
            "entity_id": entity_id,
            "note":      "Ensure TRUST_GRAPH_URL is set and Trust-graph- service is running",
        })


# ── Tool 10: Qualify Lead via NOWHERE.AI ─────────────────────────────────────
@tool
def qualify_lead_nowhere(
    company:          str,
    contact:          str,
    email:            str,
    budget_aed:       int  = 0,
    service_interest: str  = "",
    source:           str  = "unknown",
) -> str:
    """Score and qualify a B2B lead using the NOWHERE.AI platform (sahiixx/Fixfizx).
    Returns lead score (0-100), tier (A/B/C), and recommended next action.
    Args:
        company:          Company name.
        contact:          Primary contact full name.
        email:            Contact email address.
        budget_aed:       Estimated budget in AED (0 if unknown).
        service_interest: Primary service of interest.
        source:           Lead source (LinkedIn, referral, web, etc.).
    """
    import json as _json
    try:
        payload = _json.dumps({
            "company":          company,
            "contact":          contact,
            "email":            email,
            "budget_aed":       budget_aed,
            "service_interest": service_interest,
            "source":           source,
        }).encode()
        headers = {
            "Content-Type":  "application/json",
            "Authorization": f"Bearer {NOWHERE_AI_JWT}",
            "User-Agent":    "TheAgency/1.0",
        }
        req = urllib.request.Request(
            f"{NOWHERE_AI_URL}/api/agents/sales/qualify-lead",
            data=payload,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            return _json.dumps(_json.loads(r.read().decode()), indent=2)
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        return _json.dumps({"error": f"HTTP {e.code}: {body[:200]}"})
    except Exception as e:
        return _json.dumps({"error": str(e), "note": "Ensure NOWHERE_AI_URL and NOWHERE_AI_JWT are set"})


# ── Tool 11: Dubai Market Analysis via NOWHERE.AI ────────────────────────────
@tool
def analyze_dubai_market(sector: str, query: str, include_competitors: bool = False) -> str:
    """Run UAE/Dubai market intelligence via NOWHERE.AI platform (sahiixx/Fixfizx).
    Returns market size, growth trends, opportunities, and AED revenue projections.
    Args:
        sector:              Industry sector (e.g., 'B2B SaaS', 'Real Estate', 'FinTech').
        query:               Specific research question or analysis request.
        include_competitors: If True, include competitive landscape analysis.
    """
    import json as _json
    try:
        payload = _json.dumps({
            "sector":              sector,
            "query":               query,
            "include_competitors": include_competitors,
        }).encode()
        headers = {
            "Content-Type":  "application/json",
            "Authorization": f"Bearer {NOWHERE_AI_JWT}",
            "User-Agent":    "TheAgency/1.0",
        }
        req = urllib.request.Request(
            f"{NOWHERE_AI_URL}/api/ai/advanced/dubai-market-analysis",
            data=payload,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            return _json.dumps(_json.loads(r.read().decode()), indent=2)
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        return _json.dumps({"error": f"HTTP {e.code}: {body[:200]}"})
    except Exception as e:
        return _json.dumps({"error": str(e), "note": "Ensure NOWHERE_AI_URL and NOWHERE_AI_JWT are set"})


# ── Tool 12: Create Campaign via NOWHERE.AI ───────────────────────────────────
@tool
def create_campaign_nowhere(
    target_industry:  str,
    target_geography: str  = "Dubai",
    budget_aed:       int  = 0,
    duration_days:    int  = 30,
    channels:         str  = "LinkedIn,Google",
    language:         str  = "bilingual",
) -> str:
    """Generate a multi-channel marketing campaign via NOWHERE.AI platform (sahiixx/Fixfizx).
    Returns campaign brief, ad copy variants (EN + AR), budget allocation, and KPI targets.
    Args:
        target_industry:  Target industry vertical.
        target_geography: Geography focus (default: Dubai).
        budget_aed:       Total campaign budget in AED.
        duration_days:    Campaign duration in days.
        channels:         Comma-separated channel list (LinkedIn, Google, Meta, Email).
        language:         Content language — 'en', 'ar', or 'bilingual'.
    """
    import json as _json
    try:
        payload = _json.dumps({
            "target_industry":  target_industry,
            "target_geography": target_geography,
            "budget_aed":       budget_aed,
            "duration_days":    duration_days,
            "channels":         [c.strip() for c in channels.split(",")],
            "language":         language,
        }).encode()
        headers = {
            "Content-Type":  "application/json",
            "Authorization": f"Bearer {NOWHERE_AI_JWT}",
            "User-Agent":    "TheAgency/1.0",
        }
        req = urllib.request.Request(
            f"{NOWHERE_AI_URL}/api/agents/marketing/create-campaign",
            data=payload,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            return _json.dumps(_json.loads(r.read().decode()), indent=2)
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        return _json.dumps({"error": f"HTTP {e.code}: {body[:200]}"})
    except Exception as e:
        return _json.dumps({"error": str(e), "note": "Ensure NOWHERE_AI_URL and NOWHERE_AI_JWT are set"})


# ── Tool 13: n8n Workflow Trigger ─────────────────────────────────────────────
@tool
def n8n_trigger(workflow_tag: str, payload: str = "{}") -> str:
    """Trigger an n8n workflow via webhook. The Agency's n8n automation bus.
    Args:
        workflow_tag: Workflow name/tag — e.g. 'email', 'slack', 'crm', 'report'.
                      Maps to the n8n webhook path suffix.
        payload:      JSON string of data to send to the workflow.
    Returns JSON with trigger status and workflow response.
    Environment: N8N_BASE_URL, N8N_API_KEY, N8N_WEBHOOK_PATH (optional).
    """
    import json as _json
    N8N_BASE_URL     = os.getenv("N8N_BASE_URL",     "http://localhost:5678")
    N8N_API_KEY      = os.getenv("N8N_API_KEY",      "")
    N8N_WEBHOOK_PATH = os.getenv("N8N_WEBHOOK_PATH", "/webhook/agency")
    try:
        data = _json.loads(payload) if payload else {}
    except _json.JSONDecodeError:
        data = {"input": payload}
    data["workflow_tag"] = workflow_tag

    url  = f"{N8N_BASE_URL.rstrip('/')}{N8N_WEBHOOK_PATH}"
    body = _json.dumps(data).encode()
    headers: dict = {"Content-Type": "application/json", "User-Agent": "TheAgency/1.0"}
    if N8N_API_KEY:
        headers["X-N8N-API-KEY"] = N8N_API_KEY
    try:
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode()
        try:
            resp_data = _json.loads(raw)
            out = resp_data.get("output") or resp_data.get("result") or resp_data
        except (_json.JSONDecodeError, AttributeError):
            out = raw
        return _json.dumps({"status": "triggered", "workflow_tag": workflow_tag, "response": out}, indent=2)
    except Exception as e:
        return _json.dumps({"error": str(e), "note": f"Is n8n running at {N8N_BASE_URL}?"})


# ── Tool 14: Perplexica Search (AI-powered search) ────────────────────────────
@tool
def perplexica_search(query: str, focus: str = "webSearch") -> str:
    """AI-powered search via Perplexica (sahiixx/Perplexica).
    Provides richer, AI-synthesised results compared to DuckDuckGo.
    Args:
        query: The search query.
        focus: Search focus mode — 'webSearch', 'academicSearch', 'writingAssistant',
               'wolframAlphaSearch', 'youtubeSearch', 'redditSearch'. Default: 'webSearch'.
    Returns synthesised answer with citations.
    Environment: PERPLEXICA_URL (default: http://localhost:3001).
    """
    import json as _json
    PERPLEXICA_URL = os.getenv("PERPLEXICA_URL", "http://localhost:3001")
    payload = _json.dumps({
        "query":    query,
        "focusMode": focus,
        "optimizationMode": "balanced",
    }).encode()
    headers = {"Content-Type": "application/json", "User-Agent": "TheAgency/1.0"}
    try:
        req = urllib.request.Request(
            f"{PERPLEXICA_URL.rstrip('/')}/api/search",
            data=payload,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            data = _json.loads(r.read().decode())
        answer  = data.get("message", "")
        sources = data.get("sources", [])
        src_lines = [f"  [{i+1}] {s.get('metadata', {}).get('url', '')}" for i, s in enumerate(sources[:PERPLEXICA_MAX_SOURCES])]
        return answer + ("\n\nSources:\n" + "\n".join(src_lines) if src_lines else "")
    except Exception as e:
        # Graceful fallback to DuckDuckGo
        return web_search.invoke({"query": query})


# ── Tool 15: SQL Query via SQLBot ─────────────────────────────────────────────
@tool
def sql_query(question: str, connection_string: str = "") -> str:
    """Natural-language SQL query via SQLBot (Text-to-SQL).
    Converts plain-English questions into SQL and executes them.
    Args:
        question:          Natural language database question (e.g. 'How many users signed up last week?').
        connection_string: Database URL — SQLite, PostgreSQL, MySQL supported.
                           Defaults to SQLBOT_DB env var.
    Returns the query results as formatted text.
    Environment: SQLBOT_URL (SQLBot API, default: http://localhost:8010), SQLBOT_DB.
    """
    import json as _json
    SQLBOT_URL = os.getenv("SQLBOT_URL", "http://localhost:8010")
    db_url     = connection_string or os.getenv("SQLBOT_DB", "")
    payload = _json.dumps({"question": question, "db_url": db_url}).encode()
    headers = {"Content-Type": "application/json", "User-Agent": "TheAgency/1.0"}
    try:
        req = urllib.request.Request(
            f"{SQLBOT_URL.rstrip('/')}/query",
            data=payload,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            data = _json.loads(r.read().decode())
        sql     = data.get("sql", "")
        results = data.get("results", data.get("data", data))
        output  = f"SQL: {sql}\n\nResults:\n{_json.dumps(results, indent=2)}" if sql else _json.dumps(results, indent=2)
        return output
    except Exception as e:
        return _json.dumps({"error": str(e), "note": "Ensure SQLBOT_URL is set and SQLBot is running"})


# ── Tool 16: Public API Lookup ────────────────────────────────────────────────
@tool
def api_lookup(topic: str, category: str = "") -> str:
    """Discover public APIs for a given topic or category.
    Uses the public-apis catalogue (sahiixx/public-apis) to find free APIs.
    Args:
        topic:    What the API should do (e.g. 'weather', 'finance', 'sports').
        category: Optional category filter (e.g. 'Data', 'Finance', 'Science').
    Returns a list of matching public APIs with their descriptions and URLs.
    Environment: PUBLIC_APIS_URL (optional, default: uses GitHub raw content).
    """
    import json as _json
    PUBLIC_APIS_URL = os.getenv(
        "PUBLIC_APIS_URL",
        "https://api.publicapis.org/entries"
    )
    topic_lower = topic.lower()
    try:
        params = urllib.parse.urlencode({
            "title":    topic,
            "category": category,
        })
        url = f"{PUBLIC_APIS_URL.rstrip('/')}?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": "TheAgency/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = _json.loads(r.read().decode())
        entries = data.get("entries", [])
        if not entries:
            return f"No public APIs found for '{topic}' (category: {category or 'any'})"
        lines = [f"Public APIs matching '{topic}':"]
        for e in entries[:10]:
            lines.append(
                f"  • {e.get('API','?')} ({e.get('Category','?')}) — "
                f"{e.get('Description','')[:80]} "
                f"[{e.get('Link','')}]"
            )
        return "\n".join(lines)
    except Exception as e:
        return _json.dumps({"error": str(e), "query": topic})


# ── Tool 17: AIrecon autonomous recon scan ────────────────────────────────────
@tool
def airecon_scan(target: str, scan_type: str = "passive") -> str:
    """Run an autonomous reconnaissance scan using AIrecon (sahiixx/airecon).
    Collects OSINT, subdomain enumeration, port info, and threat intel.
    Args:
        target:    Target domain, IP, or organisation name.
        scan_type: 'passive' (OSINT only, no direct contact — default) or
                   'active' (includes direct probing — use only on authorised targets).
    Returns a recon report with findings.
    Environment: AIRECON_URL (default: http://localhost:8020).
    WARNING: Only use active scans on systems you own or have explicit authorisation to test.
    """
    import json as _json
    AIRECON_URL = os.getenv("AIRECON_URL", "http://localhost:8020")
    payload = _json.dumps({"target": target, "scan_type": scan_type}).encode()
    headers = {"Content-Type": "application/json", "User-Agent": "TheAgency/1.0"}
    try:
        req = urllib.request.Request(
            f"{AIRECON_URL.rstrip('/')}/scan",
            data=payload,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            data = _json.loads(r.read().decode())
        return _json.dumps(data, indent=2)
    except Exception as e:
        # Fallback: try invoking airecon CLI if available
        try:
            result = subprocess.run(
                ["airecon", "--target", target, "--mode", scan_type, "--output", "json"],
                capture_output=True, text=True, timeout=60
            )
            return result.stdout or result.stderr or f"airecon exited with code {result.returncode}"
        except FileNotFoundError:
            return _json.dumps({
                "error": str(e),
                "note":  "Ensure AIRECON_URL is set or airecon CLI is installed (pip install airecon)",
            })


# ── Tool 18: TruffleHog secret scan ──────────────────────────────────────────
@tool
def scan_secrets(repo_path: str, since_commit: str = "", only_verified: bool = False) -> str:
    """Scan a repository for leaked secrets using TruffleHog (sahiixx/trufflehog).
    Detects API keys, tokens, passwords, and other sensitive credentials.
    Args:
        repo_path:      Path to a local git repo (absolute) or a GitHub repo URL
                        (https://github.com/org/repo).
        since_commit:   Optional commit SHA — only scan commits after this point.
        only_verified:  If True, only return verified (live) credentials.
    Returns a JSON report of found secrets.
    WARNING: Only scan repos you own or have explicit authorisation to test.
    """
    import json as _json
    cmd = ["trufflehog"]
    if repo_path.startswith("http"):
        cmd += ["git", repo_path]
    else:
        cmd += ["filesystem", repo_path]
    cmd += ["--json", "--no-update"]
    if since_commit:
        cmd += ["--since-commit", since_commit]
    if only_verified:
        cmd += ["--only-verified"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        raw    = result.stdout.strip()
        if not raw:
            return _json.dumps({"status": "clean", "secrets_found": 0, "repo": repo_path})
        # trufflehog outputs one JSON object per line
        findings = []
        for line in raw.splitlines():
            try:
                findings.append(_json.loads(line))
            except _json.JSONDecodeError:
                pass
        return _json.dumps({
            "repo":           repo_path,
            "secrets_found":  len(findings),
            "findings":       findings[:TRUFFLEHOG_MAX_FINDINGS],
        }, indent=2)
    except FileNotFoundError:
        return _json.dumps({
            "error": "trufflehog not installed",
            "note":  "Install: https://github.com/trufflesecurity/trufflehog#installation",
        })
    except Exception as e:
        return _json.dumps({"error": str(e)})


# ── Tool 19: Shannon web pentest ──────────────────────────────────────────────
@tool
def web_pentest(target_url: str, scan_profile: str = "passive") -> str:
    """Run a web application penetration test via Shannon (sahiixx/shannon).
    Identifies OWASP Top 10 vulnerabilities, misconfigs, and exposed endpoints.
    Args:
        target_url:   Full URL of the target web application (e.g. https://example.com).
        scan_profile: 'passive' (headers/meta analysis only — default) or
                      'active' (full scan including fuzzing — authorised use only).
    Returns a pentest report with vulnerability findings and remediation advice.
    Environment: SHANNON_URL (default: http://localhost:8030).
    WARNING: Only run active scans on systems you own or have explicit written authorisation to test.
    """
    import json as _json
    SHANNON_URL = os.getenv("SHANNON_URL", "http://localhost:8030")
    payload = _json.dumps({"target": target_url, "profile": scan_profile}).encode()
    headers = {"Content-Type": "application/json", "User-Agent": "TheAgency/1.0"}
    try:
        req = urllib.request.Request(
            f"{SHANNON_URL.rstrip('/')}/scan",
            data=payload,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            data = _json.loads(r.read().decode())
        return _json.dumps(data, indent=2)
    except Exception as e:
        return _json.dumps({
            "error": str(e),
            "note":  f"Ensure SHANNON_URL is set and Shannon is running at {SHANNON_URL}",
        })


# ── Registry ─────────────────────────────────────────────────────────────────
MCP_TOOLS = [
    web_search,
    read_file,
    write_output,
    code_lint,
    memory_recall,
    get_datetime,
    scrape_ae_leads,
    trigger_moltbot_mission,
    query_trust_graph,
    qualify_lead_nowhere,
    analyze_dubai_market,
    create_campaign_nowhere,
    # Phase 6 — n8n automation bus
    n8n_trigger,
    # Phase 7 — data & knowledge layer
    perplexica_search,
    sql_query,
    api_lookup,
    # Phase 4 — security & recon
    airecon_scan,
    scan_secrets,
    web_pentest,
]

# ── Dynamic tools from MCP Registry (non-fatal) ───────────────────────────────
# Loads tools from any MCP servers registered via MCP_SERVERS env var or
# registry.json / MCP_REGISTRY_URL at import time.
try:
    from mcp_registry import load_registry_tools
    _registry_tools = load_registry_tools()
    if _registry_tools:
        MCP_TOOLS.extend(_registry_tools)
except Exception as _e:
    pass  # Registry discovery is best-effort; missing servers are non-fatal

MCP_TOOL_NAMES = [t.name for t in MCP_TOOLS]


if __name__ == "__main__":
    print("MCP Tools available:")
    for t in MCP_TOOLS:
        print(f"  {t.name:20} — {t.description.split('.')[0]}")
    print(f"\nTesting memory_recall...")
    print(memory_recall.invoke({"topic": "auth"}))
    print(f"\nTesting get_datetime...")
    print(get_datetime.invoke({}))
