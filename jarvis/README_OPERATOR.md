# Jarvis as Agency Operator

This document explains how to use the Jarvis operator integration that lets
Jarvis act as the front-end operator for The Agency.

Overview
--------
The operator (jarvis/operator.py) attempts to use Jarvis' AI brain when
available (jarvis/modules/ai_brain.AIBrain). If the Jarvis brain is not
present or its constructor fails, the operator falls back to a simple
stdin-based interactive loop.

Safety
------
- By default the operator runs missions in dry-run mode (no cloud LLM calls).
  This prevents accidental charges or long-running model calls.
- To enable live runs set the environment variable:

```bash
export JARVIS_OPERATOR_ALLOW_LIVE=1
```

Usage
-----
One-off mission (non-interactive):

```bash
python3 -m jarvis.operator --mission "Build a REST API for user auth" --preset saas
```

Interactive mode (stdin):

```bash
python3 -m jarvis.operator
# then type missions at the prompt, e.g.:
# Mission> Design a landing page --preset saas
```

If Jarvis' AIBrain is available, the operator will use it to capture natural
language missions instead of requiring typed input.

Notes for integration
---------------------
- The operator imports agency.run_mission lazily at runtime to avoid import
  cycles. Keep the operator as a thin bridge layer; heavy changes should be
  applied inside agency.run_mission or a dedicated API wrapper.
- The operator will respect `--agents a,b,c` and `--preset name` when present
  in a one-off invocation or when included in the natural language mission
  string.
