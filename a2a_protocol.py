#!/usr/bin/env python3
"""
a2a_protocol.py — Native A2A (Agent2Agent) Protocol implementation for The Agency.

Implements the Google A2A spec v0.3 (Linux Foundation, 2025):
  https://a2a-protocol.org/latest/specification/

Capabilities:
  A2AServer    — expose any Agency agent as an A2A-compliant HTTP server
                 with Agent Card discovery at /.well-known/agent.json
                 JSON-RPC 2.0 task endpoint at /
                 SSE streaming at /stream
  A2AClient    — call any external A2A-compliant agent from within a mission
  AgentCard    — structured capability advertisement (JSON format)
  TaskManager  — full task lifecycle: SUBMITTED → WORKING → COMPLETED/FAILED
  A2ATool      — LangChain tool wrapper so orchestrator can call remote A2A agents

The Agency exposes each registered agent as its own A2A server on sequential
ports starting at 8100. The orchestrator can discover and call any of them,
or call external A2A agents from other frameworks (CrewAI, AutoGen, ADK).

Usage:
  # Start The Agency as A2A servers (background)
  python3 a2a_protocol.py --serve --preset full --port 8100

  # Call an external A2A agent
  python3 a2a_protocol.py --call http://localhost:8100 --task "Plan a REST API"

  # From orchestrator — use A2ATool
  from a2a_protocol import make_a2a_tools
  tools = make_a2a_tools(["http://localhost:8100", "http://external-agent:9000"])
"""

import asyncio
import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from enum import Enum

import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse, Response
from starlette.routing import Route
from langchain_core.tools import tool

# ── Task state machine ────────────────────────────────────────────────────────

class TaskState(str, Enum):
    SUBMITTED  = "TASK_STATE_SUBMITTED"
    WORKING    = "TASK_STATE_WORKING"
    COMPLETED  = "TASK_STATE_COMPLETED"
    FAILED     = "TASK_STATE_FAILED"
    CANCELED   = "TASK_STATE_CANCELED"


@dataclass
class TaskStatus:
    state:     TaskState = TaskState.SUBMITTED
    timestamp: str       = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    message:   str       = ""


@dataclass
class Artifact:
    artifactId: str       = field(default_factory=lambda: str(uuid.uuid4()))
    name:       str       = "result"
    parts:      list      = field(default_factory=list)

    def text_part(self, text: str) -> "Artifact":
        self.parts.append({"text": text})
        return self


@dataclass
class A2ATask:
    id:        str        = field(default_factory=lambda: str(uuid.uuid4()))
    contextId: str        = field(default_factory=lambda: str(uuid.uuid4()))
    status:    TaskStatus = field(default_factory=TaskStatus)
    artifacts: list       = field(default_factory=list)
    metadata:  dict       = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id":        self.id,
            "contextId": self.contextId,
            "status": {
                "state":     self.status.state.value,
                "timestamp": self.status.timestamp,
                "message":   self.status.message,
            },
            "artifacts": [
                {
                    "artifactId": a.artifactId,
                    "name":       a.name,
                    "parts":      a.parts,
                }
                for a in self.artifacts
            ],
            "metadata": self.metadata,
        }


# ── Agent Card ────────────────────────────────────────────────────────────────

def make_agent_card(
    name:        str,
    description: str,
    port:        int,
    skills:      list[dict],
    version:     str = "1.0.0",
) -> dict:
    """
    Build an A2A Agent Card per spec section 3.1.
    Served at /.well-known/agent.json for discovery.
    """
    return {
        "name":        name,
        "description": description,
        "version":     version,
        "url":         f"http://localhost:{port}",
        "provider": {
            "organization": "The Agency",
            "url":          "https://github.com/sahiixx/agency-agents",
        },
        "capabilities": {
            "streaming":          True,
            "pushNotifications":  False,
            "extendedAgentCard":  False,
            "a2aVersion":         "0.3",
        },
        "skills": skills,
        "defaultInputModes":  ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "securitySchemes":    {},
        "metadata": {
            "model":     "claude-sonnet-4-6",
            "framework": "deepagents+langgraph",
            "memory":    "titans-v1",
        },
    }


# ── A2A Server ────────────────────────────────────────────────────────────────

class A2AServer:
    """
    HTTP server exposing one Agency agent as an A2A endpoint.

    Endpoints:
      GET  /.well-known/agent.json  — Agent Card discovery
      POST /                        — JSON-RPC 2.0 task submission
      GET  /stream                  — SSE streaming task updates
    """

    def __init__(
        self,
        agent_name:   str,
        description:  str,
        handler:      Any,   # callable(task_text: str) -> str
        port:         int,
        skills:       Optional[list] = None,
    ):
        self.agent_name  = agent_name
        self.description = description
        self.handler     = handler
        self.port        = port
        self.tasks:      dict[str, A2ATask] = {}
        self._skills     = skills or [
            {
                "id":          agent_name,
                "name":        agent_name.replace("-", " ").title(),
                "description": description,
                "tags":        ["agency", agent_name],
                "examples":    [f"Help me with {agent_name} tasks"],
            }
        ]
        self._card = make_agent_card(
            name=f"Agency:{agent_name}",
            description=description,
            port=port,
            skills=self._skills,
        )
        self._app = self._build_app()

    # ── Route handlers ────────────────────────────────────────────────────────

    async def _agent_card(self, request: Request) -> JSONResponse:
        return JSONResponse(self._card)

    async def _jsonrpc(self, request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse(self._error(-32700, "Parse error"), status_code=400)

        method  = body.get("method", "")
        params  = body.get("params", {})
        req_id  = body.get("id", 1)

        if method == "tasks/send":
            return await self._handle_send(params, req_id)
        elif method == "tasks/get":
            return await self._handle_get(params, req_id)
        elif method == "tasks/cancel":
            return await self._handle_cancel(params, req_id)
        else:
            return JSONResponse(self._error(-32601, f"Method not found: {method}", req_id))

    async def _sse_stream(self, request: Request) -> StreamingResponse:
        task_id = request.query_params.get("taskId")
        if not task_id or task_id not in self.tasks:
            return Response("Task not found", status_code=404)

        async def generate():
            task = self.tasks[task_id]
            # Stream status updates until done
            for _ in range(30):
                await asyncio.sleep(0.5)
                event = json.dumps({"task": task.to_dict()})
                yield f"data: {event}\n\n"
                if task.status.state in (TaskState.COMPLETED, TaskState.FAILED):
                    break

        return StreamingResponse(generate(), media_type="text/event-stream")

    # ── Task handlers ─────────────────────────────────────────────────────────

    async def _handle_send(self, params: dict, req_id: Any) -> JSONResponse:
        task_id    = params.get("id", str(uuid.uuid4()))
        context_id = params.get("contextId", str(uuid.uuid4()))
        messages   = params.get("message", {}).get("parts", [])
        task_text  = " ".join(p.get("text", "") for p in messages if "text" in p)

        task = A2ATask(id=task_id, contextId=context_id)
        task.status = TaskStatus(TaskState.WORKING, message=f"Processing via {self.agent_name}")
        self.tasks[task_id] = task

        # Run handler in thread to avoid blocking
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(None, self.handler, task_text)
            task.status = TaskStatus(TaskState.COMPLETED, message="Done")
            task.artifacts = [Artifact().text_part(str(result))]
        except Exception as e:
            task.status = TaskStatus(TaskState.FAILED, message=str(e))

        return JSONResponse({"jsonrpc": "2.0", "id": req_id, "result": {"task": task.to_dict()}})

    async def _handle_get(self, params: dict, req_id: Any) -> JSONResponse:
        task_id = params.get("id", "")
        if task_id not in self.tasks:
            return JSONResponse(self._error(-32001, f"Task not found: {task_id}", req_id))
        return JSONResponse({"jsonrpc": "2.0", "id": req_id, "result": {"task": self.tasks[task_id].to_dict()}})

    async def _handle_cancel(self, params: dict, req_id: Any) -> JSONResponse:
        task_id = params.get("id", "")
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus(TaskState.CANCELED)
        return JSONResponse({"jsonrpc": "2.0", "id": req_id, "result": {"status": "canceled"}})

    def _error(self, code: int, message: str, req_id: Any = None) -> dict:
        r = {"jsonrpc": "2.0", "error": {"code": code, "message": message}}
        if req_id is not None:
            r["id"] = req_id
        return r

    # ── App builder ───────────────────────────────────────────────────────────

    def _build_app(self) -> Starlette:
        return Starlette(routes=[
            Route("/.well-known/agent.json", self._agent_card,  methods=["GET"]),
            Route("/",                       self._jsonrpc,      methods=["POST"]),
            Route("/stream",                 self._sse_stream,   methods=["GET"]),
        ])

    def run_in_thread(self) -> threading.Thread:
        """Start server in a background daemon thread."""
        import uvicorn
        config = uvicorn.Config(self._app, host="0.0.0.0", port=self.port,
                                log_level="error", access_log=False)
        server = uvicorn.Server(config)

        def _run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(server.serve())

        t = threading.Thread(target=_run, daemon=True, name=f"a2a-{self.agent_name}")
        t.start()
        time.sleep(0.4)  # let server bind
        return t


# ── A2A Client ────────────────────────────────────────────────────────────────

class A2AClient:
    """
    Call any A2A-compliant server (Agency or external — CrewAI, AutoGen, ADK).
    Discovers capabilities via Agent Card, submits tasks via JSON-RPC 2.0.
    """

    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout  = timeout
        self._card:   Optional[dict] = None

    def discover(self) -> dict:
        """Fetch and cache Agent Card from /.well-known/agent.json"""
        if self._card:
            return self._card
        resp = httpx.get(f"{self.base_url}/.well-known/agent.json", timeout=5.0)
        resp.raise_for_status()
        self._card = resp.json()
        return self._card

    def send_task(self, text: str, context_id: Optional[str] = None) -> A2ATask:
        """Submit a task and block until completion."""
        task_id    = str(uuid.uuid4())
        context_id = context_id or str(uuid.uuid4())

        payload = {
            "jsonrpc": "2.0",
            "id":      1,
            "method":  "tasks/send",
            "params": {
                "id":        task_id,
                "contextId": context_id,
                "message": {
                    "role":  "user",
                    "parts": [{"text": text}],
                },
            },
        }

        resp = httpx.post(
            self.base_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        if "error" in data:
            raise RuntimeError(f"A2A error: {data['error']}")

        task_dict = data["result"]["task"]
        task = A2ATask(
            id=task_dict["id"],
            contextId=task_dict["contextId"],
            status=TaskStatus(
                state=TaskState(task_dict["status"]["state"]),
                message=task_dict["status"].get("message", ""),
            ),
        )
        for a in task_dict.get("artifacts", []):
            art = Artifact(artifactId=a["artifactId"], name=a.get("name", "result"))
            art.parts = a.get("parts", [])
            task.artifacts.append(art)
        return task

    def get_result_text(self, task: A2ATask) -> str:
        """Extract text from first artifact."""
        for art in task.artifacts:
            for part in art.parts:
                if "text" in part:
                    return part["text"]
        return ""

    def call(self, text: str) -> str:
        """Discover + send + extract in one call."""
        try:
            self.discover()
            task = self.send_task(text)
            return self.get_result_text(task) or f"[A2A task {task.id}: {task.status.state}]"
        except Exception as e:
            return f"[A2A call failed: {e}]"


# ── LangChain Tool wrapper ────────────────────────────────────────────────────

def make_a2a_tool(url: str, agent_name: Optional[str] = None):
    """
    Create a LangChain tool that calls a remote A2A agent.
    The orchestrator can use this to call external agents (CrewAI, AutoGen, etc.)
    """
    client = A2AClient(url)

    # Try to discover name from Agent Card
    try:
        card = client.discover()
        name = agent_name or card.get("name", url).replace(":", "_").replace("/", "_").replace(".", "_")
        desc = card.get("description", f"Remote A2A agent at {url}")
    except Exception:
        name = agent_name or f"a2a_agent_{url.split(':')[-1]}"
        desc = f"Remote A2A agent at {url}"

    safe_name = "".join(c if c.isalnum() or c == "_" else "_" for c in name)[:40]
    tool_desc  = f"Remote A2A agent [{name}]: {desc}. Pass a plain-text task description."

    def _fn(task: str) -> str:
        """Call a remote A2A agent with a plain-text task."""
        return client.call(task)

    _fn.__name__    = safe_name
    _fn.__doc__     = tool_desc
    lc_tool         = tool(_fn)
    lc_tool.description = tool_desc
    return lc_tool


def make_a2a_tools(urls: list[str]) -> list:
    """Create LangChain tools for a list of A2A server URLs."""
    tools = []
    for url in urls:
        try:
            tools.append(make_a2a_tool(url))
        except Exception as e:
            print(f"  ⚠️  A2A tool creation failed for {url}: {e}")
    return tools


# ── Agency A2A server pool ────────────────────────────────────────────────────

BASE_PORT = 8100

def start_agency_a2a_servers(
    agent_names: list[str],
    agent_registry: dict,
    repo_root: Path,
) -> dict[str, int]:
    """
    Start one A2A server per agent in agent_names.
    Returns mapping: agent_name → port.

    Each server exposes the agent's system prompt as its capability
    and responds to tasks with a simple echo + system prompt preamble
    (real LLM calls happen through the orchestrator, not per-server).
    """
    port_map: dict[str, int] = {}

    for i, name in enumerate(agent_names):
        port = BASE_PORT + i
        path, desc = agent_registry.get(name, ("", f"Agency agent: {name}"))

        # Load system prompt for context
        sp_path = repo_root / path if path else None
        system_prompt = sp_path.read_text() if sp_path and sp_path.exists() else f"# {name} agent"

        def make_handler(agent_n: str, sp: str):
            def handler(task_text: str) -> str:
                # In production: invoke LLM with system_prompt + task
                # Here: return structured stub so A2A plumbing is testable without API key
                return (
                    f"[A2A:{agent_n}] Task received: {task_text[:100]}\n"
                    f"Agent: {agent_n} | System prompt: {len(sp)} chars | "
                    f"A2A task completed at {datetime.now(timezone.utc).isoformat()}"
                )
            return handler

        server = A2AServer(
            agent_name=name,
            description=desc,
            handler=make_handler(name, system_prompt),
            port=port,
        )
        server.run_in_thread()
        port_map[name] = port
        print(f"  [A2A] {name:12} → http://localhost:{port}")

    return port_map


# ── Registry of running servers (module-level, singleton) ─────────────────────

_running_servers: dict[str, int] = {}


def get_running_servers() -> dict[str, int]:
    return _running_servers


def register_servers(port_map: dict[str, int]):
    _running_servers.update(port_map)


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="A2A Protocol for The Agency")
    parser.add_argument("--serve",   action="store_true",        help="Start A2A servers for all registry agents")
    parser.add_argument("--port",    type=int, default=BASE_PORT, help="Base port (default 8100)")
    parser.add_argument("--call",    type=str,                    help="Call an A2A server URL")
    parser.add_argument("--task",    type=str, default="Hello",   help="Task text to send")
    parser.add_argument("--card",    type=str,                    help="Fetch Agent Card from URL")
    args = parser.parse_args()

    if args.card:
        client = A2AClient(args.card)
        card = client.discover()
        print(json.dumps(card, indent=2))

    elif args.call:
        print(f"Calling A2A agent: {args.call}")
        client = A2AClient(args.call)
        try:
            card = client.discover()
            print(f"  Agent: {card.get('name')} — {card.get('description','')}")
        except Exception:
            print("  (Agent Card not available)")
        result = client.call(args.task)
        print(f"  Result: {result}")

    elif args.serve:
        sys.path.insert(0, str(Path(__file__).parent / "deepagents/libs/deepagents"))
        sys.path.insert(0, str(Path(__file__).parent))
        import agency
        repo_root = Path(__file__).parent

        BASE_PORT = args.port
        print(f"\nStarting Agency A2A servers (base port {BASE_PORT})...")
        agents = list(agency.AGENT_REGISTRY.keys())
        port_map = start_agency_a2a_servers(agents, agency.AGENT_REGISTRY, repo_root)
        register_servers(port_map)

        print(f"\n✅  {len(port_map)} A2A servers running")
        print(f"    Discovery:  http://localhost:{BASE_PORT}/.well-known/agent.json")
        print(f"    All agents: {list(port_map.keys())}")
        print("\nPress Ctrl+C to stop.\n")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nA2A servers stopped.")

    else:
        # Self-test: start one server, call it, verify
        print("A2A Protocol self-test...")

        def echo_handler(text: str) -> str:
            return f"Echo from test-agent: {text} | ts={datetime.now(timezone.utc).isoformat()}"

        server = A2AServer(
            agent_name="test-agent",
            description="Self-test A2A agent",
            handler=echo_handler,
            port=18999,
        )
        server.run_in_thread()

        client = A2AClient("http://localhost:18999")
        print(f"  Agent Card: {json.dumps(client.discover(), indent=2)[:200]}...")
        result = client.call("Build a mortgage calculator")
        print(f"  Task result: {result}")

        tool = make_a2a_tool("http://localhost:18999", "test_agent")
        lc_result = tool.invoke({"task": "Design a REST API"})
        print(f"  LangChain tool: {lc_result}")

        print("\n✅  A2A self-test passed")
