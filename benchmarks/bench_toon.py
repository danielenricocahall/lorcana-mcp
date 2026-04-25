"""Compare JSON vs TOON encoding cost for representative search_cards responses.

Run from the project root:
    uv run python benchmarks/bench_toon.py

Tokenizer is tiktoken's cl100k_base if installed, used as a proxy for Claude's
tokenizer; falls back to a chars/4 estimate otherwise. Numbers are directional
either way — relative deltas matter more than absolute counts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lorcana_mcp.repository import InMemoryCardRepository
from lorcana_mcp.toon import to_toon

try:
    import tiktoken

    _enc = tiktoken.get_encoding("cl100k_base")

    def count_tokens(s: str) -> int:
        return len(_enc.encode(s))

    TOKENIZER = "tiktoken cl100k_base (proxy for Claude)"
except ImportError:

    def count_tokens(s: str) -> int:
        return len(s) // 4

    TOKENIZER = "chars/4 estimate (install tiktoken for real counts)"


CACHE = Path("cards.json")

QUERIES: list[tuple[str, dict[str, Any]]] = [
    ("amber chars, limit=200", {"color": "amber", "limit": 200}),
    ("ruby chars, limit=50", {"color": "ruby", "limit": 50}),
    ("actions only (sparse cols), limit=50", {"card_type": "action", "limit": 50}),
    ("body_text='when' (long full_text), limit=50", {"body_text": "when", "limit": 50}),
    ("name='elsa', limit=20", {"name": "elsa", "limit": 20}),
]


def fmt(n: int) -> str:
    return f"{n:>8,}"


def pct(new: int, old: int) -> str:
    if not old:
        return "   --"
    delta = (new - old) / old * 100
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta:5.1f}%"


def main() -> None:
    if not CACHE.exists():
        raise SystemExit(f"{CACHE} not found. Run the server once to populate the cache.")

    repo = InMemoryCardRepository(cache_path=CACHE)
    print(f"Loaded {repo.total_cards} cards from {CACHE}")
    print(f"Tokenizer: {TOKENIZER}\n")

    header = (
        f"{'query':<46} {'rows':>5}  {'json B':>9} {'toon B':>9} {'B Δ':>7}  {'json T':>9} {'toon T':>9} {'T Δ':>7}"
    )
    print(header)
    print("-" * len(header))

    totals = {"json_b": 0, "toon_b": 0, "json_t": 0, "toon_t": 0}

    for label, kwargs in QUERIES:
        results = repo.search(**kwargs)
        json_str = json.dumps(results, ensure_ascii=False)
        toon_str = to_toon(results)

        jb = len(json_str.encode("utf-8"))
        tb = len(toon_str.encode("utf-8"))
        jt = count_tokens(json_str)
        tt = count_tokens(toon_str)

        totals["json_b"] += jb
        totals["toon_b"] += tb
        totals["json_t"] += jt
        totals["toon_t"] += tt

        print(
            f"{label:<46} {len(results):>5}  {fmt(jb)} {fmt(tb)} {pct(tb, jb):>7}  {fmt(jt)} {fmt(tt)} {pct(tt, jt):>7}"
        )

    print("-" * len(header))
    print(
        f"{'TOTAL':<46} {'':>5}  "
        f"{fmt(totals['json_b'])} {fmt(totals['toon_b'])} {pct(totals['toon_b'], totals['json_b']):>7}  "
        f"{fmt(totals['json_t'])} {fmt(totals['toon_t'])} {pct(totals['toon_t'], totals['json_t']):>7}"
    )


if __name__ == "__main__":
    main()
