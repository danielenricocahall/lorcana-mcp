"""Runtime fetcher for the published Lorcana card list.

The published JSON at the configured `LORCANA_API` URL is already in our
internal schema (the `data_pipeline/fetch_cards.py` job normalizes Lorcast
data and publishes it to gh-pages). The runtime just fetches and returns
the list — no schema mapping happens here.
"""

from __future__ import annotations

from typing import Any

import requests

from lorcana_mcp.config import LorcanaConfig


class LorcanaApiClient:
    def __init__(self, config: LorcanaConfig):
        self._config = config

    def fetch_cards(self) -> list[dict[str, Any]]:
        response = requests.get(self._config.api_url, timeout=self._config.request_timeout_seconds)
        response.raise_for_status()
        cards = response.json()
        if not isinstance(cards, list):
            raise ValueError(
                f"Expected a JSON list of normalized cards from {self._config.api_url}, got {type(cards).__name__}"
            )
        return cards
