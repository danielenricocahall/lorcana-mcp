import asyncio
import json

from lorcana_mcp import server
from tests.test_server_startup import FakeApiClient, FakeConfig, FakeRepo


def _extract_text(result):
    return result.content[0].text


def test_search_cards_response_format_toon_returns_string(monkeypatch):
    repo = FakeRepo(has_cards_value=True)
    monkeypatch.setattr(server, "LorcanaConfig", lambda: FakeConfig(False, True))
    monkeypatch.setattr(server, "InMemoryCardRepository", lambda *a, **k: repo)
    monkeypatch.setattr(server, "LorcanaApiClient", lambda _cfg: FakeApiClient(None))

    repo.search = lambda **kwargs: [
        {"id": 1, "name": "Mickey", "cost": 3},
        {"id": 2, "name": "Elsa", "cost": 5},
    ]

    mcp = server.create_server()
    result = asyncio.run(mcp.call_tool("search_cards", {"response_format": "toon"}))
    text = _extract_text(result)

    assert text.startswith("cards[2]"), text
    assert "{id,name,cost}" in text
    assert "Mickey" in text and "Elsa" in text


def test_search_cards_default_format_returns_json(monkeypatch):
    repo = FakeRepo(has_cards_value=True)
    monkeypatch.setattr(server, "LorcanaConfig", lambda: FakeConfig(False, True))
    monkeypatch.setattr(server, "InMemoryCardRepository", lambda *a, **k: repo)
    monkeypatch.setattr(server, "LorcanaApiClient", lambda _cfg: FakeApiClient(None))

    sample = [{"id": 1, "name": "Mickey", "cost": 3}]
    repo.search = lambda **kwargs: sample

    mcp = server.create_server()
    result = asyncio.run(mcp.call_tool("search_cards", {}))
    payload = json.loads(_extract_text(result))

    assert payload == sample
