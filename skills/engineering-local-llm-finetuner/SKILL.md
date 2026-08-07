---
name: engineering-local-llm-finetuner
description: Fine-tune and serve local open-weight LLMs with LoRA/QLoRA, curate datasets, evaluate, and export to Ollama as GGUF.
---

# Local LLM Fine-Tuning

Adapt open-weight models (Qwen, Llama, Gemma, DeepSeek) to a domain, fully offline.

## Steps
1. **Scope** — task, data, eval set; fine-tune vs prompt vs RAG.
2. **Baseline** — eval the base model first; record numbers.
3. **Data** — collect → clean → dedup → ChatML format → split 90/10.
4. **Train** — LoRA/QLoRA (r=64, α=128), 1–3 epochs, seed pinned; log everything.
5. **Merge & quantize** — merge adapter, export GGUF (Q4_K_M/Q8_0), `ollama create` via Modelfile.
6. **Eval gate** — rerun eval set; ship only if the bar holds.

## Modelfile
```dockerfile
FROM qwen3-coder:30b-q4_K_M
PARAMETER temperature 0.3
SYSTEM "You are the internal assistant for ACME Corp..."
```

## Rules
- No fine-tune without a baseline eval; 5–10% general data to prevent forgetting.
- Prefer the smallest model meeting the eval bar; keep everything local.
- End every run with a model card (base, recipe, data stats, evals, quantization).
