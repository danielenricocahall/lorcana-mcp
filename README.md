# Disney Lorcana MCP Server
[![MCP Badge](https://lobehub.com/badge/mcp/danielenricocahall-lorcana-mcp)](https://lobehub.com/mcp/danielenricocahall-lorcana-mcp)

An MCP server that lets Claude (or any MCP client) search, analyze, and build decks for the
**Disney Lorcana TCG**. Ask for cards in plain English, get rules-checked deck validation, ink
curves and keyword breakdowns, and round-trip deck lists with Dreamborn/Pixelborn.

**2,506 unique cards** (3,192 printings including alternate arts and promos), refreshed daily.
No API key, no database, no rate limits — the server ships against a snapshot published from
our own pipeline, so it never depends on a third-party API being up at query time.

## Tools

| Tool | What it does |
|---|---|
| `search_cards` | Filter and retrieve cards by name, color, cost, rarity, type, keyword, stats, set, and body text. Supports `response_format="toon"` for ~10% fewer tokens |
| `count_cards` | Count cards matching a filter without paying for the card objects |
| `aggregate_cards` | Group counts by `cost` (ink curve), `rarity`, `color`, `set_code`, or `type` |
| `resolve_card` | Fuzzy-match an informal, partial, or misspelled card name to the closest cards |
| `top_traits` | Most common traits (Storyborn, Hero, Villain, Ally, ...) across all cards |
| `validate_deck` | Check a deck against format rules (≥60 cards, max 4 copies, ≤2 inks, dual-ink requirements); returns `{legal, total_cards, inks, violations}` |
| `deck_stats` | Ink curve, color split, inkable count, type breakdown, keyword counts, subtype counts, and per-card keyword tags |
| `import_deck` | Parse a Dreamborn/Pixelborn deck list into resolved cards, with fuzzy candidates for unresolved lines |
| `export_deck` | Render a deck back out as a Dreamborn/Pixelborn-compatible text list |
| `server_status` | Startup metadata (card count, configuration) |

## Install

### uvx (recommended — no clone, no Docker)

```bash
uvx lorcana-cards-mcp
```

Claude Desktop / `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "lorcana": {
      "command": "uvx",
      "args": ["lorcana-cards-mcp"]
    }
  }
}
```

Claude CLI:

```bash
claude mcp add --scope user -- lorcana uvx lorcana-cards-mcp
```

### pip / pipx

```bash
pipx install lorcana-cards-mcp   # then run: lorcana-cards-mcp
```

### Docker

The server is also published to [GHCR](https://github.com/danielenricocahall/lorcana-mcp/pkgs/container/lorcana-mcp)
and the [MCP Registry](https://registry.modelcontextprotocol.io/?q=lorcana).

```bash
docker run --rm -i ghcr.io/danielenricocahall/lorcana-mcp:latest
```

```json
{
  "mcpServers": {
    "lorcana": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "ghcr.io/danielenricocahall/lorcana-mcp:latest"]
    }
  }
}
```

To persist the card cache across container restarts, mount a volume:

```bash
docker run --rm -i \
  -e LORCANA_CACHE_PATH=/data/cards.json \
  -e LORCANA_SKIP_IF_DB_EXISTS=true \
  -v lorcana_mcp_data:/data \
  ghcr.io/danielenricocahall/lorcana-mcp:latest
```

### From a clone

```bash
uv run python main.py
```

```bash
docker build -t lorcana-mcp:latest .
docker run --rm -i lorcana-mcp:latest

# or via compose
docker compose build
docker compose run --rm -T lorcana-mcp
```

No port is exposed; MCP communication is over stdio.

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

## MCP prompts
- `build_deck(colors, playstyle="balanced")` — guides the model through assembling a legal Lorcana deck (60-card minimum, ≤2 inks, max 4 copies of any card) for the requested color(s) and playstyle (`aggressive` / `control` / `lore-race` / `balanced`). Uses the search/aggregate tools above plus the rules embedded in the server instructions.

## Card data & startup behavior

On startup, the server fetches a JSON list of cards from
`https://danielenricocahall.github.io/lorcana-mcp/allCards.json`. The snapshot is refreshed daily
by `data_pipeline/fetch_cards.py`, which pulls from the [Lorcast API](https://lorcast.com/),
normalizes each card into our internal schema, and publishes the list to the `gh-pages` branch.
That middle layer insulates running servers from Lorcast's availability and rate limits — the
runtime never calls Lorcast directly.

Cards are kept in memory as a Python list for fast filtering. The dataset holds **2,506 unique
cards**, each carrying a `printings` array for its alternate sets, numbers, and rarities (3,192
printings in total). Consolidating printings onto one row per card means a search for "Elsa"
returns each distinct Elsa once rather than repeating her for every promo reprint. A local JSON
file cache (`LORCANA_CACHE_PATH`, default `cards.json`) lets the server skip the network fetch on
subsequent startups.

## Config

- `LORCANA_API` (default: `https://danielenricocahall.github.io/lorcana-mcp/allCards.json`)
- `LORCANA_CACHE_PATH` (default: `cards.json`) — local file for caching fetched cards
- `LORCANA_HTTP_TIMEOUT_SECONDS` (default: `60`)
- `LORCANA_REFRESH_ON_STARTUP` (default: `false`) — `true` always fetches and repopulates storage
- `LORCANA_SKIP_IF_DB_EXISTS` (default: `true`) — `false` fetches and repopulates even if the cache is populated

## TOON response format

`search_cards` accepts a `response_format` argument:

- `"json"` (default) — list of card objects, unchanged from prior versions.
- `"toon"` — a [TOON](https://toonformat.org/) string with one column header line and one row per card, encoded by the [`toons`](https://github.com/alesanfra/toons) Rust-backed library (the official community reference implementation).

Example (`search_cards(name="elsa", limit=2, response_format="toon")`):

```
cards[2]:
  - id: crd_01c4835a62df4960bb973aeff81f2bb2
    name: Elsa
    version: Ice Maker
    full_name: Elsa - Ice Maker
    cost: 7
    ...
    printings[3]{set_code,set_name,number,rarity}:
      "7",Archazia's Island,69,Super Rare
      C2,Lorcana Challenge Year 3,2,Promo
      C2,Lorcana Challenge Year 3,6,Promo
  - id: crd_04bca46a8e2d4e9ba0fbdbfc6c99e51e
    name: Elsa
    ...
```

The outer `cards[2]:` falls back to YAML-style per-card blocks (rather than a single tabular table) because card shapes vary — Actions and Items don't carry strength/willpower/lore, for example. The inner `printings[N]{...}:` block is fully tabular since every printing has the same four fields.


### Benchmark

Measured with `benchmarks/bench_toon.py` against the live 2,506-card dataset, tokenizing with
tiktoken `cl100k_base` (used as a proxy for Claude's tokenizer):

| query | rows | JSON tokens | TOON tokens | Δ |
|---|---:|---:|---:|---:|
| `color="amber", limit=200` | 200 | 44,101 | 39,680 | **−10.0%** |
| `color="ruby", limit=50` | 50 | 10,522 | 9,519 | **−9.5%** |
| `card_type="action", limit=50` (sparse cols) | 50 | 10,154 | 9,250 | **−8.9%** |
| `body_text="when", limit=50` (long full_text) | 50 | 11,602 | 10,391 | **−10.4%** |
| `name="elsa", limit=20` | 14 | 3,488 | 2,940 | **−15.7%** |
| **total** |  | **79,867** | **71,780** | **−10.1%** |

Note: TOON's relative savings are smaller here than they were before the printings consolidation
(pre-PR-#29 the same queries showed ~50% reductions). That gap is structural to the nested
`printings` array — TOON's columnar encoding wins on the top-level fields but falls back to
JSON-style encoding inside the per-printing entries, so the array dilutes the relative gain.
Absolute token counts are still down meaningfully versus the equivalent count of pre-consolidation
rows, since each unique card is now represented once with a small printings list rather than as
1-3 separate full rows.

Reproduce with `PYTHONPATH=. uv run python benchmarks/bench_toon.py` (requires a populated
`cards.json` cache).

## Disclaimer

This is a personal, unofficial fan and engineering project. It is not affiliated with, endorsed by,
sponsored by, or reviewed by Disney, Ravensburger, or the Disney Lorcana TCG team. It is built
and distributed in accordance with Ravensburger's
[Disney Lorcana TCG Community Code](https://cdn.ravensburger.com/lorcana/community-code-en),
using only publicly available and community data sources. All Disney Lorcana TCG names, card text,
trademarks, and related intellectual property belong to Disney and Ravensburger. This project is
non-commercial and reflects my personal views only, not those of my employer.

---

<sub>MCP Registry ownership verification — the registry reads this line from the published package description to confirm this project owns the server name.</sub>

mcp-name: io.github.danielenricocahall/lorcana-mcp
