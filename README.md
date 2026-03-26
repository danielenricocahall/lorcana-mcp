# Lorcana MCP Server
[![MCP Badge](https://lobehub.com/badge/mcp/danielenricocahall-lorcana-mcp)](https://lobehub.com/mcp/danielenricocahall-lorcana-mcp)

An MCP server for searching and aggregating Disney Lorcana cards. 

## Startup behavior
On startup, the server fetches all cards from [lorcanajson.org](https://lorcanajson.org) via a GET request to `https://lorcanajson.org/files/current/en/allCards.json`.

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
- `LORCANA_API` (default: `https://lorcanajson.org/files/current/en/allCards.json`)
- `LORCANA_STORAGE_BACKEND` (`sqlite` default, or `memory`)
- `LORCANA_DB_PATH` (default: `cards.db`)
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
- `get_card_by_id` — fetch a single card by its ID
- `aggregate_cards` — count cards grouped by any field
- `ink_curve_stats` — card counts by ink cost
- `top_traits` — most common traits across all cards
- `color_distribution` — card count per color
- `rarity_breakdown` — card count per rarity
- `set_distribution` — card count per set
- `server_status` — startup metadata (backend, card count, config)
