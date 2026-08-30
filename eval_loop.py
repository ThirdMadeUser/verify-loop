"""Score results against labels. See module docstring for the abstention stance."""
from __future__ import annotations

import json
from pathlib import Path


def score(results: list[dict], labels_path: Path) -> str:
    gold = {}
    for line in labels_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            gold[d["row"]] = d["label"]

    tp = errors = reviews = 0
    error_rows: list[str] = []
    for r in results:
        g = gold.get(r["row"])
        if g is None:
            continue
        pred = r["label"]
        if pred == "review":
            reviews += 1
        elif pred == g:
            tp += 1
        else:
            errors += 1
            error_rows.append(f"row {r['row']}: said {pred}, truth {g} ({r.get('why', '')})")

    confident = tp + errors
    precision = tp / confident if confident else 1.0
    lines = [
        "# Scorecard",
        "",
        f"- confident-correct: {tp}",
        f"- confident-WRONG (the metric): {errors}"
        + (f" -> {'; '.join(error_rows)}" if error_rows else ""),
        f"- abstained to human: {reviews}",
        f"- precision {precision:.2f} (confident calls only)",
        "",
        f"verdict: {'PASS' if errors == 0 else 'CHECK ERROR ROWS'}",
    ]
    return "\n".join(lines) + "\n"
