# Lorcana MCP Server
[![MCP Badge](https://lobehub.com/badge/mcp/danielenricocahall-lorcana-mcp)](https://lobehub.com/mcp/danielenricocahall-lorcana-mcp)

An MCP server for searching and aggregating Disney Lorcana cards. 

## Startup behavior
On startup, the server fetches all cards from [lorcanajson.org](https://lorcanajson.org) via a GET request to `https://lorcanajson.org/files/current/en/allCards.json`.

Cards are kept in-memory as a Python list for fast filtering. With ~2,700 cards this is lightweight and requires no external database. A local JSON file cache (`LORCANA_CACHE_PATH`, default `cards.json`) lets the server skip the API fetch on subsequent startups.

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
- `LORCANA_API` (default: `https://lorcanajson.org/files/current/en/allCards.json`)
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

> **Note:** Keyword searches like `Evasive`, `Singer 5`, or `Reckless` match against the `full_text` field and work reliably since keywords appear verbatim in card text.

## MCP tools
- `search_cards` — filter and retrieve card objects
- `count_cards` — count cards matching a filter without returning full objects
- `aggregate_cards` — count cards grouped by any field
- `ink_curve_stats` — card counts by ink cost
- `top_traits` — most common traits across all cards
- `color_distribution` — card count per color
- `rarity_breakdown` — card count per rarity
- `set_distribution` — card count per set
- `server_status` — startup metadata (card count, config)
