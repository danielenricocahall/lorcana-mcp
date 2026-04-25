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
from typing import NamedTuple

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
