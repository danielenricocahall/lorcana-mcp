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
    api_url: str = os.getenv("LORCANA_API", "https://lorcania.com/api/cardsSearch")
    storage_backend: str = os.getenv("LORCANA_STORAGE_BACKEND", "sqlite").strip().lower()
    db_path: Path = Path(os.getenv("LORCANA_DB_PATH", "cards.db"))
    request_timeout_seconds: float = float(os.getenv("LORCANA_HTTP_TIMEOUT_SECONDS", "30"))
    refresh_on_startup: bool = _env_bool("LORCANA_REFRESH_ON_STARTUP", False)
    skip_if_db_exists: bool = _env_bool("LORCANA_SKIP_IF_DB_EXISTS", True)

    def validate(self) -> None:
        if self.storage_backend not in {"memory", "sqlite"}:
            raise ValueError(
                "LORCANA_STORAGE_BACKEND must be either 'memory' or 'sqlite'."
            )
