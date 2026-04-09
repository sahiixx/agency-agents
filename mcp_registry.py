#!/usr/bin/env python3
"""
mcp_registry.py — MCP Server Registry for The Agency.

Discovers, registers, and dynamically loads tools from MCP-compatible servers.
Supports three discovery modes:

  1. Local registry file  — reads registry.json / registry.yaml from REPO_ROOT
  2. Remote registry      — fetches from a configured registry URL (e.g. sahiixx/registry)
  3. Environment override — MCP_SERVERS env var (comma-separated base URLs)

Each registered server is queried for its tool list via:
  GET  {server_url}/tools/list   (MCP HTTP transport)
  or
  POST {server_url}  {"method":"tools/list"}  (JSON-RPC transport)

Loaded tools are wrapped as LangChain @tool callables and added to MCP_TOOLS at
import time.

Usage:
  from mcp_registry import load_registry_tools
  extra_tools = load_registry_tools()   # returns list of LangChain tools

  # Or to get a full MCPRegistry instance:
  from mcp_registry import MCPRegistry
  registry = MCPRegistry()
  registry.discover()
  tools = registry.as_langchain_tools()

Environment variables:
  MCP_REGISTRY_URL   — URL to a remote registry JSON endpoint
                       (e.g. https://raw.githubusercontent.com/sahiixx/registry/main/registry.json)
  MCP_SERVERS        — Comma-separated list of MCP server base URLs
                       (e.g. http://localhost:8080,http://localhost:8081)
  BIFROST_URL        — Bifrost LLM gateway URL for unified observability/rate-limiting
                       (e.g. http://localhost:8000) — if set, all provider calls are proxied
  BIFROST_API_KEY    — Bifrost API key (optional)
"""

from __future__ import annotations
import json
import os
import urllib.request
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from langchain_core.tools import tool as lc_tool

REPO_ROOT = Path(__file__).parent.resolve()

MCP_REGISTRY_URL  = os.getenv("MCP_REGISTRY_URL",  "")
MCP_SERVERS_ENV   = os.getenv("MCP_SERVERS",        "")
BIFROST_URL       = os.getenv("BIFROST_URL",        "")
BIFROST_API_KEY   = os.getenv("BIFROST_API_KEY",    "")

# Local registry file (optional)
LOCAL_REGISTRY_FILE = REPO_ROOT / "registry.json"


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class MCPServer:
    """Metadata for a single registered MCP server."""
    name:        str
    url:         str
    description: str  = ""
    transport:   str  = "http"   # "http" | "jsonrpc" | "stdio"
    tags:        list = field(default_factory=list)
    tools:       list = field(default_factory=list)   # list of MCPToolDef
    reachable:   bool = False

    def __repr__(self):
        status = "✓" if self.reachable else "✗"
        return f"<MCPServer [{status}] {self.name} @ {self.url} ({len(self.tools)} tools)>"


@dataclass
class MCPToolDef:
    """Definition of a single tool exposed by an MCP server."""
    name:        str
    description: str = ""
    server_url:  str = ""
    input_schema: dict = field(default_factory=dict)


# ── Registry ──────────────────────────────────────────────────────────────────

class MCPRegistry:
    """Discovers and loads tools from all registered MCP servers."""

    def __init__(self):
        self.servers: list[MCPServer] = []

    # ── Discovery ─────────────────────────────────────────────────────────────

    def discover(self, timeout: int = 5) -> "MCPRegistry":
        """Discover servers from all configured sources."""
        self._load_local_registry()
        self._load_remote_registry()
        self._load_env_servers()
        self._probe_all(timeout=timeout)
        return self

    def _load_local_registry(self):
        if LOCAL_REGISTRY_FILE.exists():
            try:
                data = json.loads(LOCAL_REGISTRY_FILE.read_text())
                for entry in data.get("servers", []):
                    self._add_server_from_dict(entry)
            except Exception as e:
                print(f"  [mcp_registry] local registry parse error: {e}")

    def _load_remote_registry(self):
        if not MCP_REGISTRY_URL:
            return
        try:
            req = urllib.request.Request(
                MCP_REGISTRY_URL,
                headers={"User-Agent": "TheAgency/1.0"},
            )
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read().decode())
            for entry in data.get("servers", []):
                self._add_server_from_dict(entry)
        except Exception as e:
            print(f"  [mcp_registry] remote registry fetch error: {e}")

    def _load_env_servers(self):
        if not MCP_SERVERS_ENV:
            return
        for url in MCP_SERVERS_ENV.split(","):
            url = url.strip()
            if url:
                self._add_server_from_dict({"url": url, "name": url.split("//")[-1].split(":")[0]})

    def _add_server_from_dict(self, d: dict):
        url = d.get("url", "").strip()
        if not url or any(s.url == url for s in self.servers):
            return
        self.servers.append(MCPServer(
            name=d.get("name", url),
            url=url,
            description=d.get("description", ""),
            transport=d.get("transport", "http"),
            tags=d.get("tags", []),
        ))

    # ── Probe ─────────────────────────────────────────────────────────────────

    def _probe_all(self, timeout: int = 5):
        for server in self.servers:
            try:
                tools = self._fetch_tools(server, timeout=timeout)
                server.tools     = tools
                server.reachable = True
            except Exception:
                server.reachable = False

    def _fetch_tools(self, server: MCPServer, timeout: int = 5) -> list[MCPToolDef]:
        """Fetch tool list from a server via HTTP or JSON-RPC."""
        if server.transport == "jsonrpc":
            return self._fetch_tools_jsonrpc(server, timeout)
        return self._fetch_tools_http(server, timeout)

    def _fetch_tools_http(self, server: MCPServer, timeout: int) -> list[MCPToolDef]:
        url = f"{server.url.rstrip('/')}/tools/list"
        req = urllib.request.Request(url, headers={"User-Agent": "TheAgency/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode())
        return self._parse_tool_list(data, server.url)

    def _fetch_tools_jsonrpc(self, server: MCPServer, timeout: int) -> list[MCPToolDef]:
        payload = json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}
        }).encode()
        req = urllib.request.Request(
            server.url,
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "TheAgency/1.0"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode())
        result = data.get("result", data)
        return self._parse_tool_list(result, server.url)

    def _parse_tool_list(self, data: Any, server_url: str) -> list[MCPToolDef]:
        tools_raw = (
            data.get("tools") or
            data.get("result", {}).get("tools") or
            (data if isinstance(data, list) else [])
        )
        out = []
        for t in tools_raw:
            if isinstance(t, dict):
                out.append(MCPToolDef(
                    name=t.get("name", "unknown"),
                    description=t.get("description", ""),
                    server_url=server_url,
                    input_schema=t.get("inputSchema", {}),
                ))
        return out

    # ── LangChain tool wrapping ───────────────────────────────────────────────

    def as_langchain_tools(self) -> list:
        """Wrap every discovered tool as a LangChain @tool callable."""
        lc_tools = []
        for server in self.servers:
            if not server.reachable:
                continue
            for tool_def in server.tools:
                lc_tools.append(self._wrap_tool(tool_def, server))
        return lc_tools

    def _wrap_tool(self, tool_def: MCPToolDef, server: MCPServer):
        """Create a LangChain tool that calls the MCP server tool via HTTP."""
        import re
        raw_name  = f"mcp_{server.name}_{tool_def.name}"
        # Replace any non-alphanumeric/underscore character with underscore,
        # then collapse consecutive underscores and strip leading digits.
        tool_name = re.sub(r'[^a-zA-Z0-9_]', '_', raw_name)
        tool_name = re.sub(r'_+', '_', tool_name).strip('_')
        if tool_name and tool_name[0].isdigit():
            tool_name = f"mcp_{tool_name}"
        tool_desc = (
            f"[MCP:{server.name}] {tool_def.description or tool_def.name}"
        )
        server_url = server.url

        @lc_tool
        def _mcp_tool(arguments: str = "{}") -> str:
            f"""{tool_desc}
            Args:
                arguments: JSON string of tool input arguments.
            """
            return _call_mcp_tool(server_url, tool_def.name, arguments)

        # Patch name/description so LangChain surfaces them correctly
        _mcp_tool.name        = tool_name
        _mcp_tool.description = tool_desc
        return _mcp_tool

    # ── Summary ───────────────────────────────────────────────────────────────

    def summary(self) -> str:
        total_tools = sum(len(s.tools) for s in self.servers if s.reachable)
        reachable   = sum(1 for s in self.servers if s.reachable)
        return (
            f"{reachable}/{len(self.servers)} servers reachable, "
            f"{total_tools} tools discovered"
        )


# ── Low-level HTTP call ───────────────────────────────────────────────────────

def _call_mcp_tool(server_url: str, tool_name: str, arguments_json: str) -> str:
    """Call a specific tool on an MCP server."""
    try:
        args = json.loads(arguments_json) if arguments_json else {}
    except json.JSONDecodeError:
        args = {"input": arguments_json}

    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": args},
    }).encode()

    try:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "TheAgency/1.0",
        }
        headers.update(get_bifrost_headers())
        req = urllib.request.Request(
            server_url,
            data=payload,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            resp = json.loads(r.read().decode())
        result = resp.get("result", resp)
        if isinstance(result, dict):
            content = result.get("content", result)
            if isinstance(content, list):
                return "\n".join(
                    c.get("text", json.dumps(c)) for c in content if isinstance(c, dict)
                )
            return json.dumps(content, indent=2)
        return str(result)
    except Exception as e:
        return f"MCP tool call error ({tool_name}@{server_url}): {e}"


# ── Bifrost gateway wrapper ───────────────────────────────────────────────────

def get_bifrost_headers() -> dict:
    """Return HTTP headers for routing through the Bifrost LLM gateway."""
    if not BIFROST_URL:
        return {}
    headers = {"X-Bifrost-Gateway": BIFROST_URL}
    if BIFROST_API_KEY:
        headers["X-Bifrost-API-Key"] = BIFROST_API_KEY
    return headers


def bifrost_base_url() -> Optional[str]:
    """Return the Bifrost proxy base URL, or None if not configured."""
    return BIFROST_URL.rstrip("/") if BIFROST_URL else None


# ── Public API ────────────────────────────────────────────────────────────────

_registry_singleton: Optional[MCPRegistry] = None


def load_registry_tools(force_reload: bool = False) -> list:
    """
    Discover and return all MCP registry tools as LangChain callables.
    Results are cached after the first call unless force_reload=True.
    """
    global _registry_singleton
    if _registry_singleton is None or force_reload:
        _registry_singleton = MCPRegistry()
        _registry_singleton.discover()
        if _registry_singleton.servers:
            print(f"  [mcp_registry] {_registry_singleton.summary()}")
    return _registry_singleton.as_langchain_tools()


if __name__ == "__main__":
    print("MCP Registry — discovering servers…")
    reg = MCPRegistry().discover()
    print(f"  {reg.summary()}")
    for s in reg.servers:
        print(f"  {s}")
        for t in s.tools:
            print(f"    • {t.name}: {t.description[:60]}")

    if BIFROST_URL:
        print(f"\n  Bifrost gateway: {BIFROST_URL}")
    else:
        print("\n  Bifrost: not configured (set BIFROST_URL to enable)")
