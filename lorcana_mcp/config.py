from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class LorcanaConfig:
    api_url: str = os.getenv(
        "LORCANA_API",
        "https://danielenricocahall.github.io/lorcana-mcp/allCards.json",
    )
    cache_path: Path = Path(os.getenv("LORCANA_CACHE_PATH", "cards.json"))
    request_timeout_seconds: float = float(os.getenv("LORCANA_HTTP_TIMEOUT_SECONDS", "60"))
    refresh_on_startup: bool = _env_bool("LORCANA_REFRESH_ON_STARTUP", False)
    skip_if_db_exists: bool = _env_bool("LORCANA_SKIP_IF_DB_EXISTS", True)
