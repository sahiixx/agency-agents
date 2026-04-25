"""Bridge that connects agency-agents swarm to sahiixx-bus SwarmBus and A2ARouter.

This module creates a two-way integration:
  * Publishes missions and results to the shared SwarmBus so that
    sovereign-swarm and other ecosystem services can observe/route.
  * Re-uses A2ARouter for capability-based task routing instead of
    inline hard-coded orchestrator logic.

Usage:
    from orchestration_bridge import (
        publish_mission,
        subscribe_to_results,
        route_via_meta_orchestrator,
        register_agency_services,
    )

    mission_id = await publish_mission("Build API", "full", ["pm", "backend", "core"])
    sub_id = await subscribe_to_results(mission_id, my_handler)
    result = await route_via_meta_orchestrator("Plan sprint", ["planning", "pm"])
    await register_agency_services({"pm": 8100, "backend": 8101})
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any, Awaitable, Callable

# Ensure sahiixx-bus is on the path (sibling package in the SAHIIXX ecosystem)
_REPO_ROOT = Path(__file__).parent.resolve()
_ECO_ROOT = _REPO_ROOT.parent
_BUS_PKG = _ECO_ROOT / "sahiixx-bus"
for _p in (str(_BUS_PKG), str(_REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from sahiixx_bus import SwarmBus, A2ARouter, SafetyCouncil, AgencyBridge
except ImportError as _imp_err:
    raise ImportError(
        "sahiixx-bus is required for the orchestration bridge. "
        "Install it first:  pip install -e ../sahiixx-bus"
    ) from _imp_err


# ── Shared singleton instances ────────────────────────────────────────────────

_bus = SwarmBus(namespace="agency-agents")
_safety = SafetyCouncil()
_router = A2ARouter(_bus, _safety)

# Keep a local cache of mission subscriptions so we can unsubscribe later
_mission_subscriptions: dict[str, str] = {}


# ── Public API ─────────────────────────────────────────────────────────────

async def publish_mission(mission_goal: str, preset: str, agent_names: list) -> str:
    """Post a mission to SwarmBus so sovereign-swarm can observe/route.

    The mission is published on the ``missions.new`` channel with a
    generated mission ID.  Any downstream subscriber (e.g. sovereign-swarm
    StateManager, dashboard, or audit logger) can react to it.

    Args:
        mission_goal: Human-readable mission description.
        preset:       Preset name (e.g. "full", "saas", "dubai").
        agent_names:  List of agent keys that will participate.

    Returns:
        The generated mission ID (UUIDv4).
    """
    import uuid
    from datetime import datetime, timezone

    mission_id = str(uuid.uuid4())
    payload = {
        "mission_id": mission_id,
        "goal": mission_goal,
        "preset": preset,
        "agents": list(agent_names),
        "source": "agency-agents",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "submitted",
    }
    await _bus.publish("missions.new", payload)
    return mission_id


async def subscribe_to_results(
    mission_id: str,
    handler: Callable[[dict], Awaitable[None]],
) -> str:
    """Subscribe to agent results flowing back via SwarmBus.

    Each result message is expected on ``missions.{mission_id}.results``.
    The handler receives the full message dict.

    Args:
        mission_id: Mission ID returned by ``publish_mission``.
        handler:    Async callable that processes each result dict.

    Returns:
        Subscription ID that can be used to unsubscribe later.
    """
    channel = f"missions.{mission_id}.results"
    sub_id = await _bus.subscribe(channel, handler)
    _mission_subscriptions[mission_id] = sub_id
    return sub_id


async def unsubscribe_results(mission_id: str) -> bool:
    """Unsubscribe a previously registered result handler.

    Args:
        mission_id: Mission ID used when subscribing.

    Returns:
        True if a subscription was found and removed.
    """
    sub_id = _mission_subscriptions.pop(mission_id, None)
    if sub_id:
        await _bus.unsubscribe(sub_id)
        return True
    return False


async def route_via_meta_orchestrator(task: str, capabilities: list | None = None) -> dict:
    """Route task selection through A2ARouter instead of inline logic.

    This delegates the heavy lifting of scoring services by capability
    overlap and fallback-chain traversal to the shared A2ARouter.

    Args:
        task:           Plain-text task description.
        capabilities:   List of required capability strings.  If None the
                        router skips capability scoring and falls back to
                        the first available service.

    Returns:
        Routing result dict with keys: ``routed`` (bool), ``service`` (str),
        ``result`` (Any), and possibly ``error`` / ``violations``.
    """
    return await _router.route_task(task, required_capabilities=capabilities or [])


async def register_agency_services(port_map: dict[str, int]) -> None:
    """Register all agency A2A servers with the unified router.

    For every entry in *port_map* an ``AgencyBridge`` endpoint is
    registered so that cross-framework routing (e.g. sovereign-swarm →
    agency-agents) works transparently.

    Args:
        port_map: Mapping ``agent_name → port`` as produced by
                  ``a2a_protocol.start_agency_a2a_servers``.
    """
    for agent_name, port in port_map.items():
        url = f"http://localhost:{port}"
        capabilities = [agent_name, "a2a", "agency"]
        await _router.register_service(
            name=f"agency-{agent_name}",
            url=url,
            capabilities=capabilities,
        )
        # Also publish a discovery event on the bus
        await _bus.publish(
            "services.discovered",
            {
                "service": f"agency-{agent_name}",
                "url": url,
                "capabilities": capabilities,
            },
        )

    # Register the umbrella "agency-agents" service as well (used by fallback chain)
    if port_map:
        first_port = list(port_map.values())[0]
        await _router.register_service(
            name="agency-agents",
            url=f"http://localhost:{first_port}",
            capabilities=list(port_map.keys()) + ["a2a", "agency"],
        )


async def publish_result(mission_id: str, agent_name: str, result_text: str, verdict: str = "PENDING") -> None:
    """Publish an intermediate or final result back to the bus.

    Downstream subscribers (dashboard, memory, audit) can consume these
    events in real time.

    Args:
        mission_id:  Mission identifier.
        agent_name:  Name of the agent that produced the result.
        result_text: The result payload (truncated if very large).
        verdict:     Mission verdict so far (GO / CONDITIONAL GO / NO-GO / PENDING).
    """
    from datetime import datetime, timezone

    channel = f"missions.{mission_id}.results"
    payload = {
        "mission_id": mission_id,
        "agent": agent_name,
        "result": result_text[:8000],  # cap at 8 kB to keep bus messages lean
        "verdict": verdict,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await _bus.publish(channel, payload)


async def publish_verdict(mission_id: str, verdict: str, final_output: str = "") -> None:
    """Publish the final mission verdict and output to the bus.

    This is a convenience wrapper around ``publish_result`` that also
    emits a ``missions.completed`` event for downstream workflow triggers.

    Args:
        mission_id:   Mission identifier.
        verdict:      Final verdict string (GO / CONDITIONAL GO / NO-GO).
        final_output: The complete final deliverable (truncated at 8 kB).
    """
    await publish_result(mission_id, "core", final_output, verdict)
    from datetime import datetime, timezone

    await _bus.publish(
        "missions.completed",
        {
            "mission_id": mission_id,
            "verdict": verdict,
            "output": final_output[:8000],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


# ── Bridge helpers for agency.py integration ────────────────────────────────

def get_bus() -> SwarmBus:
    """Return the shared SwarmBus singleton (for advanced integrations)."""
    return _bus


def get_router() -> A2ARouter:
    """Return the shared A2ARouter singleton (for advanced integrations)."""
    return _router


# ── Self-test ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    async def _self_test() -> None:
        print("Orchestration Bridge self-test...")

        # 1. Publish a mission
        mid = await publish_mission("Test mission", "research", ["pm", "ai", "core"])
        print(f"  [OK] published mission: {mid}")

        # 2. Subscribe to results
        received: list[dict] = []

        async def _handler(msg: dict) -> None:
            received.append(msg)

        sub_id = await subscribe_to_results(mid, _handler)
        print(f"  [OK] subscribed to results: {sub_id}")

        # 3. Publish a result and verify it arrives
        await publish_result(mid, "pm", "Project plan drafted", "PENDING")
        await asyncio.sleep(0.2)  # let the bus deliver
        assert len(received) == 1
        assert received[0]["agent"] == "pm"
        print(f"  [OK] result received: {received[0]['result']}")

        # 4. Publish verdict
        await publish_verdict(mid, "GO", "All phases complete.")
        await asyncio.sleep(0.2)
        assert len(received) == 2
        print(f"  [OK] verdict published: {received[1]['verdict']}")

        # 5. Unsubscribe
        ok = await unsubscribe_results(mid)
        assert ok is True
        print("  [OK] unsubscribed")

        # 6. Register agency services
        await register_agency_services({"pm": 8100, "backend": 8101})
        assert "agency-pm" in _router._registry
        assert "agency-backend" in _router._registry
        print("  [OK] services registered with router")

        # 7. Fallback chain inspection
        assert "agency-agents" in _router._registry
        assert "agency-agents" in _router.get_fallback_chain()
        print("  [OK] fallback chain includes agency-agents")

        print("\nOrchestration Bridge self-test PASSED")

    asyncio.run(_self_test())
