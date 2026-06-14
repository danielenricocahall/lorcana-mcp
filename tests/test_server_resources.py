import asyncio
import json

import pytest

from lorcana_mcp import server
from lorcana_mcp.repository import InMemoryCardRepository
from lorcana_mcp.rules import LORCANA_INK_COLORS, LORCANA_KEYWORDS, LORCANA_RULES

SAMPLE_CARDS = [
    {"id": "crd_1", "name": "Elsa", "full_name": "Elsa - Spirit of Winter", "cost": 8},
]


class FakeConfig:
    api_url = "https://example.test"
    cache_path = "unused.json"
    refresh_on_startup = False
    skip_if_db_exists = True


class FakeApiClient:
    def __init__(self, _config):
        pass

    def fetch_cards(self):  # pragma: no cover - cache is used, so this shouldn't run
        raise AssertionError("network fetch should not happen when cache has cards")


@pytest.fixture
def mcp(monkeypatch):
    repo = InMemoryCardRepository()
    repo.load_cards(SAMPLE_CARDS)
    monkeypatch.setattr(server, "LorcanaConfig", lambda: FakeConfig())
    monkeypatch.setattr(server, "InMemoryCardRepository", lambda *a, **k: repo)
    monkeypatch.setattr(server, "LorcanaApiClient", lambda _c: FakeApiClient(None))
    return server.create_server()


def _read(mcp, uri):
    return asyncio.run(mcp.read_resource(uri)).contents[0].content


def test_resources_are_registered(mcp):
    uris = {str(r.uri) for r in asyncio.run(mcp.list_resources())}
    assert {"lorcana://rules", "lorcana://keywords", "lorcana://colors"} <= uris


def test_rules_resource_returns_full_rules(mcp):
    assert _read(mcp, "lorcana://rules") == LORCANA_RULES


def test_keywords_resource_returns_glossary(mcp):
    body = _read(mcp, "lorcana://keywords")
    assert body == LORCANA_KEYWORDS
    assert "**Bodyguard**" in body and "**Ward**" in body


def test_colors_resource_lists_six_inks(mcp):
    payload = json.loads(_read(mcp, "lorcana://colors"))
    assert payload["colors"] == LORCANA_INK_COLORS
    assert len(payload["colors"]) == 6
    assert payload["max_per_deck"] == 2


def test_card_resource_resolves_by_full_name(mcp):
    payload = json.loads(_read(mcp, "lorcana://card/Elsa - Spirit of Winter"))
    assert payload["full_name"] == "Elsa - Spirit of Winter"
    assert payload["cost"] == 8


def test_card_resource_unknown_name_errors(mcp):
    with pytest.raises(Exception, match="No card found"):
        _read(mcp, "lorcana://card/Not A Real Card")
