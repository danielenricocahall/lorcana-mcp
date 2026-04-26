# Lorcana MCP Server
[![MCP Badge](https://lobehub.com/badge/mcp/danielenricocahall-lorcana-mcp)](https://lobehub.com/mcp/danielenricocahall-lorcana-mcp)

An MCP server for searching and aggregating Disney Lorcana cards. 

## Startup behavior
On startup, the server fetches a JSON list of cards from `https://danielenricocahall.github.io/lorcana-mcp/allCards.json`. The snapshot is refreshed daily by `data_pipeline/fetch_cards.py`, which pulls from the [Lorcast API](https://lorcast.com/), normalizes each card into our internal schema, and publishes the list to the `gh-pages` branch. The middle layer insulates running containers from Lorcast's availability and rate limits — the runtime never calls Lorcast directly.

Cards are kept in-memory as a Python list for fast filtering. With ~2,270 unique cards (each carrying a `printings` array for its alternate sets/rarities) this is lightweight and requires no external database. A local JSON file cache (`LORCANA_CACHE_PATH`, default `cards.json`) lets the server skip the network fetch on subsequent startups.

Startup data loading is controlled by:

- `LORCANA_REFRESH_ON_STARTUP`:
  - `true`: always fetch from API and repopulate storage
  - `false`: use existing cache if available
- `LORCANA_SKIP_IF_DB_EXISTS`:
  - `true` (default): skip API fetch if the cache file already contains cards
  - `false`: fetch and repopulate

## Quick start (no clone required)

The server is published to [GHCR](https://github.com/danielenricocahall/lorcana-mcp/pkgs/container/lorcana-mcp) and the [MCP Registry](https://registry.modelcontextprotocol.io/?q=lorcana). Pull and run it directly:

```bash
docker pull ghcr.io/danielenricocahall/lorcana-mcp:latest

docker run --rm -i ghcr.io/danielenricocahall/lorcana-mcp:latest
```

To persist the card cache across container restarts, mount a volume:

```bash
docker run --rm -i \
  -e LORCANA_CACHE_PATH=/data/cards.json \
  -e LORCANA_SKIP_IF_DB_EXISTS=true \
  -v lorcana_mcp_data:/data \
  ghcr.io/danielenricocahall/lorcana-mcp:latest
```

## Run locally (stdio MCP)
```bash
uv run python main.py
```

## Docker
### Build image
```bash
docker build -t lorcana-mcp:latest .
```

### Run as stdio MCP server
```bash
docker run --rm -i lorcana-mcp:latest
```

## Docker Compose
### Start with compose
```bash
docker compose build
docker compose run --rm -T lorcana-mcp
```

Notes:
- No port is exposed; MCP communication is over stdio.
- Use a volume to persist the JSON cache across restarts.

## Config
- `LORCANA_API` (default: `https://danielenricocahall.github.io/lorcana-mcp/allCards.json`)
- `LORCANA_CACHE_PATH` (default: `cards.json`) — local file for caching fetched cards
- `LORCANA_HTTP_TIMEOUT_SECONDS` (default: `60`)
- `LORCANA_REFRESH_ON_STARTUP` (`false` default)
- `LORCANA_SKIP_IF_DB_EXISTS` (`true` default)

## MCP client setup examples


### Local process (Claude Desktop-style)
```json
{
  "mcpServers": {
    "lorcana": {
      "command": "uv",
      "args": ["run", "python", "/absolute/path/to/lorcana-mcp/main.py"]
    }
  }
}
```

### Published image — GHCR (Claude Desktop-style, no clone required)
```json
{
  "mcpServers": {
    "lorcana": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "ghcr.io/danielenricocahall/lorcana-mcp:latest"
      ]
    }
  }
}
```

### Docker process (Claude Desktop-style, locally built)
```json
{
  "mcpServers": {
    "lorcana": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "lorcana-mcp:latest"
      ]
    }
  }
}
```

### Docker Compose process (Claude Desktop-style)
```json
{
  "mcpServers": {
    "lorcana": {
      "command": "docker",
      "args": ["compose", "run", "--rm", "-T", "lorcana-mcp"]
    }
  }
}
```

### Via the Claude CLI — published image (global, no clone required)
```shell
claude mcp add --scope user \
  -- lorcana docker run --rm -i \
  ghcr.io/danielenricocahall/lorcana-mcp:latest
```

### Via the Claude CLI — locally built
```shell
claude mcp add --scope user \
  -- lorcana docker run --rm -i lorcana-mcp:latest
```

## Example questions

Once connected to an MCP client, you can ask natural language questions like:

**Card lookup**
- "Show me all cards named Moana"
- "What does the card Maui - Hero to All do?"
- "Find all legendary amber cards"

**Deck building**
- "What are the cheapest ruby characters with at least 3 strength?"
- "Show me inkable sapphire cards that cost 4 or less"
- "Find steel characters with 5 or more willpower"
- "What 3-lore characters exist in emerald?"

**Keyword & ability search**
- "How many Singer cards cost exactly 5?"
- "How many Evasive characters are there in the first set?"
- "How many ruby cards have Reckless?"
- "Find all cards with Ward in their text"
- "Show me Shift cards in amethyst"

**Stats & aggregations**
- "How many cards are in each set?"
- "What's the color distribution across all cards?"
- "What are the most common traits?"
- "Show me the ink curve — how many cards exist at each cost?"
- "How many legendary cards are inkable?"

**Cross-filter queries**
- "How many amber characters have 3 or more lore?"
- "Find cheap (cost 2-3) characters with high strength (4+) in steel"
- "How many cards in set 1 have Evasive and cost less than 4?"

> **Note:** For plain keyword queries (Evasive, Bodyguard, Shift, etc.) use the `keyword` parameter — it filters against the structured ability list and is more reliable than substring search. For value-specific queries like `Singer 5` or `Resist +2`, use `body_text` (keyword values live in the card's full text, not the ability list).

## MCP tools
- `search_cards` — filter and retrieve card objects (supports `response_format="toon"` for ~50% fewer tokens)
- `count_cards` — count cards matching a filter without returning full objects
- `aggregate_cards` — card counts grouped by `cost` (ink curve), `rarity`, `color`, `set_code`, or `type`
- `resolve_card` — fuzzy-match an informal/partial/misspelled card name to the closest cards (returns full card data)
- `top_traits` — most common traits across all cards
- `export_deck` — render a deck as a Dreamborn/Pixelborn-compatible text deck list
- `import_deck` — parse a Dreamborn/Pixelborn-style deck list, returning resolved cards plus any unresolved lines with fuzzy candidates
- `validate_deck` — check a deck against the format rules (≥60 cards, max 4 copies, ≤2 inks); returns `{legal, total_cards, inks, violations}`
- `deck_stats` — compute ink curve, color split, inkable count, and type breakdown for a deck
- `server_status` — startup metadata (card count, config)

## TOON response format

`search_cards` accepts a `response_format` argument:

- `"json"` (default) — list of card objects, unchanged from prior versions.
- `"toon"` — a [TOON](https://toonformat.org/) string with one column header line and one row per card, encoded by the [`toons`](https://github.com/alesanfra/toons) Rust-backed library (the official community reference implementation).

Example (`search_cards(name="elsa", limit=2, response_format="toon")`):

```
cards[2]{id,name,version,full_name,cost,inkwell,...}:
  1,Elsa,Spirit of Winter,Elsa - Spirit of Winter,5,false,...
  2,Elsa,Snow Queen,Elsa - Snow Queen,8,true,...
```

### Benchmark

Measured with `benchmarks/bench_toon.py` against the live ~2,270-card dataset (post-consolidation), tokenizing with tiktoken `cl100k_base` (used as a proxy for Claude's tokenizer):

| query | rows | JSON tokens | TOON tokens | Δ |
|---|---:|---:|---:|---:|
| `color="amber", limit=200` | 200 | 43,672 | 39,282 | **−10.1%** |
| `color="ruby", limit=50` | 50 | 10,446 | 9,464 | **−9.4%** |
| `card_type="action", limit=50` (sparse cols) | 50 | 10,150 | 9,265 | **−8.7%** |
| `body_text="when", limit=50` (long full_text) | 50 | 11,574 | 10,380 | **−10.3%** |
| `name="elsa", limit=20` | 14 | 3,456 | 2,925 | **−15.4%** |
| **total** |  | **79,298** | **71,316** | **−10.1%** |

Note: TOON's relative savings are smaller here than they were before the printings consolidation (pre-PR-#29 the same queries showed ~50% reductions). That gap is structural to the nested `printings` array — TOON's columnar encoding wins on the top-level fields but falls back to JSON-style encoding inside the per-printing entries, so the array dilutes the relative gain. Absolute token counts are still down meaningfully versus the equivalent count of pre-consolidation rows since each unique card is now represented once with a small printings list rather than as 1-3 separate full rows.

Reproduce with `PYTHONPATH=. uv run python benchmarks/bench_toon.py` (requires a populated `cards.json` cache).
