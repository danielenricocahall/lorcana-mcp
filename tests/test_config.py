from lorcana_mcp.config import _env_bool


def test_env_bool_truthy(monkeypatch):
    monkeypatch.setenv("TEST_BOOL", "TrUe")
    assert _env_bool("TEST_BOOL", False) is True


def test_env_bool_default_when_missing(monkeypatch):
    monkeypatch.delenv("TEST_BOOL", raising=False)
    assert _env_bool("TEST_BOOL", True) is True
