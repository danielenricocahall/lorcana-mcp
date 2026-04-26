"""Tests for the Lorcast → internal-schema normalizer.

The pipeline runs in CI; the normalizer is the load-bearing piece. Verify it
produces the field set the runtime repository expects, with correct shapes for
the cases that have actually surprised us in the data (dual-ink, songs as a
multi-type list, pre-Set 7 cards with no `inks` field, etc.).
"""

from __future__ import annotations

from data_pipeline.fetch_cards import normalize_card

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
    "image_uris": {"digital": {"large": "https://x/large.avif", "small": "https://x/small.avif"}},
    "classifications": ["Storyborn", "Hero"],
    "keywords": [],
    "illustrators": ["Some Artist"],
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
    "image_uris": {"digital": {"large": "https://x/dual_large.avif", "small": "https://x/dual_small.avif"}},
    "classifications": ["Storyborn"],
    "keywords": [],
    "illustrators": [],
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
    "image_uris": {"digital": {"large": "https://x/song_large.avif", "small": "https://x/song_small.avif"}},
    "classifications": [],
    "keywords": [],
    "illustrators": ["Eric Proctor"],
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
    "image_uris": {"digital": {"large": "https://x/k.avif", "small": "https://x/ks.avif"}},
    "classifications": ["Storyborn", "Hero"],
    "keywords": ["Evasive", "Rush"],
    "illustrators": [],
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
    assert out["image_full"] == "https://x/large.avif"
    assert out["image_thumbnail"] == "https://x/small.avif"
    assert out["subtypes"] == "Storyborn • Hero"
    assert out["abilities"] == []
    assert out["artists"] == "Some Artist"
    assert out["full_identifier"] == "115 • 1"


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


def test_normalize_handles_missing_optional_fields():
    minimal = {
        "id": "crd_min",
        "name": "Test",
        "type": ["Action"],
        "text": "do a thing",
        "rarity": "Common",
        "set": {"code": "1"},
        "image_uris": {},
        # No version, classifications, keywords, illustrators, ink/inks, etc.
    }
    out = normalize_card(minimal)
    assert out["full_name"] == "Test"
    assert out["version"] is None
    assert out["color"] == []
    assert out["subtypes"] is None
    assert out["abilities"] == []
    assert out["artists"] is None
    assert out["image_full"] is None
    assert out["image_thumbnail"] is None
    assert out["set_name"] is None
    assert out["number"] is None  # No collector_number → None.


def test_normalize_handles_non_numeric_collector_number_for_promos():
    promo = {**CHARACTER_RAW, "collector_number": "P1-3"}
    out = normalize_card(promo)
    assert out["number"] is None  # Can't parse "P1-3" as int.
    assert out["full_identifier"] == "P1-3 • 1"  # But still surface it as a string.
