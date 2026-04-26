from unittest.mock import MagicMock, patch

from lorcana_mcp.client import LorcanaApiClient, _normalize_card
from lorcana_mcp.config import LorcanaConfig

CHARACTER_RAW = {
    "abilities": [],
    "author": "Cam Kendell",
    "card_identifier": "1/204 EN 12",
    "card_sets": ["set12"],
    "culture_invariant_id": 2716,
    "flavor_text": '"I bet Dad never caught any flowers like this!"',
    "ink_convertible": False,
    "ink_cost": 2,
    "magic_ink_colors": ["AMBER"],
    "name": "Gosalyn Mallard",
    "quest_value": 1,
    "rarity": "COMMON",
    "rules_text": (
        "\\Heroic Intervention\\ When you play this character, you may ready chosen character with cost 2 or less."
    ),
    "searchable_keywords": ["Darkwing Duck"],
    "strength": 2,
    "subtitle": "The Quiverwing Quack",
    "subtypes": ["Dreamborn", "Super", "Hero"],
    "thumbnail_url": "https://example.test/thumb.jpg",
    "variants": [
        {"detail_image_url": "https://example.test/regular.jpg", "variant_id": "Regular"},
        {
            "detail_image_url": "https://example.test/foil.jpg",
            "foil_mask_url": "https://example.test/mask.jpg",
            "foil_type": "Silver",
            "variant_id": "Foiled",
        },
    ],
    "willpower": 3,
}

ACTION_RAW = {
    "abilities": [],
    "author": "Hedvig H-S",
    "card_identifier": "28/204 EN 12",
    "card_sets": ["set12"],
    "culture_invariant_id": 2743,
    "flavor_text": "",
    "ink_convertible": True,
    "ink_cost": 2,
    "magic_ink_colors": ["AMBER"],
    "name": "Ranger Team-Up",
    "rarity": "UNCOMMON",
    "rules_text": "Chosen character gets +{S} equal to their {W} this turn.",
    "searchable_keywords": ["Rescue Rangers"],
    "subtypes": [],
    "thumbnail_url": "https://example.test/action_thumb.jpg",
    "variants": [{"detail_image_url": "https://example.test/action_regular.jpg", "variant_id": "Regular"}],
}

LOCATION_RAW = {
    "abilities": [],
    "author": "Jiahui Eva Gao",
    "card_identifier": "34/204 EN 12",
    "card_sets": ["set12"],
    "culture_invariant_id": 2749,
    "flavor_text": "",
    "ink_convertible": True,
    "ink_cost": 3,
    "magic_ink_colors": ["AMBER"],
    "move_cost": 2,
    "name": "Andy's Room",
    "quest_value": 1,
    "rarity": "RARE",
    "rules_text": "\\Andy's Favorite\\ While you have only 1 character here, they get +2 {W} and +1 {L}.",
    "searchable_keywords": ["Toy Story"],
    "subtitle": "Home Base",
    "subtypes": [],
    "thumbnail_url": "https://example.test/loc_thumb.jpg",
    "variants": [{"detail_image_url": "https://example.test/loc_regular.jpg", "variant_id": "Regular"}],
    "willpower": 8,
}

DUAL_INK_RAW = {
    "author": "Some Artist",
    "card_identifier": "5/204 EN 7",
    "card_sets": ["set7"],
    "culture_invariant_id": 9999,
    "ink_convertible": True,
    "ink_cost": 4,
    "magic_ink_colors": ["RUBY", "SAPPHIRE"],
    "name": "Test Card",
    "quest_value": 2,
    "rarity": "RARE",
    "rules_text": "Dual-ink test card.",
    "subtitle": "Dual Threat",
    "subtypes": ["Storyborn"],
    "strength": 3,
    "thumbnail_url": "https://example.test/dual_thumb.jpg",
    "variants": [],
    "willpower": 4,
}


def test_normalize_character():
    out = _normalize_card(CHARACTER_RAW, "Character")
    assert out["id"] == 2716
    assert out["name"] == "Gosalyn Mallard"
    assert out["version"] == "The Quiverwing Quack"
    assert out["full_name"] == "Gosalyn Mallard - The Quiverwing Quack"
    assert out["simple_name"] == "gosalyn mallard the quiverwing quack"
    assert out["cost"] == 2
    assert out["inkwell"] is False
    assert out["strength"] == 2
    assert out["willpower"] == 3
    assert out["color"] == ["Amber"]
    assert out["type"] == "Character"
    assert out["lore"] == 1
    assert out["rarity"] == "Common"
    assert out["set_code"] == "12"
    assert out["number"] == 1
    assert out["story"] == "Darkwing Duck"
    assert out["subtypes"] == "Dreamborn • Super • Hero"
    assert out["artists"] == "Cam Kendell"
    assert out["full_identifier"] == "1/204 • EN • 12"


def test_normalize_strips_ability_markers_from_full_text():
    out = _normalize_card(CHARACTER_RAW, "Character")
    # Backslash markers around ability names are removed from full_text.
    assert out["full_text"].startswith("Heroic Intervention When you play")
    assert "\\" not in out["full_text"]


def test_normalize_extracts_ability_names():
    out = _normalize_card(CHARACTER_RAW, "Character")
    assert out["abilities"] == [{"name": "Heroic Intervention"}]


def test_normalize_no_abilities_when_no_markers():
    out = _normalize_card(ACTION_RAW, "Action")
    assert out["abilities"] == []


def test_normalize_picks_regular_variant_for_image_full():
    out = _normalize_card(CHARACTER_RAW, "Character")
    assert out["image_full"] == "https://example.test/regular.jpg"
    assert out["image_thumbnail"] == "https://example.test/thumb.jpg"


def test_normalize_falls_back_to_first_variant_when_no_regular():
    raw = {**CHARACTER_RAW, "variants": [{"detail_image_url": "https://example.test/only.jpg", "variant_id": "Foiled"}]}
    out = _normalize_card(raw, "Character")
    assert out["image_full"] == "https://example.test/only.jpg"


def test_normalize_action_has_no_strength_or_willpower():
    out = _normalize_card(ACTION_RAW, "Action")
    assert out["type"] == "Action"
    assert out["strength"] is None
    assert out["willpower"] is None
    assert out["lore"] is None
    # Action has no subtitle; full_name is just the name.
    assert out["full_name"] == "Ranger Team-Up"
    assert out["version"] is None
    assert out["subtypes"] is None


def test_normalize_location_keeps_willpower():
    out = _normalize_card(LOCATION_RAW, "Location")
    assert out["type"] == "Location"
    assert out["willpower"] == 8
    assert out["lore"] == 1


def test_normalize_dual_ink_card_returns_both_colors():
    out = _normalize_card(DUAL_INK_RAW, "Character")
    assert out["color"] == ["Ruby", "Sapphire"]
    assert out["set_code"] == "7"


def test_fetch_cards_flattens_buckets_and_assigns_types():
    catalog = {
        "cards": {
            "characters": [CHARACTER_RAW, DUAL_INK_RAW],
            "actions": [ACTION_RAW],
            "items": [],
            "locations": [LOCATION_RAW],
        }
    }
    fake_response = MagicMock()
    fake_response.json.return_value = catalog
    fake_response.raise_for_status.return_value = None

    client = LorcanaApiClient(LorcanaConfig())
    with patch("lorcana_mcp.client.requests.get", return_value=fake_response):
        cards = client.fetch_cards()

    assert len(cards) == 4
    types = [c["type"] for c in cards]
    # Buckets are processed in order: characters, actions, items, locations.
    assert types == ["Character", "Character", "Action", "Location"]


def test_fetch_cards_rejects_non_bucket_response():
    fake_response = MagicMock()
    fake_response.json.return_value = {"cards": [CHARACTER_RAW]}  # legacy flat shape
    fake_response.raise_for_status.return_value = None

    client = LorcanaApiClient(LorcanaConfig())
    with patch("lorcana_mcp.client.requests.get", return_value=fake_response):
        try:
            client.fetch_cards()
        except ValueError as exc:
            assert "bucket-grouped" in str(exc)
        else:
            raise AssertionError("Expected ValueError for non-bucket response")
