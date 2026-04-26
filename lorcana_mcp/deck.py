"""Lorcana deck list format: `<count> <full_name>` per line.

This is the canonical Lorcana deck format used by Dreamborn exports, Pixelborn
imports, and Limitless tournament submissions. There are no sections, no
sideboards, and no set codes — just one line per stack of identical cards.

Example:
    4 Mickey Mouse - Brave Little Tailor
    4 Aladdin - Street Rat
    3 Be Prepared
"""

from __future__ import annotations

import re
from typing import Any, NamedTuple

LORCANA_MIN_DECK_SIZE = 60
LORCANA_MAX_COPIES = 4
LORCANA_MAX_INKS = 2

# Matches `4 Card Name` or `4x Card Name`, with arbitrary surrounding whitespace.
_LINE_RE = re.compile(r"^\s*(\d+)\s*x?\s+(.+?)\s*$", re.IGNORECASE)

# Lines we deliberately skip (totals, comments, section headers).
_SKIP_RE = re.compile(r"^\s*(?:#|//|total\b|\[)", re.IGNORECASE)


class ParsedLine(NamedTuple):
    count: int
    name: str
    raw: str


class MalformedLine(NamedTuple):
    raw: str


def dump_deck(entries: list[dict]) -> str:
    """Render a deck list as text. Each entry is `{name: str, count: int}`.

    Entries are emitted in the order given. Counts <= 0 are skipped. The output
    ends with a trailing newline so concatenation/append is well-behaved.
    """
    lines = []
    for entry in entries:
        count = int(entry["count"])
        if count <= 0:
            continue
        name = str(entry["name"]).strip()
        lines.append(f"{count} {name}")
    return "\n".join(lines) + ("\n" if lines else "")


def parse_lines(text: str) -> list[ParsedLine | MalformedLine]:
    """Parse deck list text into per-line records.

    Blank lines, comments (`#`, `//`), totals (`Total: 60`), and bracketed
    section headers are silently skipped. Lines that look like `<count> <name>`
    are returned as `ParsedLine`; everything else as `MalformedLine` so callers
    can surface them.

    Em-dash / en-dash characters in card names are normalized to ASCII hyphens
    so copy-paste from word processors still resolves cleanly.
    """
    out: list[ParsedLine | MalformedLine] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        if _SKIP_RE.match(line):
            continue
        m = _LINE_RE.match(line)
        if not m:
            out.append(MalformedLine(raw=line))
            continue
        count = int(m.group(1))
        name = m.group(2).replace("–", "-").replace("—", "-").strip()
        out.append(ParsedLine(count=count, name=name, raw=line))
    return out


def validate_deck(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Validate a Lorcana deck against the format rules.

    Each entry: `{"count": int, "name": str, "card": dict | None}`. `card` is
    the resolved card dict (with `color`, `inkwell`, etc.) or `None` if the
    name didn't resolve.

    Rules enforced: deck size ≥ 60 (no maximum — 60 is just the floor), max
    4 copies of any card, ≤ 2 distinct ink colors across the deck. The
    dual-ink rule is folded into the ink limit — including a Ruby/Sapphire
    dual-ink card adds both colors to the deck's ink set, so a deck that
    would otherwise be mono-Ruby will trip `ink_limit` if the union exceeds 2.
    """
    violations: list[dict[str, Any]] = []
    total = sum(int(e.get("count", 0)) for e in entries)

    if total < LORCANA_MIN_DECK_SIZE:
        violations.append({"type": "deck_size", "total": total, "min": LORCANA_MIN_DECK_SIZE})

    counts_by_name: dict[str, int] = {}
    for entry in entries:
        name = str(entry.get("name", ""))
        counts_by_name[name] = counts_by_name.get(name, 0) + int(entry.get("count", 0))
    for name, count in counts_by_name.items():
        if count > LORCANA_MAX_COPIES:
            violations.append({"type": "max_copies", "card": name, "count": count, "max": LORCANA_MAX_COPIES})

    inks: set[str] = set()
    for entry in entries:
        card = entry.get("card")
        if card is None:
            violations.append(
                {"type": "unknown_card", "name": str(entry.get("name", "")), "count": int(entry.get("count", 0))}
            )
            continue
        for color in card.get("color") or []:
            inks.add(color)

    if len(inks) > LORCANA_MAX_INKS:
        violations.append({"type": "ink_limit", "inks": sorted(inks), "max": LORCANA_MAX_INKS})

    return {
        "legal": len(violations) == 0,
        "total_cards": total,
        "inks": sorted(inks),
        "violations": violations,
    }


def deck_stats(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute summary stats for a Lorcana deck.

    Color split counts copies per color; dual-ink cards contribute to BOTH
    color buckets, so the sum of `color_split` values may exceed `total_cards`
    by the dual-ink contribution. Unresolved names are excluded from the per-
    card stats but still counted in `total_cards`.
    """
    total = 0
    inks: set[str] = set()
    ink_curve: dict[int, int] = {}
    color_split: dict[str, int] = {}
    type_breakdown: dict[str, int] = {}
    inkable_count = 0
    uninkable_count = 0
    unresolved: list[str] = []

    for entry in entries:
        count = int(entry.get("count", 0))
        total += count
        card = entry.get("card")
        if card is None:
            unresolved.append(str(entry.get("name", "")))
            continue
        cost = card.get("cost")
        if cost is not None:
            ink_curve[int(cost)] = ink_curve.get(int(cost), 0) + count
        for color in card.get("color") or []:
            inks.add(color)
            color_split[color] = color_split.get(color, 0) + count
        if card.get("inkwell"):
            inkable_count += count
        else:
            uninkable_count += count
        ctype = str(card.get("type") or "Unknown")
        type_breakdown[ctype] = type_breakdown.get(ctype, 0) + count

    return {
        "total_cards": total,
        "inks": sorted(inks),
        "ink_curve": dict(sorted(ink_curve.items())),
        "color_split": color_split,
        "inkable_count": inkable_count,
        "uninkable_count": uninkable_count,
        "type_breakdown": type_breakdown,
        "unresolved": unresolved,
    }
