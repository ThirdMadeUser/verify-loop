"""End-to-end demo: messy CSV in -> normalized -> classified (with abstention)
-> guards -> report.json + scorecard.md.

Single wiring file; real logic in guards.py / eval_loop.py.
Usage:
    uv run python pipeline.py sample_data/claims_messy.csv --dry-run
    uv run python pipeline.py sample_data/claims_messy.csv            # live, needs OPENROUTER_API_KEY
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from eval_loop import score
from guards import DupLedger, SpendGuard

HERE = Path(__file__).parent
DATE_RE = re.compile(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})|(\d{1,2})/(\d{1,2})/(\d{4})")


def normalize_amount(raw: str) -> float | None:
    """'$1,234.50' / '1234' / 'USD 900' -> float; None if unparsable."""
    m = re.search(r"[\d,]+(?:\.\d+)?", (raw or "").replace("USD", ""))
    return float(m.group(0).replace(",", "")) if m else None


def normalize_date(raw: str) -> str | None:
    """Whatever date-ish string -> ISO date; None covers malformed (bogus 2026-13-01)."""
    if not raw:
        return None
    m = DATE_RE.search(raw)
    if not m:
        return None
    try:
        if m.group(1):
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date().isoformat()
        return datetime(int(m.group(6)), int(m.group(4)), int(m.group(5))).date().isoformat()
    except ValueError:
        return None


def row_hash(claimant: str, amount: float, text: str) -> str:
    core = json.dumps([claimant.strip().lower(), amount, text.strip().lower()], sort_keys=True)
    return hashlib.sha256(core.encode()).hexdigest()[:16]


def classify(text: str, amount: float, dry_run: bool) -> dict:
    """One label per claim: approve / reject / review (abstention is first-class)."""
    if dry_run:
        label = "approve" if "receipt" in text.lower() else "review"
        return {"label": label, "why": "dry-run heuristic: receipt keyword"}

    from openai import OpenAI  # late import so --dry-run needs no SDK

    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPENROUTER_API_KEY"])
    r = client.chat.completions.create(
        model="z-ai/glm-5.3-flash",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": (
                "Label this expense claim approve|reject|review. Reply JSON "
                f'{{"label":"...","why":"..."}} only.\namount={amount}\ntext={text[:400]}'
            ),
        }],
    )
    try:
        out = json.loads(r.choices[0].message.content)
        return {"label": out.get("label", "review"), "why": out.get("why", "")}
    except (json.JSONDecodeError, AttributeError, TypeError):
        return {"label": "review", "why": "unparsable model output"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("csv_path")
    ap.add_argument("--dry-run", action="store_true", help="no LLM calls, heuristics only")
    ap.add_argument("--spend-cap", type=float, default=0.05, help="max USD for this run")
    ap.add_argument("--out-dir", default=str(HERE / "out"))
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    spend = SpendGuard(cap_usd=args.spend_cap)
    ledger = DupLedger(path=out_dir / "seen_hashes.json")
    results: list[dict] = []
    dropped = {"dupe": 0, "bad_row": 0}

    with open(args.csv_path, newline="", encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f)):
            row = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
            amount = normalize_amount(row.get("amount", ""))
            date = normalize_date(row.get("date", ""))
            text = row.get("text") or row.get("description") or ""
            if amount is None or not text:
                dropped["bad_row"] += 1
                results.append({"row": i, "label": "review", "why": "malformed row",
                                "amount": amount, "date": date})
                continue

            h = row_hash(row.get("claimant", ""), amount, text)
            if ledger.seen(h):
                dropped["dupe"] += 1
                continue
            if not spend.allow():
                results.append({"row": i, "label": "review",
                                "why": f"spend cap hit (${spend.spent:.2f})",
                                "amount": amount, "date": date})
                continue

            verdict = classify(text, amount, args.dry_run)
            results.append({"row": i, "label": verdict["label"], "why": verdict["why"],
                            "amount": amount, "date": date, "hash": h})

    (out_dir / "report.json").write_text(
        json.dumps({"results": results, "dropped": dropped, "spend": spend.summary()}, indent=2),
        encoding="utf-8",
    )
    labels = HERE / "sample_data" / "labels.jsonl"
    if labels.exists():
        card = score(results, labels)
        (out_dir / "scorecard.md").write_text(card, encoding="utf-8")
        print(card)
    print(f"report -> {out_dir / 'report.json'}  (dropped: {dropped})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
