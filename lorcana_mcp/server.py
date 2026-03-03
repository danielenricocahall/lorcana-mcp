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
            f"(mode={startup_mode}). "
            "Valid color names: ruby, sapphire, emerald, amber, amethyst, steel. "
            "To count cards matching a filter (e.g. 'how many ruby cards?'), use count_cards. "
            "To get a breakdown of all cards by color, use color_distribution. "
            "To retrieve card details or browse cards, use search_cards."
        ),
        version="0.1.0",
    )

    @mcp.tool(
        description=(
            "Search Lorcana cards with optional filters. Returns card objects (not counts). "
            "Color must be one of: ruby, sapphire, emerald, amber, amethyst, steel. "
            "Use min_attack/max_attack and min_defence/max_defence for stat-based queries "
            "(e.g. 'characters with 4+ attack'). Use min_cost/max_cost for cost ranges. "
            "Use body_text to search card ability text (e.g. 'Evasive', 'Singer', 'Reckless'). "
            "Use lore/min_lore/max_lore to filter by lore value (stars). "
            "Use count_cards instead if you only need a total count."
        )
    )
    def search_cards(
        name: str | None = None,
        color: str | None = None,
        cost: int | None = None,
        min_cost: int | None = None,
        max_cost: int | None = None,
        trait: str | None = None,
        rarity: str | None = None,
        inkwell: bool | None = None,
        card_set_id: int | None = None,
        min_attack: int | None = None,
        max_attack: int | None = None,
        min_defence: int | None = None,
        max_defence: int | None = None,
        body_text: str | None = None,
        lore: int | None = None,
        min_lore: int | None = None,
        max_lore: int | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        return repository.search(
            name=name,
            color=color,
            cost=cost,
            min_cost=min_cost,
            max_cost=max_cost,
            trait=trait,
            rarity=rarity,
            inkwell=inkwell,
            card_set_id=card_set_id,
            min_attack=min_attack,
            max_attack=max_attack,
            min_defence=min_defence,
            max_defence=max_defence,
            body_text=body_text,
            lore=lore,
            min_lore=min_lore,
            max_lore=max_lore,
            limit=limit,
        )

    @mcp.tool(description="Get a single Lorcana card by id.")
    def get_card_by_id(card_id: int) -> dict[str, Any] | None:
        return repository.get_by_id(card_id)

    @mcp.tool(
        description=(
            "Count cards matching the given filters. Use this for questions like "
            "'how many ruby cards are there?' or 'how many legendary inkwell cards cost 3?'. "
            "Supports stat ranges: min_attack/max_attack, min_defence/max_defence, min_cost/max_cost. "
            "Use body_text to match card ability text (e.g. 'Singer 5', 'Evasive', 'Reckless'). "
            "Use lore/min_lore/max_lore to filter by lore value (stars). "
            "Color must be one of: ruby, sapphire, emerald, amber, amethyst, steel."
        )
    )
    def count_cards(
        name: str | None = None,
        color: str | None = None,
        cost: int | None = None,
        min_cost: int | None = None,
        max_cost: int | None = None,
        trait: str | None = None,
        rarity: str | None = None,
        inkwell: bool | None = None,
        card_set_id: int | None = None,
        min_attack: int | None = None,
        max_attack: int | None = None,
        min_defence: int | None = None,
        max_defence: int | None = None,
        body_text: str | None = None,
        lore: int | None = None,
        min_lore: int | None = None,
        max_lore: int | None = None,
    ) -> int:
        return repository.count(
            name=name,
            color=color,
            cost=cost,
            min_cost=min_cost,
            max_cost=max_cost,
            trait=trait,
            rarity=rarity,
            inkwell=inkwell,
            card_set_id=card_set_id,
            min_attack=min_attack,
            max_attack=max_attack,
            min_defence=min_defence,
            max_defence=max_defence,
            body_text=body_text,
            lore=lore,
            min_lore=min_lore,
            max_lore=max_lore,
        )

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

    @mcp.tool(description="Return card count per color (ruby, sapphire, emerald, amber, amethyst, steel).")
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
