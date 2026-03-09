from __future__ import annotations

import threading
from contextlib import asynccontextmanager
from typing import Any

from fastmcp import FastMCP

from lorcana_mcp.client import LorcanaApiClient
from lorcana_mcp.config import LorcanaConfig
from lorcana_mcp.embeddings import ChromaCardIndex
from lorcana_mcp.repository import (
    SQLiteCardRepository,
)

_SQLITE_READY_TIMEOUT = 45.0  # seconds to wait for API fetch + SQLite load
_NOT_READY_MSG = "Server is still loading card data, please try again in a moment."
_SEMANTIC_NOT_READY_MSG = "Semantic index is still building, please try again in a moment."


def _build_repository(config: LorcanaConfig):
    if config.storage_backend == "sqlite":
        return SQLiteCardRepository(config.db_path)


def create_server() -> FastMCP:
    config = LorcanaConfig()
    config.validate()

    api_client = LorcanaApiClient(config)
    repository = SQLiteCardRepository(config.db_path)
    chroma_index = ChromaCardIndex(config.chroma_path)

    _sqlite_ready = threading.Event()
    _chroma_ready = threading.Event()
    _startup_state: dict[str, Any] = {
        "loaded_count": 0,
        "loaded_from_cache": False,
        "fetch_on_startup": True,
        "error": None,
    }

    def _background_startup() -> None:
        try:
            fetch_on_startup = True
            if not config.refresh_on_startup and config.skip_if_db_exists and repository.has_cards():
                fetch_on_startup = False
                _startup_state["loaded_from_cache"] = True

            _startup_state["fetch_on_startup"] = fetch_on_startup

            if fetch_on_startup:
                cards = api_client.fetch_cards()

                sqlite_exc: list[Exception] = []
                chroma_exc: list[Exception] = []

                def _load_sqlite() -> None:
                    try:
                        _startup_state["loaded_count"] = repository.load_cards(cards)
                    except Exception as e:
                        sqlite_exc.append(e)
                    finally:
                        _sqlite_ready.set()

                def _hydrate_chroma() -> None:
                    try:
                        chroma_index.hydrate(cards)
                    except Exception as e:
                        chroma_exc.append(e)
                    finally:
                        _chroma_ready.set()

                t_sqlite = threading.Thread(target=_load_sqlite, daemon=True)
                t_chroma = threading.Thread(target=_hydrate_chroma, daemon=True)
                t_sqlite.start()
                t_chroma.start()
                t_sqlite.join()
                t_chroma.join()

                if sqlite_exc:
                    raise sqlite_exc[0]
                if chroma_exc:
                    raise chroma_exc[0]
            else:
                _startup_state["loaded_count"] = repository.total_cards()
                _sqlite_ready.set()
                if not chroma_index.is_hydrated():
                    all_cards = repository.search(limit=9999)
                    chroma_index.hydrate(all_cards)
                _chroma_ready.set()

        except Exception as e:
            _startup_state["error"] = e
            _sqlite_ready.set()
            _chroma_ready.set()

    @asynccontextmanager
    async def lifespan(server: FastMCP):
        t = threading.Thread(target=_background_startup, daemon=True)
        t.start()
        yield
        t.join()

    def _require_sqlite() -> None:
        if not _sqlite_ready.wait(timeout=_SQLITE_READY_TIMEOUT):
            raise RuntimeError(_NOT_READY_MSG)
        if _startup_state["error"]:
            raise RuntimeError(f"Startup failed: {_startup_state['error']}")

    mcp = FastMCP(
        name="lorcana-mcp",
        instructions=(
            "Use this server to search and aggregate Disney Lorcana cards. "
            "Valid color names: ruby, sapphire, emerald, amber, amethyst, steel. "
            "\n\nTOOL SELECTION GUIDE:\n"
            "- semantic_search_cards: PREFER THIS for any natural-language or intent-based query — "
            "'cards that bounce characters', 'cheap aggressive questers', 'good control cards', "
            "'cards with draw effects', 'tanky support characters'. Use it whenever the query "
            "describes a concept, play-pattern, or role rather than exact field values.\n"
            "- search_cards: Use ONLY when filtering by exact/known field values — specific name, "
            "exact color, cost range, rarity, inkwell status, attack/defence/lore thresholds, "
            "or body text keyword. Not suited for concept or intent queries.\n"
            "- count_cards: Use when the user wants a count, not card details.\n"
            "- color_distribution, rarity_breakdown, ink_curve_stats, top_traits, set_distribution: "
            "Use for aggregate/breakdown questions.\n"
            "Note: card data loads in the background at startup; tools will wait briefly if still loading."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    @mcp.tool(
        description=(
            "Filter Lorcana cards by exact or ranged field values. Use ONLY when you have specific "
            "filter criteria: name substring, color, cost range, rarity, inkwell, attack/defence/lore "
            "thresholds, or a known ability keyword in body_text (e.g. 'Evasive', 'Singer 5'). "
            "NOT suitable for concept or intent queries — use semantic_search_cards for those. "
            "Color must be one of: ruby, sapphire, emerald, amber, amethyst, steel. "
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
        _require_sqlite()
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
        _require_sqlite()
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
        _require_sqlite()
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
        _require_sqlite()
        return repository.count_by(field)

    @mcp.tool(description="Return card counts by ink cost.")
    def ink_curve_stats() -> dict[str, int]:
        _require_sqlite()
        return repository.count_by("cost")

    @mcp.tool(description="Return most common traits.")
    def top_traits(limit: int = 10) -> dict[str, int]:
        _require_sqlite()
        return repository.top_traits(limit=limit)

    @mcp.tool(description="Return card count per color (ruby, sapphire, emerald, amber, amethyst, steel).")
    def color_distribution() -> dict[str, int]:
        _require_sqlite()
        return repository.color_distribution()

    @mcp.tool(description="Return card distribution by rarity.")
    def rarity_breakdown() -> dict[str, int]:
        _require_sqlite()
        return repository.count_by("rarity")

    @mcp.tool(description="Return card distribution by set id.")
    def set_distribution() -> dict[str, int]:
        _require_sqlite()
        return repository.count_by("card_set_id")

    @mcp.tool(
        description=(
            "PRIMARY discovery tool for Lorcana cards. Use this for any natural-language or "
            "intent-based query — it understands concepts, play-patterns, and roles. Examples: "
            "'cards that return characters to hand', 'cheap high-lore questers', "
            "'cards that draw and then discard', 'tanky bodyguards', 'aggressive cheap attackers', "
            "'support cards that ready allies', 'cards with cost reduction'. "
            "Prefer this over search_cards whenever the query is not filtering by an exact field value. "
            "Optionally pre-filter by color (ruby/sapphire/emerald/amber/amethyst/steel) or rarity."
        )
    )
    def semantic_search_cards(
        query: str,
        n_results: int = 10,
        color: str | None = None,
        rarity: str | None = None,
    ) -> list[dict[str, Any]] | dict[str, str]:
        if not _chroma_ready.is_set():
            return {"status": "not_ready", "message": _SEMANTIC_NOT_READY_MSG}
        if _startup_state["error"]:
            raise RuntimeError(f"Startup failed: {_startup_state['error']}")
        card_ids = chroma_index.search(query, n_results=n_results, color=color, rarity=rarity)
        return [card for card_id in card_ids if (card := repository.get_by_id(card_id)) is not None]

    @mcp.tool(description="Show startup metadata for this server instance.")
    def server_status() -> dict[str, Any]:
        return {
            "api_url": config.api_url,
            "storage_backend": config.storage_backend,
            "loaded_cards": _startup_state["loaded_count"],
            "db_path": str(config.db_path),
            "refresh_on_startup": config.refresh_on_startup,
            "skip_if_db_exists": config.skip_if_db_exists,
            "loaded_from_cache": _startup_state["loaded_from_cache"],
            "sqlite_ready": _sqlite_ready.is_set(),
            "chroma_ready": _chroma_ready.is_set(),
        }

    return mcp
