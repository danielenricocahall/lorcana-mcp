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

Cards are bulk inserted into `lorcana_cards` using `executemany`.

## Quick start (no clone required)

The server is published to [GHCR](https://github.com/danielenricocahall/lorcana-mcp/pkgs/container/lorcana-mcp) and the [MCP Registry](https://registry.modelcontextprotocol.io/?q=lorcana). Pull and run it directly:

```bash
docker pull ghcr.io/danielenricocahall/lorcana-mcp:1.0.0

docker run --rm -i \
  -e LORCANA_STORAGE_BACKEND=sqlite \
  -e LORCANA_DB_PATH=/data/cards.db \
  -e LORCANA_SKIP_IF_DB_EXISTS=true \
  -v lorcana_mcp_data:/data \
  ghcr.io/danielenricocahall/lorcana-mcp:1.0.0
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
docker run --rm -i \
  -e LORCANA_STORAGE_BACKEND=sqlite \
  -e LORCANA_DB_PATH=/data/cards.db \
  -v lorcana_mcp_data:/data \
  lorcana-mcp:latest
```

## Docker Compose
### Start with compose
```bash
docker compose build
docker compose run --rm -T lorcana-mcp
```

Notes:
- No port is exposed; MCP communication is over stdio.
- Use a volume (as above) to persist sqlite cache across restarts.

## Config
- `LORCANA_API` (default: `https://lorcania.com/api/cardsSearch`)
- `LORCANA_STORAGE_BACKEND` (`sqlite` default, or `memory`)
- `LORCANA_DB_PATH` (default: `cards.db`)
- `LORCANA_CHROMA_PATH` (default: `chroma_db`) — directory for the persistent semantic search index
- `LORCANA_HTTP_TIMEOUT_SECONDS` (default: `30`)
- `LORCANA_REFRESH_ON_STARTUP` (`false` default)
- `LORCANA_SKIP_IF_DB_EXISTS` (`true` default)

## MCP client setup examples


### Local process (Claude Desktop-style)
```json
{
  "mcpServers": {
    "lorcana": {
      "command": "uv",
      "args": ["run", "python", "/absolute/path/to/lorcana-mcp/main.py"],
      "env": {
        "LORCANA_STORAGE_BACKEND": "sqlite",
        "LORCANA_DB_PATH": "/absolute/path/to/lorcana-mcp/cards.db",
        "LORCANA_SKIP_IF_DB_EXISTS": "true"
      }
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
        "-e",
        "LORCANA_STORAGE_BACKEND=sqlite",
        "-e",
        "LORCANA_DB_PATH=/data/cards.db",
        "-e",
        "LORCANA_SKIP_IF_DB_EXISTS=true",
        "-v",
        "lorcana_mcp_data:/data",
        "ghcr.io/danielenricocahall/lorcana-mcp:1.0.0"
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
        "-e",
        "LORCANA_STORAGE_BACKEND=sqlite",
        "-e",
        "LORCANA_DB_PATH=/data/cards.db",
        "-e",
        "LORCANA_SKIP_IF_DB_EXISTS=true",
        "-v",
        "lorcana_mcp_data:/data",
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
  -e LORCANA_STORAGE_BACKEND=sqlite \
  -e LORCANA_DB_PATH=/data/cards.db \
  -e LORCANA_SKIP_IF_DB_EXISTS=true \
  -- lorcana docker run --rm -i -v lorcana_mcp_data:/data \
  ghcr.io/danielenricocahall/lorcana-mcp:1.0.0
```

### Via the Claude CLI — locally built
```shell
claude mcp add --scope user \
  -e LORCANA_STORAGE_BACKEND=sqlite \
  -e LORCANA_DB_PATH=/data/cards.db \
  -e LORCANA_SKIP_IF_DB_EXISTS=true \
  -- lorcana docker run --rm -i -v lorcana_mcp_data:/data lorcana-mcp:latest
```

## Example questions

Once connected to an MCP client, you can ask natural language questions like:

**Card lookup**
- "Show me all cards named Moana"
- "What does the card Maui - Hero to All do?"
- "Find all legendary amber cards"

**Deck building**
- "What are the cheapest ruby characters with at least 3 attack?"
- "Show me inkable sapphire cards that cost 4 or less"
- "Find steel characters with 5 or more defence"
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
- "Find cheap (cost 2-3) characters with high attack (4+) in steel"
- "How many cards in set 1 have Evasive and cost less than 4?"

**Semantic / concept search**
- "Find cards that return characters to hand"
- "Show me cheap high-lore questers in amethyst"
- "Cards that let you draw and then discard"
- "Tanky bodyguards with lots of willpower"
- "Cards that reduce ink costs"
- "Ruby cards that deal damage to characters"

> **Note:** The `action` (ability text) field is stored as raw HTML from the API. Keyword searches like `Evasive`, `Singer 5`, or `Reckless` work reliably since the keyword word appears verbatim, but complex phrase searches may be slightly noisy. Sanitizing the action text is a planned improvement.

## MCP tools

### Search & retrieval
- `search_cards` — filter and retrieve card objects by structured criteria (color, cost, stats, traits, body text, etc.)
- `semantic_search_cards` — find cards by natural language concept or gameplay behavior (see [Semantic search](#semantic-search))
- `count_cards` — count cards matching a filter without returning full objects
- `get_card_by_id` — fetch a single card by its ID

### Aggregations
- `aggregate_cards` — count cards grouped by any field
- `ink_curve_stats` — card counts by ink cost
- `top_traits` — most common traits across all cards
- `color_distribution` — card count per color
- `rarity_breakdown` — card count per rarity
- `set_distribution` — card count per set

### Diagnostics
- `server_status` — startup metadata (backend, card count, config)

## Semantic search

`semantic_search_cards` uses a [Chroma](https://www.trychroma.com/) vector index (persisted to `LORCANA_CHROMA_PATH`) to rank cards by similarity to a natural language query. It complements `search_cards` for queries that are hard to express as exact filters.

Each card is indexed as a document combining its name, type, color, cost/attack/willpower/lore stats, traits, and ability text. On top of that, a set of **heuristic gameplay tags** are derived and appended, so concept-level queries resolve reliably even when the exact wording differs:

| Tag | Meaning |
|---|---|
| `evasive`, `rush`, `ward`, `bodyguard`, `singer`, `challenger`, `support`, `shift`, `resist`, `reckless`, `vanish` | Keyword abilities found in card text |
| `bounce` | Returns a character to hand |
| `draw` | Draws one or more cards |
| `removal` | Banishes a character |
| `damage_dealer` | Deals direct damage |
| `heal` | Removes damage counters |
| `ready` | Readies (untaps) a character |
| `exert` | Forces an opponent's character to exert |
| `discard` | Causes a player to discard |
| `tutor` | Searches the deck for a card |
| `lore_gain` | Gains lore outside of questing |
| `scry` | Looks at the top of the deck |
| `cost_reduction` | Reduces ink cost to play cards |
| `stat_boost` | Grants +strength or +willpower to other cards |
| `ink_ramp` | Puts additional cards into the inkwell |
| `song` | Card type is Song |
| `non_inkable` | Cannot be placed in the inkwell |
| `high_quester` | Cost ≤ 2 with lore ≥ 2 |
| `efficient_quester` | Lore/cost ratio ≥ 1.0 |
| `tank` | Willpower ≥ 5 |
| `glass_cannon` | Attack ≥ 5 and willpower ≤ 2 |

**Parameters:**
- `query` *(required)* — free-text description of what you're looking for
- `n_results` — number of results to return (default: 10)
- `color` — pre-filter by color before semantic ranking (`ruby`, `sapphire`, `emerald`, `amber`, `amethyst`, `steel`)
- `rarity` — pre-filter by rarity before semantic ranking (e.g. `legendary`, `rare`, `common`)

The index is built at startup and persisted to disk, so subsequent restarts with a warm cache skip re-embedding.
