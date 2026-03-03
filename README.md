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

### Docker process (Claude Desktop-style)
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

### Via the Claude CLI (global)
```shell
  claude mcp add --scope user \
    -e LORCANA_STORAGE_BACKEND=sqlite \
    -e LORCANA_DB_PATH=/data/cards.db \
    -e LORCANA_SKIP_IF_DB_EXISTS=true \
    -- lorcana docker run --rm -i -v lorcana_mcp_data:/data lorcana-mcp:latest # or preferred way
```

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
