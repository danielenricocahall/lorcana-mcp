from unittest.mock import MagicMock, patch

import pytest

from lorcana_mcp.client import LorcanaApiClient
from lorcana_mcp.config import LorcanaConfig


def test_fetch_cards_returns_the_published_list_unchanged():
    """The published JSON is already in our internal schema; client just passes it through."""
    cards = [
        {"id": "crd_a", "name": "Mickey Mouse", "full_name": "Mickey Mouse - Brave Little Tailor"},
        {"id": "crd_b", "name": "Elsa", "full_name": "Elsa - Spirit of Winter"},
    ]
    fake_response = MagicMock()
    fake_response.json.return_value = cards
    fake_response.raise_for_status.return_value = None

    client = LorcanaApiClient(LorcanaConfig())
    with patch("lorcana_mcp.client.requests.get", return_value=fake_response):
        out = client.fetch_cards()

    assert out == cards


def test_fetch_cards_rejects_non_list_response():
    """Defend against a stale gh-pages snapshot still in the legacy bucket-grouped shape."""
    fake_response = MagicMock()
    fake_response.json.return_value = {"cards": {"characters": []}}
    fake_response.raise_for_status.return_value = None

    client = LorcanaApiClient(LorcanaConfig())
    with patch("lorcana_mcp.client.requests.get", return_value=fake_response):
        with pytest.raises(ValueError, match="JSON list of normalized cards"):
            client.fetch_cards()
