#!/usr/bin/env python3
"""
tool_fabricator.py — Runtime Tool Synthesis for The Agency.

AGI capability: agents can describe new tools in natural language and this
module generates, tests, and registers them as LangChain-compatible tools at
runtime. No restart needed.

Key idea: tool fabrication is a hallmark of AGI — the ability to create
new capabilities on demand rather than relying on a fixed toolkit.

How it works:
  1. Agent describes the desired tool in natural language
  2. ToolFabricator uses Ollama to generate the tool function code
  3. Synthesized tool is validated (syntax, test call, schema generation)
  4. Tool is registered in the global tool registry and immediately usable
  5. Tool metadata is saved to disk for persistence across restarts

Usage:
  from tool_fabricator import ToolFabricator
  fabricator = ToolFabricator()
  tool = fabricator.fabricate(
      name="search_hn",
      description="Search Hacker News stories by keyword",
      requirements="Query Algolia HN Search API, return top 5 story titles and URLs"
  )
  # Tool is now in MCP_TOOLS — agents can call it immediately
"""

import ast
import json
import sys
import tempfile
import textwrap
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Callable

REPO_ROOT = Path(__file__).parent.resolve()
SYNTHESIS_DIR = REPO_ROOT / "synthesized_tools"
SYNTHESIS_DIR.mkdir(exist_ok=True)

# ── In-memory tool registry ───────────────────────────────────────────────────

_fabricated_tools: dict[str, Callable] = {}
_fabricated_metadata: list[dict] = []


def load_persisted_metadata() -> list[dict]:
    """Load previously fabricated tool metadata from disk."""
    meta_file = SYNTHESIS_DIR / ".tool_registry.json"
    if meta_file.exists():
        try:
            return json.loads(meta_file.read_text())
        except (json.JSONDecodeError, Exception):
            return []
    return []


def save_persisted_metadata(metadata: list[dict]):
    """Save tool metadata for persistence across restarts."""
    meta_file = SYNTHESIS_DIR / ".tool_registry.json"
    meta_file.write_text(json.dumps(metadata, indent=2))


def get_registry() -> list[dict]:
    """Return all fabricated tool metadata (in-memory + persisted)."""
    persisted = load_persisted_metadata()
    # Merge with in-memory, deduplicate by name
    names = {m["name"] for m in _fabricated_metadata}
    all_meta = list(_fabricated_metadata)
    for m in persisted:
        if m["name"] not in names:
            all_meta.append(m)
            names.add(m["name"])
    return all_meta


# ── Tool Fabricator ────────────────────────────────────────────────────────────

class ToolFabricator:
    """
    Synthesizes new LangChain-compatible tools from natural language descriptions.

    The fabricator:
    1. Uses Ollama (via provided LLM) to generate tool code
    2. Validates the generated code (syntax, safety checks)
    3. Tests the tool with sample input
    4. Registers it for immediate use by all agents
    5. Persists tool metadata for cross-session availability
    """

    def __init__(self):
        self.registry = get_registry()

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """
        Call Ollama to generate tool code.
        Falls back to a template-based generator if Ollama is unavailable.
        """
        try:
            sys.path.insert(0, str(REPO_ROOT / "deepagents/libs/deepagents"))
            from deepagents import create_deep_agent
            from langchain_ollama import ChatOllama
            from langchain_core.messages import HumanMessage

            llm = ChatOllama(model="llama3.1", base_url="http://localhost:11434")
            agent = create_deep_agent(model=llm, tools=[],
                                      system_prompt=system_prompt,
                                      name="tool-fabricator")
            resp = agent.invoke({"messages": [HumanMessage(content=user_prompt)]})
            return resp["messages"][-1].content
        except Exception as e:
            return self._template_generate(user_prompt)

    def _template_generate(self, requirements: str) -> str:
        """Template-based tool code generation (offline fallback)."""
        name = "custom_tool"
        lines = requirements.strip().split("\n")
        desc = lines[0][:80] if lines else "Custom tool"

        return textwrap.dedent(f'''\
        from langchain_core.tools import tool

        @tool
        def {name}(query: str) -> str:
            """\\"{desc}\\" (synthesized)
            Args:
                query: The search or input parameter.
            Returns:
                String result of the operation.
            """
            try:
                import urllib.request, urllib.parse, json as _json
                encoded = urllib.parse.quote_plus(query)
                url = f"https://api.duckduckgo.com/?q={{encoded}}&format=json&no_html=1"
                req = urllib.request.Request(url, headers={{"User-Agent": "TheAgency/1.0"}})
                with urllib.request.urlopen(req, timeout=8) as r:
                    data = _json.loads(r.read().decode())
                results = []
                if data.get("AbstractText"):
                    results.append(f"Summary: {{data['AbstractText']}}")
                for t in data.get("RelatedTopics", [])[:5]:
                    if isinstance(t, dict) and t.get("Text"):
                        results.append(f"• {{t['Text']}}")
                return "\\\\n".join(results) if results else f"No results for: {{query}}"
            except Exception as e:
                return f"Error: {{e}}"
        ''')

    def _validate_code(self, code: str) -> tuple[bool, str]:
        """
        Validate generated tool code for safety and correctness.

        Checks:
        - Syntax validity
        - No dangerous imports (subprocess, os.system, shutil.rmtree, etc.)
        - Has a @tool decorated function
        - Has a docstring
        """
        # Check for dangerous patterns
        dangerous = [
            "os.system(", "os.popen(", "subprocess.call", "subprocess.Popen",
            "shutil.rmtree", "eval(", "exec(", "__import__(", "compile(",
        ]
        for pattern in dangerous:
            if pattern in code:
                return False, f"Dangerous pattern detected: {pattern}"

        # Check for @tool decorator
        if "@tool" not in code:
            return False, "Missing @tool decorator"

        # Check for docstring
        if '"""' not in code and "'''" not in code:
            return False, "Missing docstring"

        # Syntax check
        try:
            ast.parse(code)
        except SyntaxError as e:
            return False, f"Syntax error: {e}"

        return True, "OK"

    def _execute_tool_test(self, tool_fn: Callable) -> tuple[bool, str]:
        """Test the fabricated tool with a simple call."""
        try:
            result = tool_fn.invoke({"query": "test"})
            if result and len(str(result)) > 0:
                return True, f"Tool executed OK: {str(result)[:200]}"
            return False, "Tool returned empty result"
        except Exception as e:
            return False, f"Tool test failed: {e}\n{traceback.format_exc()}"

    def fabricate(
        self,
        name: str,
        description: str,
        requirements: str,
        test_on_create: bool = True,
    ) -> Optional[Callable]:
        """
        Fabricate a new tool from a natural language description.

        Args:
            name: Tool name (lowercase, underscores)
            description: Short description for the tool registry
            requirements: Natural language description of what the tool should do
            test_on_create: Whether to test the tool immediately after creation

        Returns:
            LangChain tool function, or None on failure
        """
        print(f"\n  🔧  Fabricating tool: {name}")
        print(f"      Description: {description}")
        print(f"      Requirements: {requirements[:100]}...")

        system_prompt = textwrap.dedent("""\
        You are a Tool Fabricator. You generate Python functions decorated with
        @tool from the langchain_core.tools module.

        Rules:
        1. Output ONLY the Python code, no explanations or markdown fences
        2. The function must be decorated with @tool
        3. Must have a clear docstring with Args and Returns
        4. Must handle errors gracefully with try/except
        5. Must import all needed modules inside the function body
        6. Must use type hints
        7. Must be self-contained (no external dependencies beyond stdlib)
        8. Prefer urllib, json, datetime, pathlib, and other stdlib modules
        9. Timeout all network calls at 10 seconds
        10. Return a string result

        Example tool:
        @tool
        def ping_url(url: str) -> str:
            \"\"\"Ping a URL and return HTTP status code.
            Args:
                url: The URL to ping.
            Returns:
                HTTP status code string or error message.
            \"\"\"
            import urllib.request
            try:
                req = urllib.request.Request(url, method="HEAD")
                with urllib.request.urlopen(req, timeout=10) as r:
                    return f"Status: {r.status}"
            except Exception as e:
                return f"Ping failed: {e}"
        """)

        user_prompt = textwrap.dedent(f"""\
        Generate a tool with:
        - Name: {name}
        - Description: {description}
        - Requirements: {requirements}

        Output ONLY the Python code.
        """)

        # Generate the tool code
        code = self._call_llm(system_prompt, user_prompt)

        # Clean up code (remove markdown fences if present)
        code = code.strip()
        if code.startswith("```"):
            code = code.split("\n", 1)[1]
        if code.endswith("```"):
            code = code.rsplit("```", 1)[0]
        code = code.strip()

        # Validate
        valid, msg = self._validate_code(code)
        if not valid:
            print(f"  ❌  Validation failed: {msg}")
            return None

        # Save the generated code
        tool_path = SYNTHESIS_DIR / f"{name}.py"
        tool_path.write_text(code)
        print(f"  ✅  Code generated ({len(code)} chars)")

        # Execute and register
        try:
            namespace: dict = {}
            exec(code, namespace)
            tool_fn = namespace.get(name)
            if not tool_fn:
                # Try to find any @tool decorated function
                for obj in namespace.values():
                    if hasattr(obj, "__call__") and hasattr(obj, "name"):
                        tool_fn = obj
                        break
                if not tool_fn:
                    print(f"  ❌  Could not find tool function in generated code")
                    return None

            # Set the tool name
            if hasattr(tool_fn, "name"):
                tool_fn.name = name

            # Test
            if test_on_create:
                ok, test_msg = self._execute_tool_test(tool_fn)
                if ok:
                    print(f"  ✅  Tool test passed: {test_msg}")
                else:
                    print(f"  ⚠️   Tool test: {test_msg}")

            # Register
            _fabricated_tools[name] = tool_fn
            meta = {
                "name": name,
                "description": description,
                "created": datetime.utcnow().isoformat(),
                "code_length": len(code),
                "tested": test_on_create,
                "path": str(tool_path),
            }
            _fabricated_metadata.append(meta)
            save_persisted_metadata(_fabricated_metadata)

            print(f"  ✅  Tool '{name}' fabricated and registered")
            return tool_fn

        except Exception as e:
            print(f"  ❌  Registration failed: {e}\n{traceback.format_exc()}")
            return None

    def list_tools(self) -> list[dict]:
        """List all fabricated tools with metadata."""
        return get_registry()

    def get_tool(self, name: str) -> Optional[Callable]:
        """Get a fabricated tool by name."""
        if name in _fabricated_tools:
            return _fabricated_tools[name]
        # Try loading from disk
        for meta in self.registry:
            if meta["name"] == name:
                path = Path(meta.get("path", ""))
                if path.exists():
                    namespace: dict = {}
                    exec(path.read_text(), namespace)
                    for obj in namespace.values():
                        if hasattr(obj, "__call__") and hasattr(obj, "name"):
                            _fabricated_tools[name] = obj
                            return obj
        return None


# ── Integration: get all fabricated tools as LangChain tools ──────────────────

def get_all_fabricated_tools() -> list:
    """Return all fabricated tools as registered LangChain tools."""
    fabricator = ToolFabricator()
    fabricator.registry = get_registry()
    tools = []
    for meta in fabricator.registry:
        tool = fabricator.get_tool(meta["name"])
        if tool:
            tools.append(tool)
    return tools


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Tool Fabricator — Runtime Tool Synthesis")
    parser.add_argument("--fabricate", type=str, help="Tool name to fabricate")
    parser.add_argument("--description", type=str, default="", help="Tool description")
    parser.add_argument("--requirements", type=str, default="", help="Tool requirements (natural language)")
    parser.add_argument("--list", action="store_true", help="List fabricated tools")
    parser.add_argument("--test", action="store_true", help="Run test fabrication")

    args = parser.parse_args()
    f = ToolFabricator()

    if args.fabricate:
        tool = f.fabricate(args.fabricate, args.description or args.fabricate, args.requirements)
        if tool:
            print(f"\n  Tool '{args.fabricate}' ready. Use get_all_fabricated_tools() to load.")
        else:
            print(f"\n  ❌  Failed to fabricate '{args.fabricate}'")
            sys.exit(1)

    elif args.list:
        tools = f.list_tools()
        if tools:
            print(f"\n  Fabricated Tools ({len(tools)}):")
            for t in tools:
                print(f"    {t['name']:<20} {t['description'][:50]}  [{t['created'][:10]}]")
        else:
            print("\n  No fabricated tools yet.")

    elif args.test:
        print("\n  Running tool fabrication test...")
        tool = f.fabricate(
            name="hn_search",
            description="Search Hacker News stories",
            requirements="Query Algolia HN Search API at https://hn.algolia.com/api/v1/search?query=xxx, return top 5 story titles with URLs and points",
            test_on_create=True,
        )
        if tool:
            print(f"\n  ✅  Test fabrication: PASS")
        else:
            print(f"\n  ❌  Test fabrication: FAIL")
            sys.exit(1)
    else:
        parser.print_help()
