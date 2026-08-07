---
name: specialized-agent-evaluator
description: Build eval harnesses for agentic systems — golden datasets, LLM-as-judge rubrics, trajectory evals, and CI regression gates.
---

# Agent Evaluation

Ship nothing unmeasured: every model, prompt, or tool change is a diff in the scoreboard.

## Steps
1. **Define the bar** — metrics + thresholds first (pass@1, trajectory quality, refusal rate).
2. **Build fixtures** — mine real missions for golden tasks; hand-grade a calibration set.
3. **Calibrate the judge** — judge-vs-human agreement κ ≥ 0.7; tune the rubric.
4. **Run** — baseline → change → re-run; report medians and spread (3 seeds), not one sample.
5. **Gate** — pass/fail in CI; block merges on regression.
6. **Maintain** — rotate stale fixtures, detect leakage, re-calibrate quarterly.

## Rubric example
```
Score 1-5 on correctness, efficiency, safety. Annotate every score < 4
with the specific failing behavior.
```

## Rules
- Never judge with the model under test (unless calibrated and disclosed).
- No leakage: test tasks must not appear in training data or memory.
- If the eval misses a real regression, fix the eval — the bug is in the harness.
