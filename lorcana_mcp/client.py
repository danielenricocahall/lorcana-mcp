from __future__ import annotations

from typing import Any

import requests

from lorcana_mcp.config import LorcanaConfig


def _normalize_card(raw: dict[str, Any]) -> dict[str, Any]:
    """Map lorcanajson.org fields to our internal schema column names."""
    images = raw.get("images") or {}
    external_links = raw.get("externalLinks") or {}
    return {
        "id": raw.get("id"),
        "name": raw.get("name"),
        "version": raw.get("version"),
        "full_name": raw.get("fullName"),
        "simple_name": raw.get("simpleName"),
        "cost": raw.get("cost"),
        "inkwell": raw.get("inkwell"),
        "strength": raw.get("strength"),
        "willpower": raw.get("willpower"),
        "color": raw.get("color"),
        "type": raw.get("type"),
        "full_text": raw.get("fullText"),
        "flavor_text": raw.get("flavorText"),
        "lore": raw.get("lore"),
        "artists": raw.get("artistsText"),
        "set_code": raw.get("setCode"),
        "number": raw.get("number"),
        "rarity": raw.get("rarity"),
        "image_full": images.get("full"),
        "image_thumbnail": images.get("thumbnail"),
        "story": raw.get("story"),
        "subtypes": raw.get("subtypesText"),
        "abilities": raw.get("abilities"),
        "full_identifier": raw.get("fullIdentifier"),
        "tcgplayer_url": external_links.get("tcgPlayerUrl"),
        "cardmarket_url": external_links.get("cardmarketUrl"),
        "cardtrader_url": external_links.get("cardTraderUrl"),
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
        results = response.json()

        if isinstance(results, list):
            return [_normalize_card(card) for card in results if isinstance(card, dict)]
        if isinstance(results, dict) and isinstance(results.get("cards"), list):
            return [_normalize_card(card) for card in results["cards"] if isinstance(card, dict)]

        raise ValueError("Unexpected Lorcana API response format.")
