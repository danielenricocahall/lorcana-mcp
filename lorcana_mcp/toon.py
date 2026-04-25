from __future__ import annotations

from typing import Any


def _toon_value(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    if "," in s or "\n" in s or s.startswith('"'):
        return '"' + s.replace('"', '""') + '"'
    return s


def to_toon(rows: list[dict[str, Any]], name: str = "rows") -> str:
    """Encode a list of flat homogeneous-ish dicts as TOON.

    Output format (one example):
        cards[2]{id,name,cost}:
        1,Mickey Mouse,3
        2,Elsa,5

    Columns are the union of keys across rows in first-seen order; missing
    values render as empty cells. Strings containing the comma delimiter,
    a newline, or a leading double-quote are RFC4180-style quoted.
    """
    if not rows:
        return f"{name}[0]{{}}:\n"

    cols: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for k in row.keys():
            if k not in seen:
                seen.add(k)
                cols.append(k)

    header = f"{name}[{len(rows)}]{{{','.join(cols)}}}:"
    body = [",".join(_toon_value(row.get(c)) for c in cols) for row in rows]
    return header + "\n" + "\n".join(body) + "\n"
