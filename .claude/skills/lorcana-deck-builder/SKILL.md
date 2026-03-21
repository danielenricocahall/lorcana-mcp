---
description: Build and analyze Disney Lorcana decks using the lorcana-mcp server tools
---

# Lorcana Deck Builder

You have access to the `lorcana-mcp` MCP server. Use it to help users build and analyze Lorcana decks.

## Deck Rules

- A legal deck contains exactly **60 cards**.
- Maximum **2 colors** (ink colors) per deck.
- Maximum **4 copies** of any single card (by name).
- Cards marked `inkwell: false` are **non-inkable** and cannot be used for ink.

## Workflow

### 1. Clarify intent
Ask the user for:
- Preferred color(s): ruby, sapphire, emerald, amber, amethyst, or steel
- Playstyle: aggressive (rush), control, lore-race (quest-focused), or midrange
- Any specific characters or synergies they want to build around

### 2. Analyze the card pool
Use these tools to explore:
- `search_cards` — find cards by color, cost, trait, rarity, or body text
- `count_cards` — confirm how many options exist for a filter
- `ink_curve_stats` — understand the overall mana curve
- `top_traits` — discover common trait synergies (e.g. Princess, Pirate, Hero)
- `color_distribution` — see total cards per color

### 3. Build the curve
A balanced 60-card deck typically needs:
- **10–14 cards at cost 1–2** (early plays / ink targets)
- **16–20 cards at cost 3–4** (midgame)
- **10–14 cards at cost 5–6** (late-game threats)
- **6–10 cards at cost 7+** (finishers, use sparingly)

Aim for **~20 inkable cards** to ensure consistent ink development.

### 4. Present the deck list
Format the final list as:

```
## Deck Name (Color1 / Color2)

### Characters (N)
- 4x Card Name (Cost) [Traits]

### Actions (N)
- 3x Card Name (Cost)

### Items (N)
- 2x Card Name (Cost)

### Songs (N)
- 4x Card Name (Cost)

Total: 60 cards
```

### 5. Explain key synergies
After the list, briefly describe:
- The win condition (how the deck wins)
- 2–3 core synergies (trait combos, singer/song pairs, keyword interactions)
- Key inkable vs non-inkable balance
