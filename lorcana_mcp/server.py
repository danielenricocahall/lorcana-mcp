from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from lorcana_mcp.client import LorcanaApiClient
from lorcana_mcp.config import LorcanaConfig
from lorcana_mcp.repository import (
    SQLiteCardRepository,
)


def _build_repository(config: LorcanaConfig):
    if config.storage_backend == "sqlite":
        return SQLiteCardRepository(config.db_path)


def create_server() -> FastMCP:
    config = LorcanaConfig()
    config.validate()

    api_client = LorcanaApiClient(config)

    loaded_from_cache = False
    fetch_on_startup = True

    repository = SQLiteCardRepository(config.db_path, initial_load=fetch_on_startup)
    if config.refresh_on_startup:
        fetch_on_startup = True
    elif config.skip_if_db_exists and repository.has_cards():
        fetch_on_startup = False
        loaded_from_cache = True


    if fetch_on_startup:
        cards = api_client.fetch_cards()
        loaded_count = repository.load_cards(cards)
    else:
        loaded_count = repository.total_cards()

    startup_mode = "fetched" if fetch_on_startup else "cached"
    mcp = FastMCP(
        name="lorcana-mcp",
        instructions=(
            "Use this server to search and aggregate Disney Lorcana cards. "
            f"Loaded {loaded_count} cards on startup using backend={config.storage_backend} "
            f"(mode={startup_mode})."
        ),
        version="0.1.0",
    )

    @mcp.tool(description="Search Lorcana cards with optional filters.")
    def search_cards(
        name: str | None = None,
        color: str | None = None,
        cost: int | None = None,
        trait: str | None = None,
        rarity: str | None = None,
        inkwell: bool | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        return repository.search(
            name=name,
            color=color,
            cost=cost,
            trait=trait,
            rarity=rarity,
            inkwell=inkwell,
            limit=limit,
        )

    @mcp.tool(description="Get a single Lorcana card by id.")
    def get_card_by_id(card_id: int) -> dict[str, Any] | None:
        return repository.get_by_id(card_id)

    @mcp.tool(
        description=(
            "Return counts grouped by a field (e.g., cost, rarity, colors, card_set_id)."
        )
    )
    def aggregate_cards(field: str) -> dict[str, int]:
        return repository.count_by(field)

    @mcp.tool(description="Return card counts by ink cost.")
    def ink_curve_stats() -> dict[str, int]:
        return repository.count_by("cost")

    @mcp.tool(description="Return most common traits.")
    def top_traits(limit: int = 10) -> dict[str, int]:
        return repository.top_traits(limit=limit)

    @mcp.tool(description="Return card distribution by color.")
    def color_distribution() -> dict[str, int]:
        return repository.color_distribution()

    @mcp.tool(description="Return card distribution by rarity.")
    def rarity_breakdown() -> dict[str, int]:
        return repository.count_by("rarity")

    @mcp.tool(description="Return card distribution by set id.")
    def set_distribution() -> dict[str, int]:
        return repository.count_by("card_set_id")

    @mcp.tool(description="Show startup metadata for this server instance.")
    def server_status() -> dict[str, Any]:
        return {
            "api_url": config.api_url,
            "storage_backend": config.storage_backend,
            "loaded_cards": loaded_count,
            "db_path": str(config.db_path),
            "refresh_on_startup": config.refresh_on_startup,
            "skip_if_db_exists": config.skip_if_db_exists,
            "loaded_from_cache": loaded_from_cache,
        }

    return mcp
