import asyncio
import json

from lorcana_mcp import server


class FakeConfig:
    def __init__(self, refresh_on_startup: bool, skip_if_db_exists: bool):
        self.api_url = "https://example.test"
        self.cache_path = "unused.json"
        self.refresh_on_startup = refresh_on_startup
        self.skip_if_db_exists = skip_if_db_exists


class FakeRepo:
    def __init__(self, has_cards_value: bool):
        self.has_cards = has_cards_value
        self.loaded_cards = 0

    @property
    def total_cards(self) -> int:
        return 42

    def load_cards(self, cards):
        self.loaded_cards = len(cards)
        return self.loaded_cards

    def search(self, **kwargs):
        return []

    def count_by(self, field: str):
        return {}

    def top_traits(self, limit: int = 10):
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


def test_server_uses_cache_when_allowed(monkeypatch):
    repo = FakeRepo(has_cards_value=True)
    api = FakeApiClient(None)

    monkeypatch.setattr(server, "LorcanaConfig", lambda: FakeConfig(False, True))
    monkeypatch.setattr(server, "InMemoryCardRepository", lambda *args, **kwargs: repo)
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
    monkeypatch.setattr(server, "InMemoryCardRepository", lambda *args, **kwargs: repo)
    monkeypatch.setattr(server, "LorcanaApiClient", lambda _cfg: api)

    mcp = server.create_server()
    status = asyncio.run(mcp.call_tool("server_status", {}))
    payload = _extract_json_content(status)

    assert api.called is True
    assert payload["loaded_from_cache"] is False
    assert payload["loaded_cards"] == 2


def test_get_version_uses_installed_distribution_metadata(monkeypatch):
    """The wheel does not ship pyproject.toml, so version lookup must not read it.

    Regression test: reading pyproject.toml by relative path raised
    FileNotFoundError on every `uvx`/`pip` install of the server.
    """
    import importlib.metadata

    from lorcana_mcp import server

    monkeypatch.setattr(importlib.metadata, "version", lambda name: "9.9.9")
    # Point the fallback at a directory with no pyproject.toml so a regression
    # to file-based lookup fails loudly instead of silently passing.
    monkeypatch.setattr(server, "__file__", "/nonexistent/lorcana_mcp/server.py")

    assert server._get_version() == "9.9.9"


def test_get_version_falls_back_to_pyproject_for_source_checkouts(monkeypatch):
    import importlib.metadata
    import tomllib
    from pathlib import Path

    from lorcana_mcp import server

    def _missing(name):
        raise importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(importlib.metadata, "version", _missing)

    expected = tomllib.loads((Path(server.__file__).parent.parent / "pyproject.toml").read_text())["project"]["version"]
    assert server._get_version() == expected


def test_version_is_consistent_across_pyproject_and_server_json():
    import json
    import tomllib
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    pyproject_version = tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"]
    manifest = json.loads((root / "server.json").read_text())

    assert manifest["version"] == pyproject_version
    for package in manifest["packages"]:
        if package["registryType"] == "pypi":
            assert package["version"] == pyproject_version
        if package["registryType"] == "oci":
            assert package["identifier"].endswith(f":{pyproject_version}")
