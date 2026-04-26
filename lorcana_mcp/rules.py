"""Disney Lorcana game rules for MCP server instructions."""

LORCANA_RULES = """
## Disney Lorcana Game Rules

### Win Condition
First player to reach 20 lore wins.

### Card Text Symbols
Card `full_text` strings use these symbols. Decode them when reading abilities:
- `{E}` — exert (rotate the card sideways; marks it as used until your next Ready Step).
  Used as a cost, e.g. `{E} —` means "exert this card to:".
- `{I}` — ink (the resource paid from your inkwell). E.g. `2 {I}` means "pay 2 ink".
- `{S}` — Strength.
- `{L}` — Lore.
- `{W}` — Willpower.

### Deck Building
- Minimum 60 cards per deck. 60 is the standard size; there is no maximum, but
  larger decks dilute the chance of drawing any specific card.
- Maximum 4 copies of any card (matched by full name).
- Maximum 2 ink colors per deck (Amber, Amethyst, Emerald, Ruby, Sapphire, Steel).
- **Dual-ink cards** (introduced in Set 7) have two ink colors. To include a dual-ink card in
  your deck, the deck MUST contain both of that card's colors. A dual-ink card cannot go in a
  deck that only uses one of its colors (e.g., a Ruby/Sapphire dual-ink card requires a
  Ruby+Sapphire deck). Dual-ink cards do not allow a third color — the 2-color limit still applies.

### Game Setup
- Each player draws 7 cards. Before the first turn, each player may mulligan: put any number
  of cards on the bottom of their deck, then draw that many (once only, no shuffle).
- First player skips their draw step on turn 1.

### Turn Structure

**Beginning Phase (in order):**
1. Ready Step - un-exert all your cards.
2. Set Step - resolve "at the start of your turn" triggers. Locations passively gain lore here.
3. Draw Step - draw 1 card (first player skips this on turn 1).

**Main Phase (any order, as many actions as able):**
- Optionally add one inkable card face-down to your inkwell (at most once per turn).
- Play a card by exerting inkwell cards equal to its cost.
- Quest with a ready character (exert to gain lore equal to its lore value).
- Challenge with a ready character (exert to fight an opponent's exerted character).
- Use character or item abilities.
- Move a character to a location (pay the location's move cost).

### Ink System
- Your inkwell is your resource pool. Only cards with the inkwell icon are inkable.
- Exert inkwell cards to pay costs. They ready during your Ready Step.
- Cards added to the inkwell are placed face-down and remain hidden — your opponent never sees
  what you've inked.

### Summoning Sickness ("The Ink Is Drying")
- Characters CANNOT quest, challenge, or use exert-based abilities on the turn they are played.
- Rush is the only exception: Rush characters can challenge (but not quest) on the turn they are played.
- Shift bypasses summoning sickness if the character underneath was already in play from a previous turn.
- Items are NOT subject to summoning sickness — they can be used immediately.
- Locations are NOT subject to summoning sickness — they passively gain lore starting on your next Set Step.

### Questing
- Exert a ready character to gain lore equal to its lore value.
- The character stays exerted until your next Ready Step (vulnerable to challenges).

### Challenging
- Exert a ready character to challenge an opponent's EXERTED character.
- You can only challenge exerted characters (unless an ability says otherwise).
- Locations can also be challenged at any time — see Card Types → Location for details.
- Both characters deal simultaneous damage equal to their Strength.
- Damage >= Willpower = banished (sent to discard pile).
- Damage from abilities (e.g., "deal 2 damage to chosen character") also causes banishing at damage >= Willpower.
- Damage persists between turns and is not removed during the Ready Step.

### Card Types

**Character** - Has Strength, Willpower, and Lore. Can quest and challenge. Subject to summoning sickness.
**Action** - One-time effect, then discarded. Actions (including Songs) can only be played on
  your own turn during your Main Phase. There is no per-turn limit on how many actions you can
  play (unlike inking, which is once per turn).
**Song** - Subtype of Action. Can be played by paying its ink cost normally OR sung for free by an
  eligible character. **Singing eligibility (this is the rule that's easy to miss):**
  - **Default rule (no keyword required):** ANY character whose own ink cost is greater than or
    equal to the song's cost can exert to sing it for free. A 4-cost character can sing any song
    costing 4 or less. A 5-cost character can sing any song costing 5 or less. Etc.
  - **Singer N** (keyword) extends this: a character with `Singer N` can sing songs costing up to N
    *regardless of the character's own cost* — useful on cheap characters.
  - **Sing Together N** (keyword on the song itself): multiple of your characters can sing the song
    together if their combined cost ≥ N.
  - **Voiceless** (keyword) prevents a character from singing at all.
  - In every case, the singing character(s) must be ready and not have summoning sickness.
  **Bottom line:** the threshold for singing a song is the song's cost, not the presence of a
  Singer keyword.
**Item** - Stays in play. No summoning sickness. Cannot quest or challenge, and cannot be challenged.
  Items can have passive abilities or activated abilities that require exerting the item (e.g., "Exert
  this item to give a character +1 lore this turn"). Exerting an item has no downside beyond the item
  being unavailable until your next Ready Step.
**Location** - Stays in play. Has Willpower, Lore, and a Move Cost.
  - Locations have NO ready/exerted state — they are always played horizontally and stay that way.
  - Locations passively gain lore equal to their lore value during the Set Step of your Beginning Phase
    (no exertion needed). Some locations have 0 lore and provide other benefits instead.
  - Pay a location's move cost to move a character there. A character can be at one location at a time.
  - Opponents can challenge a location at any time (since locations are never "ready" to protect them).
    The attacker deals Strength damage but the location deals none back.
  - Location banished at damage >= Willpower; characters there remain in play but lose location bonuses.

### Reading Card Text
Card abilities follow a few common patterns. Decoding them correctly is more important than
memorizing every keyword.

**Triggered abilities** fire automatically when their condition is met. The controller of the
ability resolves it (chooses targets, makes decisions).
- *"When you play this character..."* — fires on entry to play. Every play of the card triggers
  this; "play" is the only way cards enter play in Lorcana.
- *"Whenever this character quests / challenges / is banished..."* — fires every time the
  condition occurs.
- *"At the start of your turn..."* — fires during your Set Step (see Beginning Phase).
- *"At the end of your turn..."* — fires as your turn ends, before your opponent's turn begins.

**Activated abilities** are written as `<cost> — <effect>` (often `{E} —` to exert, or
`<N> {I} —` to pay ink). The controller pays the cost to fire the effect.

**"Once during your turn"** (the canonical Lorcana phrasing; "once per turn" appears
occasionally) means the activated ability can be used at most once each turn.

**Targeting.** *"Chosen character/item/location"* means the controller of the ability picks a
legal target. *"Chosen opposing character"* restricts the choice to the opponent's side.
Targeting respects keywords like Ward (opponents can't target this card) and Evasive (only
Evasive characters can challenge it).

**Banish vs discard.** *Banish* sends a card from play to its owner's discard pile (the Lorcana
term for "destroyed"). *Discard* most often refers to discarding from hand. Both physically end
up in the same discard pile, but a trigger that fires on banishing does NOT fire on a hand
discard, and vice versa.

**Look at vs Reveal vs Search.**
- *"Look at the top N cards of your deck"* — private to you. Often paired with a follow-up like
  "Put one into your hand and the rest on the bottom in any order."
- *"Reveal..."* — shown to all players.
- *"Search your deck for..."* — find a specified card; the deck is then shuffled.

### Keywords

**Bodyguard** - Enters play exerted. Opponents must challenge this character before other non-Bodyguard
characters you control. (Opponents are not forced to challenge, but if they do, they must target
a Bodyguard if one is exerted.) If multiple Bodyguards are exerted, the opponent chooses which to challenge.

**Challenger +N** - Gets +N Strength when initiating a challenge (not when defending).

**Evasive** - Can only be challenged by other Evasive characters. Can challenge non-Evasive characters normally.

**Reckless** - Must challenge each turn if able. Cannot quest if a valid challenge target exists.

**Resist +N** - Takes N less damage from all sources. Minimum 0 damage.

**Rush** - Can challenge on the turn it is played (bypasses summoning sickness for challenging only, not questing).

**Shift N** - Play on top of an existing character with the same name, paying N ink instead of full cost.
Name matching uses the base name only — any "Elsa" can shift onto any other "Elsa" regardless of
subtitle/version. The shifted character inherits position (ready/exerted) and damage. If the base
character was already in play from a prior turn, the shifted character is NOT subject to summoning
sickness. Named Shift variants relax the same-name requirement: **Universal Shift** lets you shift
onto any character; **Puppy Shift** lets you shift onto any character with the Puppy trait.
Otherwise variants behave like base Shift.

**Singer N** - Lets a character sing songs costing up to N regardless of the character's own cost
(see Card Types → Song for the full singing rules, including the default rule that any character
with cost ≥ the song's cost can sing it without needing the Singer keyword).

**Sing Together N** - Keyword on the *song*. Any number of your (and your teammates', in multiplayer)
characters whose combined cost is at least N may exert together to sing this song for free. Each
participating character must be ready and not have summoning sickness.

**Support** - When questing, may add this character's Strength to another chosen character until your next turn.

**Voiceless** - Character cannot sing songs at all (overrides the default singing rule and Singer N).

**Ward** - Cannot be targeted by opponent's abilities or effects. Does NOT prevent being challenged.
AoE effects ("all characters") still affect Ward characters.

**Vanish** - When an opponent chooses this character as the target of an action, this character
is banished. Typically appears on Illusion characters and is designed to punish opponent
targeting (and to feed Illusion-tribal triggers that benefit from your characters being banished).
The action that triggered Vanish can still resolve, but with no valid target it usually fizzles.

**Boost N** - Once per turn, pay N ink to put the top card of your deck face-down under this character.
The face-down card is not in play and cannot be looked at. Cards placed underneath typically enable
the character's secondary ability (e.g., stat buffs while boosted, triggered effects on quest/challenge,
or effects that fire when a card is placed underneath). Boost costs vary (1, 2, or 3 ink).

### Additional Rules

- **Deck out:** If your deck is empty, you do not lose. You simply cannot draw. The game continues
  until a player reaches 20 lore.
- **Classification traits:** Characters have classification traits (Storyborn, Dreamborn, Floodborn)
  that may be referenced by card abilities. Floodborn characters are typically the ones with the Shift
  keyword. These traits also appear in subtypes alongside character traits (Hero, Villain, Princess, etc.).
""".strip()
