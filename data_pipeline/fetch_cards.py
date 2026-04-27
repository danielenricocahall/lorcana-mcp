"""Fetch the Lorcana card catalog from Lorcast and write a normalized list to disk.

Intended to run as a scheduled GitHub Actions job, not from inside the shipped
MCP container. Lorcast's API is public and unauthenticated; no secrets needed.

The output JSON is a flat list of cards in our internal schema (the shape the
runtime repository consumes directly), so the runtime never needs to do any
schema mapping — it just `requests.get` + `.json()` and loads the list into
memory.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

BASE_URL = "https://api.lorcast.com/v0"
REQUEST_DELAY_SECONDS = 0.12  # Lorcast asks for ~50–100ms; this is slightly conservative.
TIMEOUT_SECONDS = 30
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "lorcana-mcp/data-pipeline (+https://github.com/danielenricocahall/lorcana-mcp)",
}

logger = logging.getLogger("fetch_cards")


def _get_json(url: str, max_attempts: int = 5) -> dict[str, Any]:
    """GET a URL with retry handling for 429s and 5xx responses."""
    last_error: str | None = None
    for attempt in range(max_attempts):
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT_SECONDS)

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            sleep_for = float(retry_after) if retry_after else 2**attempt
            logger.warning("Rate limited at %s; sleeping %.1fs", url, sleep_for)
            time.sleep(sleep_for)
            continue

        if 500 <= response.status_code < 600:
            sleep_for = 2**attempt
            last_error = f"status {response.status_code}"
            logger.warning("Server error %s at %s; retrying in %ds", response.status_code, url, sleep_for)
            time.sleep(sleep_for)
            continue

        response.raise_for_status()
        return response.json()

    raise RuntimeError(f"GET {url} failed after {max_attempts} attempts (last error: {last_error})")


def fetch_sets() -> list[dict[str, Any]]:
    data = _get_json(f"{BASE_URL}/sets")
    results = data.get("results")
    if not isinstance(results, list):
        raise ValueError(f"Unexpected /sets response shape: {data!r}")
    return results


def fetch_cards_for_set(set_code: str) -> list[dict[str, Any]]:
    """Fetch all printings for a set. `unique=prints` returns individual printings."""
    query = quote(f"set:{set_code}")
    data = _get_json(f"{BASE_URL}/cards/search?q={query}&unique=prints")
    results = data.get("results")
    if not isinstance(results, list):
        raise ValueError(f"Unexpected /cards/search response shape for set {set_code}: {data!r}")
    return results


def _make_simple_name(full_name: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", full_name.lower())).strip()


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except TypeError, ValueError:
        return None


def _normalize_rarity(value: Any) -> str | None:
    """Lorcast emits multi-word rarities snake-cased (e.g. "Super_rare"). Make
    them human-readable: "Super_rare" → "Super Rare", "Common" → "Common"."""
    if not value:
        return None
    return " ".join(part.capitalize() for part in str(value).replace("_", " ").split())


def normalize_card(raw: dict[str, Any]) -> dict[str, Any]:
    """Map a Lorcast catalog entry to our internal schema columns.

    Output shape matches what `lorcana_mcp.repository.InMemoryCardRepository` expects.
    Single source of truth for the field set is `_SEARCH_FIELDS` in that module.
    """
    name = (raw.get("name") or "").strip()
    version = (raw.get("version") or "").strip() or None
    full_name = f"{name} - {version}" if version else name

    # `inks` (list) is populated for Set 7+ cards (where dual-ink became possible).
    # `ink` (singular) is the legacy field, always set on pre-Set 7 cards. For
    # dual-ink cards, `ink` is sometimes null while `inks` carries both colors.
    inks = raw.get("inks")
    ink = raw.get("ink")
    if inks:
        color = list(inks)
    elif ink:
        color = [ink]
    else:
        color = []

    # Lorcast's `type` is a list. For Songs it's typically ["Action", "Song"]; we
    # join with " • " so substring filters (`card_type="song"` or
    # `card_type="action"`) both match Songs correctly.
    type_list = raw.get("type") or []
    type_str = " • ".join(type_list) if type_list else None

    classifications = raw.get("classifications") or []
    subtypes = " • ".join(classifications) if classifications else None

    # Lorcast pre-extracts keywords (e.g. ["Shift", "Evasive"]). Map to the same
    # `[{"name": kw}]` shape our existing schema uses. Lorcast's casing is
    # inconsistent in the wild (`Shift` vs `shift`, `Bodyguard` vs `bodyguard`);
    # title-case to give the repository a single canonical form to filter against.
    keywords = raw.get("keywords") or []
    abilities = [{"name": str(k).strip().title()} for k in keywords if str(k).strip()]

    set_obj = raw.get("set") or {}
    set_code = set_obj.get("code")
    set_name = set_obj.get("name")

    collector_number = raw.get("collector_number")

    return {
        "id": raw.get("id"),
        "name": name or None,
        "version": version,
        "full_name": full_name or None,
        "simple_name": _make_simple_name(full_name) or None,
        "cost": raw.get("cost"),
        "inkwell": raw.get("inkwell"),
        "strength": raw.get("strength"),
        "willpower": raw.get("willpower"),
        "color": color,
        "type": type_str,
        "full_text": raw.get("text"),
        "flavor_text": raw.get("flavor_text") or None,
        "lore": raw.get("lore"),
        "set_code": set_code,
        "set_name": set_name,
        "number": _safe_int(collector_number),
        "rarity": _normalize_rarity(raw.get("rarity")),
        "subtypes": subtypes,
        "abilities": abilities,
    }


def _card_dedupe_key(raw: dict[str, Any]) -> str:
    if raw.get("id"):
        return str(raw["id"])
    set_obj = raw.get("set") or {}
    return f"{set_obj.get('code', '')}|{raw.get('collector_number', '')}|{raw.get('name', '')}|{raw.get('version', '')}"


# Fields that identify a specific printing rather than the gameplay card itself.
# These get collected into the per-card `printings` array during consolidation.
# Kept minimal on purpose: callers only need to know which sets / rarities /
# collector numbers exist for a card. Per-printing image URLs and internal
# Lorcast IDs would balloon JSON / TOON output without answering any query the
# model has actually wanted to make.
_PRINTING_FIELDS = (
    "set_code",
    "set_name",
    "number",
    "rarity",
)


def _printing_sort_key(card: dict[str, Any]) -> tuple:
    """Sort printings so the earliest expansion-set printing is canonical.

    Numeric set codes ("1".."12") rank ahead of non-numeric promo codes
    ("P1", "P2", "C2", "DIS", etc.). Within a set, lower collector number
    wins. Falls back to id for deterministic ordering across runs.
    """
    set_code = str(card.get("set_code") or "")
    try:
        set_rank: tuple = (0, int(set_code))
    except ValueError:
        set_rank = (1, set_code)
    number = card.get("number")
    return (set_rank, number if number is not None else 10**9, str(card.get("id") or ""))


def consolidate_by_full_name(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse multiple printings of the same card into one entry.

    Each output card has top-level gameplay fields from its canonical (earliest
    expansion-set) printing, plus a `printings` array carrying per-printing
    details for every printing — including the canonical one — so callers can
    answer printing-level questions ("which sets is this in?", "is there an
    Enchanted version?") without losing any data.
    """
    groups: dict[str, list[dict[str, Any]]] = {}
    for card in cards:
        full_name = card.get("full_name")
        if not full_name:
            continue
        groups.setdefault(full_name, []).append(card)

    consolidated: list[dict[str, Any]] = []
    for full_name, printings in groups.items():
        printings_sorted = sorted(printings, key=_printing_sort_key)
        canonical = printings_sorted[0]
        entry = {**canonical}
        entry["printings"] = [{f: p.get(f) for f in _PRINTING_FIELDS} for p in printings_sorted]
        consolidated.append(entry)
    return consolidated


def fetch_all_normalized_cards() -> list[dict[str, Any]]:
    sets = fetch_sets()
    seen: dict[str, dict[str, Any]] = {}

    for i, set_obj in enumerate(sets, start=1):
        code = str(set_obj.get("code") or "")
        name = set_obj.get("name", code)
        if not code:
            logger.warning("Skipping set with no code: %r", set_obj)
            continue

        logger.info("[%d/%d] Fetching set %s: %s", i, len(sets), code, name)
        for raw in fetch_cards_for_set(code):
            seen[_card_dedupe_key(raw)] = raw

        time.sleep(REQUEST_DELAY_SECONDS)

    normalized = [normalize_card(raw) for raw in seen.values()]
    return consolidate_by_full_name(normalized)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_path", help="Path to write the normalized cards JSON list")
    args = parser.parse_args(argv[1:])

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    cards = fetch_all_normalized_cards()
    Path(args.output_path).write_text(json.dumps(cards, ensure_ascii=False), encoding="utf-8")
    logger.info("Wrote %d normalized cards to %s", len(cards), args.output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
