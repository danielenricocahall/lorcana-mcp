# lorcana-mcp

MCP server for searching and aggregating Disney Lorcana cards.

## Startup behavior
On startup, the server sends a POST request to `https://lorcania.com/api/cardsSearch` with:

- `colors`, `sets`, `traits`, `keywords`, `inkwell`, `rarity`, `options`: empty arrays
- `costs`: `[1..10]`
- `language`: `English`
- `sorting`: `default`

The server stores cards in sqlite by default (`LORCANA_STORAGE_BACKEND=sqlite`).

Startup data loading is controlled by:

- `LORCANA_REFRESH_ON_STARTUP`:
  - `true`: always fetch from API and repopulate storage
  - `false`: may use existing sqlite cache
- `LORCANA_SKIP_IF_DB_EXISTS`:
  - only used when backend is sqlite and refresh is false
  - `true`: skip API fetch if sqlite DB already contains cards
  - `false`: fetch and repopulate sqlite

If sqlite is used, cards are bulk inserted into `lorcana_cards` using `executemany`.

## Run
```bash
uv run python main.py
```

## Config
- `LORCANA_API` (default: `https://lorcania.com/api/cardsSearch`)
- `LORCANA_STORAGE_BACKEND` (`sqlite` default, or `memory`)
- `LORCANA_DB_PATH` (default: `cards.db`)
- `LORCANA_HTTP_TIMEOUT_SECONDS` (default: `30`)
- `LORCANA_REFRESH_ON_STARTUP` (`false` default)
- `LORCANA_SKIP_IF_DB_EXISTS` (`true` default)

## MCP tools
- `search_cards`
- `get_card_by_id`
- `aggregate_cards`
- `ink_curve_stats`
- `top_traits`
- `color_distribution`
- `rarity_breakdown`
- `set_distribution`
- `server_status`
