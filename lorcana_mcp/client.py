from __future__ import annotations

import re
from typing import Any

import requests

from lorcana_mcp.config import LorcanaConfig

_BUCKET_TO_TYPE = {
    "characters": "Character",
    "actions": "Action",
    "items": "Item",
    "locations": "Location",
}

# Ravensburger wraps inline ability names in single backslashes,
# e.g. "\Heroic Intervention\ When you play this character...".
_ABILITY_NAME_RE = re.compile(r"\\([^\\]+)\\")
_NUMBER_RE = re.compile(r"^(\d+)/")


def _pick_image(variants: list[dict[str, Any]]) -> str | None:
    if not variants:
        return None
    for v in variants:
        if v.get("variant_id") == "Regular":
            return v.get("detail_image_url")
    return variants[0].get("detail_image_url")


def _parse_abilities(rules_text: str | None) -> list[dict[str, str]]:
    if not rules_text:
        return []
    return [{"name": match.strip()} for match in _ABILITY_NAME_RE.findall(rules_text)]


def _strip_ability_markers(rules_text: str | None) -> str | None:
    if not rules_text:
        return rules_text
    return _ABILITY_NAME_RE.sub(r"\1", rules_text)


def _parse_number(card_identifier: str | None) -> int | None:
    if not card_identifier:
        return None
    match = _NUMBER_RE.match(card_identifier)
    return int(match.group(1)) if match else None


def _make_simple_name(full_name: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", full_name.lower())).strip()


def _normalize_card(raw: dict[str, Any], card_type: str) -> dict[str, Any]:
    """Map a Ravensburger catalog entry to our internal schema columns."""
    name = (raw.get("name") or "").strip()
    subtitle = (raw.get("subtitle") or "").strip()
    full_name = f"{name} - {subtitle}" if subtitle else name

    card_sets = raw.get("card_sets") or []
    set_code = card_sets[0].removeprefix("set") if card_sets else None

    card_identifier = raw.get("card_identifier")
    full_identifier = card_identifier.replace(" ", " • ") if card_identifier else None

    keywords = raw.get("searchable_keywords") or []
    story = keywords[0] if keywords else None

    subtypes_list = raw.get("subtypes") or []
    subtypes = " • ".join(subtypes_list) if subtypes_list else None

    colors = [c.title() for c in (raw.get("magic_ink_colors") or [])]
    rarity = (raw.get("rarity") or "").title() or None
    rules_text = raw.get("rules_text")

    return {
        "id": raw.get("culture_invariant_id"),
        "name": name or None,
        "version": subtitle or None,
        "full_name": full_name or None,
        "simple_name": _make_simple_name(full_name) or None,
        "cost": raw.get("ink_cost"),
        "inkwell": raw.get("ink_convertible"),
        "strength": raw.get("strength"),
        "willpower": raw.get("willpower"),
        "color": colors,
        "type": card_type,
        "full_text": _strip_ability_markers(rules_text),
        "flavor_text": raw.get("flavor_text") or None,
        "lore": raw.get("quest_value"),
        "artists": raw.get("author"),
        "set_code": set_code,
        "number": _parse_number(card_identifier),
        "rarity": rarity,
        "image_full": _pick_image(raw.get("variants") or []),
        "image_thumbnail": raw.get("thumbnail_url"),
        "story": story,
        "subtypes": subtypes,
        "abilities": _parse_abilities(rules_text),
        "full_identifier": full_identifier,
    }


class LorcanaApiClient:
    def __init__(self, config: LorcanaConfig):
        self._config = config

    def fetch_cards(self) -> list[dict[str, Any]]:
        response = requests.get(
            self._config.api_url,
            timeout=self._config.request_timeout_seconds,
        )
        response.raise_for_status()
        catalog = response.json()

        cards_section = catalog.get("cards")
        if not isinstance(cards_section, dict):
            raise ValueError("Unexpected catalog format: 'cards' is not a bucket-grouped object.")

        out: list[dict[str, Any]] = []
        for bucket, card_type in _BUCKET_TO_TYPE.items():
            for raw in cards_section.get(bucket) or []:
                if isinstance(raw, dict):
                    out.append(_normalize_card(raw, card_type))
        return out
