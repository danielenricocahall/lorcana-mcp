"""Tests for the Lorcast → internal-schema normalizer.

The pipeline runs in CI; the normalizer is the load-bearing piece. Verify it
produces the field set the runtime repository expects, with correct shapes for
the cases that have actually surprised us in the data (dual-ink, songs as a
multi-type list, pre-Set 7 cards with no `inks` field, etc.).
"""

from __future__ import annotations

from data_pipeline.fetch_cards import consolidate_by_full_name, normalize_card

CHARACTER_RAW = {
    "id": "crd_a",
    "name": "Mickey Mouse",
    "version": "Brave Little Tailor",
    "collector_number": "115",
    "cost": 8,
    "inkwell": True,
    "strength": 5,
    "willpower": 5,
    "lore": 4,
    "ink": "Amber",
    "inks": None,
    "type": ["Character"],
    "text": "Whenever this character quests, gain 2 lore.",
    "flavor_text": "Tailor of the brave.",
    "rarity": "Legendary",
    "set": {"code": "1", "id": "set_1", "name": "The First Chapter"},
    "classifications": ["Storyborn", "Hero"],
    "keywords": [],
}

DUAL_INK_RAW = {
    "id": "crd_dual",
    "name": "Anna",
    "version": "Ice Breaker",
    "collector_number": "5",
    "cost": 4,
    "inkwell": True,
    "strength": 3,
    "willpower": 4,
    "lore": 2,
    "ink": None,  # Lorcast leaves `ink` null on actual dual-ink cards.
    "inks": ["Amethyst", "Sapphire"],
    "type": ["Character"],
    "text": "Dual-ink test.",
    "rarity": "Rare",
    "set": {"code": "P2", "name": "Promo 2"},
    "classifications": ["Storyborn"],
    "keywords": [],
}

SONG_RAW = {
    "id": "crd_song",
    "name": "Let It Go",
    "version": None,
    "collector_number": "12",
    "cost": 5,
    "inkwell": True,
    "ink": "Amethyst",
    "inks": None,
    "type": ["Action", "Song"],
    "text": "(A character with cost 5 or more can {E} to sing this song for free.)\nEach opponent loses 2 lore.",
    "rarity": "Rare",
    "set": {"code": "1", "name": "The First Chapter"},
    "classifications": [],
    "keywords": [],
}

KEYWORDS_RAW = {
    "id": "crd_kw",
    "name": "Stitch",
    "version": "Carefree Surfer",
    "collector_number": "99",
    "cost": 3,
    "inkwell": True,
    "strength": 2,
    "willpower": 4,
    "lore": 1,
    "ink": "Ruby",
    "inks": None,
    "type": ["Character"],
    "text": "Evasive (Only characters with Evasive can challenge this character.)\nRush",
    "rarity": "Common",
    "set": {"code": "1", "name": "The First Chapter"},
    "classifications": ["Storyborn", "Hero"],
    "keywords": ["Evasive", "Rush"],
}


def test_normalize_character_basic_fields():
    out = normalize_card(CHARACTER_RAW)
    assert out["id"] == "crd_a"
    assert out["name"] == "Mickey Mouse"
    assert out["version"] == "Brave Little Tailor"
    assert out["full_name"] == "Mickey Mouse - Brave Little Tailor"
    assert out["simple_name"] == "mickey mouse brave little tailor"
    assert out["cost"] == 8
    assert out["inkwell"] is True
    assert out["strength"] == 5
    assert out["willpower"] == 5
    assert out["lore"] == 4
    assert out["color"] == ["Amber"]
    assert out["type"] == "Character"
    assert out["full_text"] == "Whenever this character quests, gain 2 lore."
    assert out["flavor_text"] == "Tailor of the brave."
    assert out["rarity"] == "Legendary"
    assert out["set_code"] == "1"
    assert out["set_name"] == "The First Chapter"
    assert out["number"] == 115
    assert out["subtypes"] == "Storyborn • Hero"
    assert out["abilities"] == []


def test_normalize_dual_ink_uses_inks_list_with_both_colors():
    out = normalize_card(DUAL_INK_RAW)
    # `ink` is null on the raw card; `inks` carries both colors. Pre-Set 7 cards
    # would do the inverse (ink populated, inks null) — both shapes must work.
    assert out["color"] == ["Amethyst", "Sapphire"]


def test_normalize_song_type_joins_action_and_song_so_substring_filters_match_either():
    out = normalize_card(SONG_RAW)
    # Songs come in as ["Action", "Song"]. Joining preserves both so card_type filters
    # for "song" or "action" both match (Songs are a subtype of Action).
    assert out["type"] == "Action • Song"
    # No subtitle → full_name is just the name.
    assert out["full_name"] == "Let It Go"
    assert out["version"] is None


def test_normalize_keywords_become_abilities_entries():
    out = normalize_card(KEYWORDS_RAW)
    assert out["abilities"] == [{"name": "Evasive"}, {"name": "Rush"}]


def test_normalize_keyword_casing_is_canonicalized():
    # Lorcast occasionally emits lowercase keywords ("shift", "bodyguard")
    # alongside the proper-cased forms. Title-case at pipeline time so the
    # repository sees a single canonical name to filter against.
    out = normalize_card({**KEYWORDS_RAW, "keywords": ["shift", "EVASIVE", "bodyguard", "Sing Together"]})
    assert out["abilities"] == [
        {"name": "Shift"},
        {"name": "Evasive"},
        {"name": "Bodyguard"},
        {"name": "Sing Together"},
    ]
    # Whitespace and empty entries are dropped.
    out = normalize_card({**KEYWORDS_RAW, "keywords": ["  Rush  ", "", "  "]})
    assert out["abilities"] == [{"name": "Rush"}]


def test_normalize_handles_missing_optional_fields():
    minimal = {
        "id": "crd_min",
        "name": "Test",
        "type": ["Action"],
        "text": "do a thing",
        "rarity": "Common",
        "set": {"code": "1"},
        # No version, classifications, keywords, ink/inks, etc.
    }
    out = normalize_card(minimal)
    assert out["full_name"] == "Test"
    assert out["version"] is None
    assert out["color"] == []
    assert out["subtypes"] is None
    assert out["abilities"] == []
    assert out["set_name"] is None
    assert out["number"] is None  # No collector_number → None.


def test_normalize_handles_non_numeric_collector_number_for_promos():
    promo = {**CHARACTER_RAW, "collector_number": "P1-3"}
    out = normalize_card(promo)
    assert out["number"] is None  # Can't parse "P1-3" as int — surface None rather than raising.


def test_normalize_humanizes_snake_cased_rarity():
    # Lorcast emits "Super_rare" with an underscore. Make it human-readable.
    out = normalize_card({**CHARACTER_RAW, "rarity": "Super_rare"})
    assert out["rarity"] == "Super Rare"
    # Single-word rarities pass through unchanged.
    assert normalize_card({**CHARACTER_RAW, "rarity": "Common"})["rarity"] == "Common"
    # Already-spaced multi-word rarities don't get double-titled.
    assert normalize_card({**CHARACTER_RAW, "rarity": "Super Rare"})["rarity"] == "Super Rare"
    # Missing/None pass through.
    assert normalize_card({**CHARACTER_RAW, "rarity": None})["rarity"] is None


# ---- consolidate_by_full_name ----


def _normalized(*, full_name, set_code, number, rarity, **extra):
    """Build a normalized-card-shaped dict for consolidation tests without going through Lorcast."""
    return {
        "id": f"crd_{set_code}_{number}",
        "name": full_name.split(" - ")[0] if " - " in full_name else full_name,
        "version": full_name.split(" - ")[1] if " - " in full_name else None,
        "full_name": full_name,
        "simple_name": full_name.lower(),
        "cost": 3,
        "inkwell": True,
        "color": ["Ruby"],
        "type": "Character",
        "full_text": "test",
        "set_code": str(set_code),
        "set_name": f"Set {set_code}",
        "number": number,
        "rarity": rarity,
        **extra,
    }


def test_consolidate_single_printing_yields_single_entry_with_one_printing():
    cards = [_normalized(full_name="Mickey Mouse - Brave Little Tailor", set_code="1", number=115, rarity="Legendary")]
    out = consolidate_by_full_name(cards)
    assert len(out) == 1
    assert out[0]["full_name"] == "Mickey Mouse - Brave Little Tailor"
    assert len(out[0]["printings"]) == 1
    assert out[0]["printings"][0]["set_code"] == "1"
    assert out[0]["printings"][0]["rarity"] == "Legendary"


def test_consolidate_picks_earliest_expansion_set_as_canonical():
    # Same card printed in Set 9 (rare), Set 9 Enchanted, and a Gateway promo.
    # Canonical should be the Set 9 rare (numeric set, lowest collector number).
    cards = [
        _normalized(full_name="Ariel - Adventurous Collector", set_code="9", number=10, rarity="Super Rare"),
        _normalized(full_name="Ariel - Adventurous Collector", set_code="9", number=210, rarity="Enchanted"),
        _normalized(full_name="Ariel - Adventurous Collector", set_code="P3", number=1, rarity="Super Rare"),
    ]
    out = consolidate_by_full_name(cards)
    assert len(out) == 1
    consolidated = out[0]
    # Canonical (top-level) is the Set 9 rare with the lowest collector number.
    assert consolidated["set_code"] == "9"
    assert consolidated["rarity"] == "Super Rare"
    assert consolidated["number"] == 10
    # All three printings preserved, in canonical order.
    set_codes = [p["set_code"] for p in consolidated["printings"]]
    assert set_codes == ["9", "9", "P3"]
    rarities = [p["rarity"] for p in consolidated["printings"]]
    assert rarities == ["Super Rare", "Enchanted", "Super Rare"]


def test_consolidate_groups_separate_cards_separately():
    cards = [
        _normalized(full_name="Card A", set_code="1", number=1, rarity="Common"),
        _normalized(full_name="Card B", set_code="1", number=2, rarity="Common"),
        _normalized(full_name="Card A", set_code="2", number=50, rarity="Rare"),  # reprint
    ]
    out = consolidate_by_full_name(cards)
    by_name = {c["full_name"]: c for c in out}
    assert set(by_name.keys()) == {"Card A", "Card B"}
    assert len(by_name["Card A"]["printings"]) == 2
    assert len(by_name["Card B"]["printings"]) == 1


def test_consolidate_skips_entries_with_no_full_name():
    cards = [
        _normalized(full_name="Real Card", set_code="1", number=1, rarity="Common"),
        {**_normalized(full_name="Real Card", set_code="1", number=1, rarity="Common"), "full_name": None},
    ]
    out = consolidate_by_full_name(cards)
    assert len(out) == 1  # The None-full_name entry is dropped.
