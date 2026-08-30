"""Guards: spend cap + duplicate-action ledger.

The FDE question these answer: how much access before guards pay for themselves?
Encoded rules: dedupe BEFORE spend; log WHY every block fired (unexplained blocks
get overridden, then abandoned).
"""
from __future__ import annotations

import json
from pathlib import Path


class SpendGuard:
    """Hard cap per run. allow() checks; charge() records."""

    def __init__(self, cap_usd: float):
        self.cap = cap_usd
        self.spent = 0.0
        self.log: list[str] = []

    def allow(self) -> bool:
        ok = self.spent < self.cap
        if not ok:
            self.log.append(f"BLOCK spend cap ${self.spent:.4f}/${self.cap:.2f}")
        return ok

    def charge(self, usd: float) -> None:
        self.spent += usd

    def summary(self) -> dict:
        return {"cap": self.cap, "spent": round(self.spent, 4), "blocks": self.log}


class DupLedger:
    """Content-hash seen-set with optional persistence (restart-safe dedupe)."""

    def __init__(self, path: Path | None = None):
        self.path = path
        self._seen: set[str] = set()
        if path and path.exists():
            self._seen = set(json.loads(path.read_text(encoding="utf-8")))

    def seen(self, h: str) -> bool:
        """True if h was seen before this call; records it either way."""
        was = h in self._seen
        self._seen.add(h)
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(sorted(self._seen)), encoding="utf-8")
        return was
