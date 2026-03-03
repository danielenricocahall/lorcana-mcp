from __future__ import annotations

from typing import Any

import requests

from lorcana_mcp.config import LorcanaConfig

REQUEST_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json",
}

REQUEST_PAYLOAD = {
    "colors": [],
    "sets": [],
    "traits": [],
    "keywords": [],
    "costs": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    "inkwell": [],
    "rarity": [],
    "language": "English",
    "options": [],
    "sorting": "default",
}


class LorcanaApiClient:
    def __init__(self, config: LorcanaConfig):
        self._config = config

    def fetch_cards(self) -> list[dict[str, Any]]:
        response = requests.post(
            self._config.api_url,
            headers=REQUEST_HEADERS,
            json=REQUEST_PAYLOAD,
            timeout=self._config.request_timeout_seconds,
        )
        response.raise_for_status()
        results = response.json()

        if isinstance(results, dict) and isinstance(results.get("cards"), list):
            return [card for card in results["cards"] if isinstance(card, dict)]
        if isinstance(results, list):
            return [card for card in results if isinstance(card, dict)]

        raise ValueError("Unexpected Lorcana API response format.")
