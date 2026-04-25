"""Safety proxy that gates agency-agents operations through sovereign-swarm's SafetyCouncil and RBACGuard.

This module acts as a transparent security layer for The Agency.  Every mission
goal is scanned for dangerous patterns, sensitive operations (kill, emergency
arm) are gated through role-based access control, and per-mission LLM costs
are tracked via the shared BudgetController.

Usage:
    from safety_proxy import safety_scan_input, gate_kill, track_mission_cost

    ok = await safety_scan_input("Build a REST API", identity="orchestrator")
    allowed = await gate_kill(identity="admin")
    await track_mission_cost("mission-123", estimated_cost=0.50, actual_cost=0.42)
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Ensure sahiixx-bus is on the path (sibling package in the SAHIIXX ecosystem)
_REPO_ROOT = Path(__file__).parent.resolve()
_ECO_ROOT = _REPO_ROOT.parent
_BUS_PKG = _ECO_ROOT / "sahiixx-bus"
for _p in (str(_BUS_PKG), str(_REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from sahiixx_bus import SafetyCouncil, RBACGuard, Permission, BudgetController
except ImportError as _imp_err:
    raise ImportError(
        "sahiixx-bus is required for the safety proxy. "
        "Install it first:  pip install -e ../sahiixx-bus"
    ) from _imp_err


# ── Shared singleton instances ────────────────────────────────────────────────

_safety = SafetyCouncil(strict_mode=True)
_rbac = RBACGuard()
_budget = BudgetController()

# Pre-configure roles ---------------------------------------------------------
_rbac.add_role(
    "orchestrator",
    {Permission.EXECUTE, Permission.AGENT_SPAWN, Permission.TOOL_USE, Permission.READ, Permission.WRITE},
)
_rbac.add_role(
    "agent",
    {Permission.EXECUTE, Permission.TOOL_USE, Permission.READ},
)
_rbac.add_role(
    "auditor",
    {Permission.READ, Permission.KILL},
)
_rbac.add_role(
    "admin",
    set(Permission),
)

# Default identity assignments (anyone not explicitly assigned gets "agent")
# These can be overridden at runtime by calling _rbac.assign_role(identity, role)


# ── Custom exceptions ───────────────────────────────────────────────────────

class SafetyError(RuntimeError):
    """Raised when SafetyCouncil.scan() finds a threat in strict mode."""
    pass


class RBACError(PermissionError):
    """Raised when an identity lacks a required permission."""
    pass


# ── Public API ─────────────────────────────────────────────────────────────

async def safety_scan_input(user_input: str, identity: str = "anonymous") -> dict:
    """Scan user input through SafetyCouncil.  Blocks prohibited patterns.

    Args:
        user_input: The raw mission goal or user query.
        identity:   Identity string for audit logging (default: anonymous).

    Returns:
        A dict with keys: ``safe`` (bool), ``threat_level`` (str),
        ``violations`` (list), ``sanitized`` (str), ``recommendation`` (str).

    Raises:
        SafetyError: If the input is not safe and strict_mode is enabled.
    """
    verdict = await _safety.scan(user_input, context=f"identity={identity}")

    result = {
        "safe": verdict.safe,
        "threat_level": verdict.threat_level,
        "violations": list(verdict.violations),
        "sanitized": verdict.sanitized,
        "recommendation": verdict.recommendation,
    }

    if not verdict.safe:
        raise SafetyError(
            f"Safety scan BLOCKED input from '{identity}'. "
            f"Threat level: {verdict.threat_level}. "
            f"Violations: {verdict.violations}. "
            f"Recommendation: {verdict.recommendation}"
        )

    return result


async def gate_kill(identity: str) -> bool:
    """Gate kill / shutdown operations through RBACGuard.

    Only identities with ``Permission.KILL`` (auditor or admin) may proceed.

    Args:
        identity: The identity requesting the kill operation.

    Returns:
        True if permitted, False otherwise (never raises).
    """
    permitted = _rbac.check(identity, Permission.KILL)
    if not permitted:
        # Publish an audit event on the bus if available (best-effort)
        try:
            from orchestration_bridge import _bus
            asyncio.create_task(
                _bus.publish(
                    "audit.kill_denied",
                    {"identity": identity, "timestamp": __import__("datetime").datetime.utcnow().isoformat()},
                )
            )
        except Exception:
            pass
    return permitted


async def gate_emergency_arm(identity: str) -> bool:
    """Gate emergency-arm operations through RBACGuard.

    Only identities with ``Permission.EMERGENCY_ARM`` (admin) may proceed.

    Args:
        identity: The identity requesting the emergency arm.

    Returns:
        True if permitted, False otherwise (never raises).
    """
    permitted = _rbac.check(identity, Permission.EMERGENCY_ARM)
    if not permitted:
        try:
            from orchestration_bridge import _bus
            asyncio.create_task(
                _bus.publish(
                    "audit.emergency_denied",
                    {"identity": identity, "timestamp": __import__("datetime").datetime.utcnow().isoformat()},
                )
            )
        except Exception:
            pass
    return permitted


# Track which missions have already acquired budget (two-phase tracking)
_budget_acquired: set[str] = set()


async def track_mission_cost(
    mission_id: str,
    estimated_cost: float,
    actual_cost: float | None = None,
) -> dict:
    """Track per-mission LLM costs via BudgetController.

    Supports two-phase usage:
        1. Call before the mission with ``actual_cost=None`` to acquire budget.
        2. Call after the mission with ``actual_cost=<real_cost>`` to release.

    Alternatively, call once with both args and the reservation is
    acquired and released in a single step.

    Args:
        mission_id:      Unique mission identifier.
        estimated_cost:  Estimated USD cost (e.g. from tracer.total_cost_usd).
        actual_cost:     Real USD cost after execution.  If None, only the
                         reservation is created and the caller must call
                         again later with the real cost to release it.

    Returns:
        Dict with ``acquired`` (bool), ``released`` (bool), ``spent`` (float).

    Raises:
        RuntimeError: If the budget cannot be acquired (mission should abort).
    """
    # Phase 1 — acquire if not already reserved for this mission
    if mission_id not in _budget_acquired:
        acquired = await _budget.acquire_budget(mission_id, estimated_cost)
        if not acquired:
            raise RuntimeError(
                f"Budget acquisition failed for mission '{mission_id}'. "
                f"Estimated cost ${estimated_cost:.4f} exceeds the current limit."
            )
        _budget_acquired.add(mission_id)

    # Phase 2 — release when actual cost is known
    if actual_cost is not None:
        await _budget.release_budget(mission_id, actual_cost)
        _budget_acquired.discard(mission_id)

    spent = await _budget.get_spent()
    return {
        "acquired": True,
        "released": actual_cost is not None,
        "mission_id": mission_id,
        "estimated": estimated_cost,
        "actual": actual_cost,
        "spent_total": spent,
    }


# ── Convenience: assign role at runtime ─────────────────────────────────────

def assign_identity_role(identity: str, role: str) -> None:
    """Assign a pre-defined role to an identity at runtime.

    Args:
        identity: Unique identity string.
        role:     One of "orchestrator", "agent", "auditor", "admin".
    """
    _rbac.assign_role(identity, role)


def revoke_identity_role(identity: str, role: str) -> None:
    """Revoke a role from an identity."""
    _rbac.revoke(identity, role)


# ── Self-test ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    async def _self_test() -> None:
        print("Safety Proxy self-test...")

        # 1. Safe input
        try:
            r = await safety_scan_input("Build a REST API for user auth")
            print(f"  [OK] safe scan: threat={r['threat_level']}, violations={r['violations']}")
        except SafetyError as e:
            print(f"  [FAIL] safe scan raised: {e}")

        # 2. Unsafe input
        try:
            await safety_scan_input("rm -rf / --no-preserve-root")
            print("  [FAIL] unsafe scan did not raise")
        except SafetyError as e:
            print(f"  [OK] unsafe scan blocked: {e}")

        # 3. RBAC — admin can kill, anonymous cannot
        assign_identity_role("admin_user", "admin")
        assert await gate_kill("admin_user") is True
        assert await gate_kill("random_user") is False
        print("  [OK] RBAC kill gate")

        # 4. RBAC — emergency arm
        assert await gate_emergency_arm("admin_user") is True
        assert await gate_emergency_arm("random_user") is False
        print("  [OK] RBAC emergency-arm gate")

        # 5. Budget tracking
        await _budget.set_limit(100.0, period="daily")
        result = await track_mission_cost("test-mission-001", estimated_cost=0.50, actual_cost=0.42)
        print(f"  [OK] budget tracking: spent=${result['spent_total']:.4f}")

        # 6. Budget overflow
        try:
            await track_mission_cost("test-mission-002", estimated_cost=999.00)
            print("  [FAIL] budget overflow did not raise")
        except RuntimeError as e:
            print(f"  [OK] budget overflow blocked: {e}")

        print("\nSafety Proxy self-test PASSED")

    asyncio.run(_self_test())
