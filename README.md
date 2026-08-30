# verify-loop — agent + messy-data integration starter (FDE-style demo)

What companies actually ask forward-deployed engineers, answered by a runnable repo:

1. How much of a claims-style workflow can you automate before the error rate is unacceptable?
2. When the pipeline gives a bad answer — retrieval fail, bad reasoning, stale source, or a guard trip?
3. How much access can an agent have before spend/dup guards pay for themselves?

## The loop

```
messy CSV in ──> normalize ──> agent classify (OpenRouter, GLM 5.3 Flash free tier)
                                   │
                                   ├─ spend guard ($ cap per run)
                                   ├─ dup guard (content-hash ledger)
                                   └─ eval loop (precision/recall vs labels)
                                            │
                                       report.json + scorecard.md
```

## Quick start (uv)

```bash
uv venv
uv pip install -r requirements.txt   # stdlib-only except openai-compatible client
set OPENROUTER_API_KEY=...           # or any OpenAI-compatible key
uv run python pipeline.py sample_data/claims_messy.csv
```

Optional live example: `pipeline.py --x402-demo` shows the same output wrapped as a
pay-per-call endpoint (see x402 section below).

## What's in the box

| File | Role |
|---|---|
| `pipeline.py` | end-to-end: normalize → classify → guards → report (single file, readable top-to-bottom) |
| `guards.py` | spend cap + duplicate-action ledger (the "how much access before it hurts" answer) |
| `eval_loop.py` | precision/recall/abstain scoring vs `sample_data/labels.jsonl` |
| `sample_data/` | deliberately messy claims CSV (mixed dates, dupes, missing fields) |
| `justfile` | `just demo`, `just eval` |

## Lessons encoded (from running this against real workloads)

- Guard order matters: dedupe BEFORE spend, or the model pays to re-see rows.
- Abstention is a first-class output: "uncertain" beats confident-wrong for triage.
- Every guard logs WHY it fired; unexplained blocks get overridden and then abandoned.

Built with: a minimal-diff discipline (ponytail-style rules), a taste skill for the
README surface, and the uv toolchain. Built as a forward-deployed-engineering
portfolio demo.

---
Built 2026-08-29 with an agent-assisted workflow. Demo runs fully offline with --dry-run; live mode uses any OpenAI-compatible key via OpenRouter.
