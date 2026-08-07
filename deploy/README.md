Deployment notes — Jarvis operator

This repo includes a lightweight Jarvis operator integration (jarvis/operator.py)
that lets Jarvis act as a front-end operator to the Agency orchestrator.

Quick enable:

1. Install dependencies (see README.md and setup.sh). Ensure jarvis/ is
   installed or available in the repository (it's present as an optional
   local module).

2. By default the operator uses dry-run mode. To allow live LLM calls, set:

```bash
export JARVIS_OPERATOR_ALLOW_LIVE=1
```

3. Run the operator (interactive):

```bash
python3 -m jarvis.operator
```

Or run a one-off mission:

```bash
python3 -m jarvis.operator --mission "Build a REST API for user authentication" --preset full
```

Security and production notes
-----------------------------
- Keep API keys in a secrets manager; do not set them in plaintext or commit to
  the repo. Use environment variables in your process manager or container runtime.
- The operator intentionally runs in dry-run by default to avoid accidental
  LLM invocation. Only set JARVIS_OPERATOR_ALLOW_LIVE=1 in trusted environments.

Integration with dashboard & A2A
--------------------------------
The operator is independent of the Next.js dashboard and A2A server, but can be
run on the same host or a separate operator host. For higher-availability, run
the operator behind a process manager (systemd, supervisord) or as a K8s
Deployment with resource limits.
