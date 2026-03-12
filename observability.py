#!/usr/bin/env python3
"""
observability.py — LangSmith-style tracing and cost tracking for The Agency.

Tracks per-agent:
  - Token usage (input / output)
  - Latency (ms)
  - Cost estimate (Sonnet 4.6 pricing)
  - Verdict

Writes a JSON trace to /tmp/agency_outputs/trace_<timestamp>.json
Prints a live summary table after each mission.

Usage:
  from observability import AgencyTracer
  tracer = AgencyTracer(mission="...")
  with tracer.span("pm"):
      ...
  tracer.finish(verdict="GO")
  tracer.print_summary()
"""

import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

OUTPUTS_DIR = Path("/tmp/agency_outputs")
OUTPUTS_DIR.mkdir(exist_ok=True)

# Claude Sonnet 4.6 pricing (per million tokens, as of early 2026)
PRICE_INPUT_PER_M  = 3.00   # $3.00 / 1M input tokens
PRICE_OUTPUT_PER_M = 15.00  # $15.00 / 1M output tokens


@dataclass
class AgentSpan:
    agent:        str
    started_at:   float = field(default_factory=time.time)
    ended_at:     float = 0.0
    input_tokens: int   = 0
    output_tokens: int  = 0
    error:        Optional[str] = None

    @property
    def latency_ms(self) -> float:
        if self.ended_at:
            return (self.ended_at - self.started_at) * 1000
        return 0.0

    @property
    def cost_usd(self) -> float:
        return (
            self.input_tokens  / 1_000_000 * PRICE_INPUT_PER_M +
            self.output_tokens / 1_000_000 * PRICE_OUTPUT_PER_M
        )


class AgencyTracer:
    def __init__(self, mission: str, preset: str = "full"):
        self.mission    = mission
        self.preset     = preset
        self.started_at = time.time()
        self.spans:     list[AgentSpan] = []
        self.verdict:   str = "PENDING"
        self._current:  Optional[AgentSpan] = None
        self.trace_id   = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    # ── Context manager for per-agent spans ──────────────────────────────────
    def span(self, agent: str):
        return _SpanContext(self, agent)

    def _start_span(self, agent: str) -> AgentSpan:
        s = AgentSpan(agent=agent)
        self.spans.append(s)
        self._current = s
        return s

    def _end_span(self, span: AgentSpan, error: Optional[str] = None):
        span.ended_at = time.time()
        span.error    = error
        self._current = None

    def add_tokens(self, input_tokens: int, output_tokens: int):
        """Call after an LLM response to record token usage."""
        if self._current:
            self._current.input_tokens  += input_tokens
            self._current.output_tokens += output_tokens

    def finish(self, verdict: str):
        self.verdict   = verdict
        self.ended_at  = time.time()

    # ── Summary ───────────────────────────────────────────────────────────────
    @property
    def total_latency_ms(self) -> float:
        return (getattr(self, "ended_at", time.time()) - self.started_at) * 1000

    @property
    def total_cost_usd(self) -> float:
        return sum(s.cost_usd for s in self.spans)

    @property
    def total_tokens(self) -> tuple[int, int]:
        return (
            sum(s.input_tokens  for s in self.spans),
            sum(s.output_tokens for s in self.spans),
        )

    def print_summary(self):
        tin, tout = self.total_tokens
        print(f"\n{'━'*65}")
        print(f"  OBSERVABILITY REPORT — {self.trace_id}")
        print(f"{'━'*65}")
        print(f"  Mission:  {self.mission[:55]}")
        print(f"  Preset:   {self.preset}   Verdict: {self.verdict}")
        print(f"  Total:    {self.total_latency_ms/1000:.1f}s  |  "
              f"${self.total_cost_usd:.4f}  |  "
              f"{tin+tout:,} tokens")
        print(f"{'─'*65}")
        print(f"  {'Agent':<14} {'Latency':>9} {'Tokens-In':>10} {'Tokens-Out':>11} {'Cost':>9} {'Status':>8}")
        print(f"{'─'*65}")
        for s in self.spans:
            status = "ERROR" if s.error else "OK"
            print(f"  {s.agent:<14} {s.latency_ms/1000:>8.1f}s "
                  f"{s.input_tokens:>10,} {s.output_tokens:>11,} "
                  f"${s.cost_usd:>8.4f} {status:>8}")
        print(f"{'━'*65}\n")

    def save_trace(self) -> Path:
        path = OUTPUTS_DIR / f"trace_{self.trace_id}.json"
        tin, tout = self.total_tokens
        trace = {
            "trace_id":       self.trace_id,
            "mission":        self.mission,
            "preset":         self.preset,
            "verdict":        self.verdict,
            "total_ms":       self.total_latency_ms,
            "total_cost_usd": self.total_cost_usd,
            "total_input_tokens":  tin,
            "total_output_tokens": tout,
            "model":          "claude-sonnet-4-6",
            "spans": [
                {
                    "agent":         s.agent,
                    "latency_ms":    s.latency_ms,
                    "input_tokens":  s.input_tokens,
                    "output_tokens": s.output_tokens,
                    "cost_usd":      s.cost_usd,
                    "error":         s.error,
                }
                for s in self.spans
            ],
        }
        path.write_text(json.dumps(trace, indent=2))
        return path


class _SpanContext:
    def __init__(self, tracer: AgencyTracer, agent: str):
        self._tracer = tracer
        self._agent  = agent
        self._span:  Optional[AgentSpan] = None
        self._error: Optional[str]       = None

    def __enter__(self) -> AgentSpan:
        self._span = self._tracer._start_span(self._agent)
        return self._span

    def __exit__(self, exc_type, exc_val, exc_tb):
        error = str(exc_val) if exc_type else None
        self._tracer._end_span(self._span, error=error)
        return False  # don't suppress exceptions


if __name__ == "__main__":
    tracer = AgencyTracer("Test mission: build a login page", preset="full")
    agents = ["pm", "frontend", "qa", "core"]
    for agent in agents:
        with tracer.span(agent) as span:
            time.sleep(0.05)
            tracer.add_tokens(input_tokens=1200, output_tokens=800)
    tracer.finish("GO")
    tracer.print_summary()
    p = tracer.save_trace()
    print(f"Trace saved: {p}")
