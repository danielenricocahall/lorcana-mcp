from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import toons
from fastmcp import FastMCP

from lorcana_mcp.client import LorcanaApiClient
from lorcana_mcp.config import LorcanaConfig
from lorcana_mcp.repository import InMemoryCardRepository
from lorcana_mcp.rules import LORCANA_RULES


def _get_version() -> str:
    pyproject = Path(__file__).parent.parent / "pyproject.toml"
    return tomllib.loads(pyproject.read_text())["project"]["version"]


def _build_repository(config: LorcanaConfig) -> InMemoryCardRepository:
    return InMemoryCardRepository(config.cache_path)


def create_server() -> FastMCP:
    config = LorcanaConfig()

    api_client = LorcanaApiClient(config)

    repository = _build_repository(config)
    loaded_from_cache = not config.refresh_on_startup and config.skip_if_db_exists and repository.has_cards

    if not loaded_from_cache:
        cards = api_client.fetch_cards()
        loaded_count = repository.load_cards(cards)
    else:
        loaded_count = repository.total_cards

    startup_mode = "cached" if loaded_from_cache else "fetched"
    mcp = FastMCP(
        name="lorcana-mcp",
        instructions=(
            "Use this server to search and aggregate Disney Lorcana cards. "
            f"Loaded {loaded_count} cards on startup "
            f"(mode={startup_mode}). "
            "Valid color names: ruby, sapphire, emerald, amber, amethyst, steel. "
            "To count cards matching a filter (e.g. 'how many ruby cards?'), use count_cards. "
            "To get a breakdown of all cards by color, use color_distribution. "
            "To retrieve card details or browse cards, use search_cards.\n\n"
            f"{LORCANA_RULES}"
        ),
        version=_get_version(),
    )

    @mcp.tool(
        description=(
            "Search Lorcana cards with optional filters. Returns card objects (not counts). "
            "Color must be one of: ruby, sapphire, emerald, amber, amethyst, steel. "
            "Use card_type to filter by card type: Character, Action, Item, Song, or Location. "
            "Use min_attack/max_attack and min_defence/max_defence for stat-based queries "
            "(e.g. 'characters with 4+ strength'). Use min_cost/max_cost for cost ranges. "
            "Use body_text to search card ability text (e.g. 'Evasive', 'Singer', 'Reckless'). "
            "Use lore/min_lore/max_lore to filter by lore value. "
            "Use sort_by to order results (id, name, cost, strength, willpower, lore, rarity, set_code); "
            "use sort_order='asc' or 'desc'. "
            "Use set_code to filter by set number (e.g. '1' for The First Chapter). "
            "Use offset to paginate through results (e.g. offset=20 for the next page). "
            "Use count_cards instead if you only need a total count. "
            "Set response_format='toon' to receive a tabular TOON-encoded string instead of "
            "JSON objects (~50% fewer tokens for large result sets); default is 'json'."
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
        set_code: str | None = None,
        min_attack: int | None = None,
        max_attack: int | None = None,
        min_defence: int | None = None,
        max_defence: int | None = None,
        body_text: str | None = None,
        lore: int | None = None,
        min_lore: int | None = None,
        max_lore: int | None = None,
        card_type: str | None = None,
        limit: int = 20,
        offset: int = 0,
        sort_by: str = "id",
        sort_order: str = "asc",
        response_format: str = "json",
    ) -> list[dict[str, Any]] | str:
        rows = repository.search(
            name=name,
            color=color,
            cost=cost,
            min_cost=min_cost,
            max_cost=max_cost,
            trait=trait,
            rarity=rarity,
            inkwell=inkwell,
            set_code=set_code,
            min_attack=min_attack,
            max_attack=max_attack,
            min_defence=min_defence,
            max_defence=max_defence,
            body_text=body_text,
            lore=lore,
            min_lore=min_lore,
            max_lore=max_lore,
            card_type=card_type,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        if response_format == "toon":
            return toons.dumps({"cards": rows})
        return rows

    @mcp.tool(description="Get a single Lorcana card by id.")
    def get_card_by_id(card_id: int) -> dict[str, Any] | None:
        return repository.get_by_id(card_id)

    @mcp.tool(
        description=(
            "Count cards matching the given filters. Use this for questions like "
            "'how many ruby cards are there?' or 'how many legendary inkwell cards cost 3?'. "
            "Supports stat ranges: min_attack/max_attack, min_defence/max_defence, min_cost/max_cost. "
            "Use body_text to match card ability text (e.g. 'Singer 5', 'Evasive', 'Reckless'). "
            "Use lore/min_lore/max_lore to filter by lore value. "
            "Use card_type to filter by card type: Character, Action, Item, Song, or Location. "
            "Use set_code to filter by set number (e.g. '1' for The First Chapter). "
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
        set_code: str | None = None,
        min_attack: int | None = None,
        max_attack: int | None = None,
        min_defence: int | None = None,
        max_defence: int | None = None,
        body_text: str | None = None,
        lore: int | None = None,
        min_lore: int | None = None,
        max_lore: int | None = None,
        card_type: str | None = None,
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
            set_code=set_code,
            min_attack=min_attack,
            max_attack=max_attack,
            min_defence=min_defence,
            max_defence=max_defence,
            body_text=body_text,
            lore=lore,
            min_lore=min_lore,
            max_lore=max_lore,
            card_type=card_type,
        )

    _AGGREGABLE_FIELDS = {"cost", "rarity", "color", "set_code", "type"}

    @mcp.tool(
        description=(
            "Return card counts grouped by a field. "
            "Valid fields: cost (ink curve), rarity, color, set_code, type. "
            "Examples: aggregate_cards('cost') for the ink curve, aggregate_cards('color') for color breakdown, "
            "aggregate_cards('rarity') for rarity breakdown, aggregate_cards('set_code') for set distribution."
        )
    )
    def aggregate_cards(field: str) -> dict[str, int] | str:
        if field not in _AGGREGABLE_FIELDS:
            return f"Invalid field '{field}'. Valid fields: {', '.join(sorted(_AGGREGABLE_FIELDS))}."
        return repository.count_by(field)

    @mcp.tool(description="Return most common traits.")
    def top_traits(limit: int = 10) -> dict[str, int]:
        return repository.top_traits(limit=limit)

    @mcp.tool(
        description=(
            "Resolve an informal, partial, or misspelled card name to the closest matching cards. "
            "Returns full card data (stats, abilities, cost, etc.) for each candidate — no follow-up query needed. "
            "Use this as follows:\n"
            "- 'Tell me about / get stats for X' → call resolve_card only, use the result directly.\n"
            "- 'Find cards that synergize with / work well with X' → resolve_card to get X's traits and "
            "abilities, then use those as inputs to search_cards.\n"
            "- 'Build a deck with X' → resolve_card to identify X, then search_cards for supporting cards.\n"
            "Never call search_cards or get_card_by_id first when the user has named a specific card — "
            "resolve_card avoids failed searches and retry loops. "
            "Example: 'Maui Half Shark' resolves to 'Maui - Half-Shark' as the top result."
        )
    )
    def resolve_card(query: str, limit: int = 5) -> list[dict[str, Any]]:
        return repository.resolve_card(query, limit=limit)

    @mcp.tool(description="Show startup metadata for this server instance.")
    def server_status() -> dict[str, Any]:
        return {
            "api_url": config.api_url,
            "loaded_cards": loaded_count,
            "cache_path": str(config.cache_path),
            "refresh_on_startup": config.refresh_on_startup,
            "skip_if_db_exists": config.skip_if_db_exists,
            "loaded_from_cache": loaded_from_cache,
        }

    @mcp.prompt(
        description=(
            "Guide the user through building a legal 60-card Lorcana deck. "
            "Accepts preferred color(s) and playstyle, then uses the available "
            "search and aggregation tools to suggest a full deck list with synergy notes."
        )
    )
    def build_deck(
        colors: str,
        playstyle: str = "balanced",
    ) -> str:
        return f"""You are helping build a legal Disney Lorcana deck. Use the lorcana-mcp tools to search \
and select cards. Refer to the Lorcana game rules in the server instructions for all game mechanics, \
keywords, and deck-building constraints.

## Parameters
- Colors: {colors}
- Playstyle: {playstyle}

## Deck-Building Guidelines
- Aim for ~20 inkable cards to ensure consistent ink development each turn
- When including dual-ink cards, ensure the deck uses both of that card's colors
- Include Shift chains where possible: pick cheap base-name characters and their Floodborn Shift versions
- Characters with Bodyguard enter play exerted — factor that into tempo planning
- Remember summoning sickness: freshly played characters cannot quest or challenge (except Rush for challenges)

## Steps

1. **Explore the card pool** — use `search_cards` filtered to the requested color(s) and card_type. \
Valid card types: Character, Action, Item, Song, Location.
2. **Build the curve** — target this distribution across 60 cards:
   - Cost 1-2: 10-14 cards (early plays and ink fodder)
   - Cost 3-4: 16-20 cards (midgame)
   - Cost 5-6: 10-14 cards (late threats)
   - Cost 7+: 6-10 cards (finishers, use sparingly)
3. **Find synergies** — use `top_traits` to identify strong trait clusters. Look for:
   - Singer/Song pairs: characters with Singer can sing songs for free (body_text="Singer")
   - Shift chains: cheap base characters + their Floodborn Shift versions for tempo advantage
   - Keyword combos: Evasive (hard to remove), Bodyguard (protects key characters), Challenger (efficient removal)
   - Location value: locations with lore passively generate lore each turn without needing to exert
   - Items with activated abilities: exert-based items for repeatable effects each turn
4. **Adjust for playstyle**:
   - aggressive: favor low-cost Characters with Rush or high attack, minimize cost 6+
   - control: include removal (body_text="banish" or "damage"), Ward, and card draw
   - lore-race: prioritize high lore values (min_lore=2), Evasive Characters, Locations with lore, \
and Songs that quest
   - balanced: even curve, mix of threats and support

## Output Format

Present the final deck as:

```
## [Deck Name] ([Color1] / [Color2])

### Characters (N)
- 4x Card Name (Cost) [Traits] — one-line note on role

### Actions (N)
- Nx Card Name (Cost)

### Items (N)
- Nx Card Name (Cost)

### Songs (N)
- Nx Card Name (Cost)

### Locations (N)
- Nx Card Name (Cost)

Total: 60 cards | Inkable: N cards
```

Then add a short paragraph covering: win condition, 2-3 key synergies, and inkable balance."""

    return mcp
