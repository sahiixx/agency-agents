---
name: engineering-agent-observability
description: Instrument and debug LLM agent pipelines — traces, spans, token/cost tracking, eval-in-prod, and MCP tool telemetry.
---

# Agentic Observability

Instrument every agent run so failures stop being mysteries.

## Steps
1. **Map the graph** — orchestrator, subagents, A2A servers, MCP tools: every hop is a span.
2. **Instrument** — wrap `agent.invoke()` and every tool call with span records (timestamps, tokens, cost, tool, latency, outcome).
3. **Propagate** — one `trace_id` across the whole mission.
4. **Analyze** — cost per agent/tool, loop detection, failure clustering, latency percentiles.
5. **Gate** — eval sampled runs in CI; alert on budget/error-rate regressions.

## Span record
```json
{"trace_id":"tr_9f2c","span_id":"sp_ab12","agent":"pm","model":"qwen3:8b","tool":"web_search","duration_ms":2140,"input_tokens":812,"output_tokens":402,"cost_usd":0.0004,"outcome":"ok"}
```

## Rules
- Redact secrets/PII before storing traces; follow OpenTelemetry GenAI conventions.
- Every alert needs a runbook with a trace example.
- If a step is invisible in the trace, that is an observability bug.
