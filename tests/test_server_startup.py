import asyncio
import json

from lorcana_mcp import server


class FakeConfig:
    def __init__(self, refresh_on_startup: bool, skip_if_db_exists: bool):
        self.api_url = "https://example.test"
        self.storage_backend = "sqlite"
        self.db_path = "unused.db"
        self.refresh_on_startup = refresh_on_startup
        self.skip_if_db_exists = skip_if_db_exists

    def validate(self) -> None:
        return None


class FakeRepo:
    def __init__(self, has_cards_value: bool):
        self._has_cards = has_cards_value
        self.loaded_cards = 0

    def has_cards(self) -> bool:
        return self._has_cards

    def total_cards(self) -> int:
        return 42

    def load_cards(self, cards):
        self.loaded_cards = len(cards)
        return self.loaded_cards

    def search(self, **kwargs):
        return []

    def get_by_id(self, card_id: int):
        return None

    def count_by(self, field: str):
        return {}

    def top_traits(self, limit: int = 10):
        return {}

    def color_distribution(self):
        return {}


class FakeApiClient:
    def __init__(self, _config):
        self.called = False

    def fetch_cards(self):
        self.called = True
        return [{"id": 1}, {"id": 2}]


def _extract_json_content(result):
    text = result.content[0].text
    return json.loads(text)


def test_server_uses_cached_sqlite_when_allowed(monkeypatch):
    repo = FakeRepo(has_cards_value=True)
    api = FakeApiClient(None)

    monkeypatch.setattr(server, "LorcanaConfig", lambda: FakeConfig(False, True))
    monkeypatch.setattr(server, "SQLiteCardRepository", lambda *args, **kwargs: repo)
    monkeypatch.setattr(server, "LorcanaApiClient", lambda _cfg: api)

    mcp = server.create_server()
    status = asyncio.run(mcp.call_tool("server_status", {}))
    payload = _extract_json_content(status)

    assert api.called is False
    assert payload["loaded_from_cache"] is True
    assert payload["loaded_cards"] == 42


def test_server_refresh_forces_fetch(monkeypatch):
    repo = FakeRepo(has_cards_value=True)
    api = FakeApiClient(None)

    monkeypatch.setattr(server, "LorcanaConfig", lambda: FakeConfig(True, True))
    monkeypatch.setattr(server, "SQLiteCardRepository", lambda *args, **kwargs: repo)
    monkeypatch.setattr(server, "LorcanaApiClient", lambda _cfg: api)

    mcp = server.create_server()
    status = asyncio.run(mcp.call_tool("server_status", {}))
    payload = _extract_json_content(status)

    assert api.called is True
    assert payload["loaded_from_cache"] is False
    assert payload["loaded_cards"] == 2
