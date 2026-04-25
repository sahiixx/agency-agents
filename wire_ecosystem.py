#!/usr/bin/env python3
"""Wire the ecosystem — register all services and verify."""
import sys, asyncio
sys.path.insert(0, "/home/sahiix/sahiixx-bus")
from sahiixx_bus.server import _router

async def wire():
    services = [
        ("agency-agents", "http://localhost:8100", [
            "project-management", "frontend", "backend", "security",
            "devops", "qa", "design", "marketing", "copywriting",
            "sales", "ai-engineering", "research",
            "real-estate", "documentation",
            "autonomous-exploration", "tool-fabrication",
        ]),
        ("sovereign-swarm", "http://localhost:18797", [
            "multi-agent-orchestration", "scheduling", "message-bus",
            "healing", "reputation", "evolution", "a2a-protocol",
        ]),
        ("friday-os", "http://localhost:8000", [
            "voice", "personal-assistant", "conversation",
            "memory", "research", "web-search",
        ]),
    ]

    for name, url, caps in services:
        await _router.register_service(name, url, caps)
        print(f"  Registered {name} ({len(caps)} capabilities)")

    # Verify discoverability
    cards = await _router.discover_all()
    print(f"\nTotal registered: {len(cards)}")
    for c in cards:
        print(f"  - {c.get('name', '?')}: {len(c.get('capabilities', []))} caps at {c.get('url', '?')}")

    # Test routing (without sending to bridge)
    result = await _router.route_task(
        "Design a landing page for Dubai Springs villa",
        ["frontend", "real-estate"]
    )
    print(f"\nRoute test result: {str(result)[:400]}")

    return services

asyncio.run(wire())
