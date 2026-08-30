# ops tasks
set shell := ["powershell", "-NoProfile", "-Command"]

default:
    @just --list

# Run the demo end-to-end without LLM calls (heuristic mode)
demo:
    uv run python pipeline.py sample_data/claims_messy.csv --dry-run

# Run against the labels file and print the scorecard
eval:
    uv run python pipeline.py sample_data/claims_messy.csv --dry-run

# Live mode (needs OPENROUTER_API_KEY; spends < cap)
live:
    uv run python pipeline.py sample_data/claims_messy.csv

# Lint (read-only)
lint:
    -uvx ruff check .
