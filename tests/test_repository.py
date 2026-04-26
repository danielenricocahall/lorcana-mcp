from pathlib import Path

import pytest

from lorcana_mcp.repository import InMemoryCardRepository


@pytest.fixture
def repo():
    r = InMemoryCardRepository()
    r.load_cards(SAMPLE_CARDS)
    return r


SAMPLE_CARDS = [
    {
        "id": 1,
        "name": "Mickey Mouse",
        "version": "Brave Little Tailor",
        "full_name": "Mickey Mouse - Brave Little Tailor",
        "simple_name": "mickey mouse brave little tailor",
        "cost": 3,
        "inkwell": 1,
        "rarity": "Common",
        "color": ["Amber"],
        "subtypes": "Hero • Captain",
        "set_code": "1",
        "type": "Character",
        "strength": 2,
        "willpower": 3,
        "lore": 1,
        "full_text": "Evasive",
        "story": "Mickey & Friends",
    },
    {
        "id": 2,
        "name": "Elsa",
        "version": "Spirit of Winter",
        "full_name": "Elsa - Spirit of Winter",
        "simple_name": "elsa spirit of winter",
        "cost": 5,
        "inkwell": 0,
        "rarity": "Legendary",
        "color": ["Amethyst"],
        "subtypes": "Storyborn • Queen",
        "set_code": "2",
        "type": "Character",
        "strength": 4,
        "willpower": 4,
        "lore": 3,
        "full_text": "Ward",
        "story": "Frozen",
    },
    {
        "id": 3,
        "name": "Anna",
        "version": "Heir to Arendelle",
        "full_name": "Anna - Heir to Arendelle",
        "simple_name": "anna heir to arendelle",
        "cost": 2,
        "inkwell": 1,
        "rarity": "Common",
        "color": ["Amber"],
        "subtypes": "Storyborn • Princess • Hero",
        "set_code": "2",
        "type": "Character",
        "strength": 1,
        "willpower": 2,
        "lore": 1,
        "full_text": None,
        "story": "Frozen",
    },
    {
        "id": 4,
        "name": "Let It Go",
        "version": None,
        "full_name": "Let It Go",
        "simple_name": "let it go",
        "cost": 4,
        "inkwell": 1,
        "rarity": "Rare",
        "color": ["Amethyst"],
        "subtypes": None,
        "set_code": "1",
        "type": "Action",
        "strength": None,
        "willpower": None,
        "lore": 0,
        "full_text": "Each opponent loses 2 lore.",
        "story": "Frozen",
    },
    {
        "id": 5,
        "name": "Pongo",
        "version": "Ol' Rascal",
        "full_name": "Pongo - Ol' Rascal",
        "simple_name": "pongo ol rascal",
        "cost": 4,
        "inkwell": 1,
        "rarity": "Rare",
        "color": ["Amber", "Amethyst"],
        "subtypes": "Storyborn • Hero",
        "set_code": "7",
        "type": "Character",
        "strength": 3,
        "willpower": 4,
        "lore": 2,
        "full_text": "Bond of Loyalty",
        "story": "101 Dalmatians",
    },
]


def test_repository_load_and_query(repo):
    assert repo.has_cards is True
    assert repo.total_cards == 5

    search_results = repo.search(name="elsa")
    assert len(search_results) == 1
    assert search_results[0]["id"] == 2


def test_color_filter_includes_dual_ink_cards(repo):
    amber_results = repo.search(color="amber")
    amber_ids = {c["id"] for c in amber_results}
    # Mickey, Anna are pure Amber; Pongo is Amber/Amethyst dual-ink and counts too.
    assert amber_ids == {1, 3, 5}

    amethyst_results = repo.search(color="amethyst")
    amethyst_ids = {c["id"] for c in amethyst_results}
    # Elsa, Let It Go are pure Amethyst; Pongo is dual-ink and counts here too.
    assert amethyst_ids == {2, 4, 5}

    # Sapphire is in no card; should match nothing.
    assert repo.search(color="sapphire") == []


def test_find_by_full_name(repo):
    hit = repo.find_by_full_name("Mickey Mouse - Brave Little Tailor")
    assert hit is not None
    assert hit["id"] == 1

    case_insensitive = repo.find_by_full_name("elsa - spirit of winter")
    assert case_insensitive is not None
    assert case_insensitive["id"] == 2

    surrounded_by_whitespace = repo.find_by_full_name("  Anna - Heir to Arendelle  ")
    assert surrounded_by_whitespace is not None
    assert surrounded_by_whitespace["id"] == 3

    assert repo.find_by_full_name("Not A Real Card") is None


def test_repository_aggregations(repo):
    rarity_counts = repo.count_by("rarity")
    assert rarity_counts["Common"] == 2
    assert rarity_counts["Legendary"] == 1
    assert rarity_counts["Rare"] == 2

    top_traits = repo.top_traits(limit=3)
    assert top_traits["Hero"] == 3  # Mickey, Anna, Pongo

    # Dual-ink Pongo contributes to both Amber and Amethyst.
    color_distribution = repo.color_distribution()
    assert color_distribution["amber"] == 3
    assert color_distribution["amethyst"] == 3

    # count_by("color") flattens the list and matches color_distribution.
    color_counts = repo.count_by("color")
    assert color_counts["Amber"] == 3
    assert color_counts["Amethyst"] == 3


def test_search_card_type_filter(repo):
    characters = repo.search(card_type="character")
    assert len(characters) == 4
    assert all(c["type"] == "Character" for c in characters)

    actions = repo.search(card_type="action")
    assert len(actions) == 1
    assert actions[0]["name"] == "Let It Go"

    assert len(repo.search(card_type="Character")) == 4


def test_search_story_filter_is_case_insensitive_substring(repo):
    frozen = repo.search(story="Frozen")
    assert {c["id"] for c in frozen} == {2, 3, 4}

    # Substring + case-insensitive: "frozen" matches "Frozen".
    assert {c["id"] for c in repo.search(story="frozen")} == {2, 3, 4}

    # Story is preserved on search output (it's in _SEARCH_FIELDS).
    elsa = next(c for c in frozen if c["id"] == 2)
    assert elsa["story"] == "Frozen"

    assert repo.search(story="Mulan") == []


def test_count_story_filter(repo):
    assert repo.count(story="Frozen") == 3
    assert repo.count(story="101 Dalmatians") == 1
    assert repo.count(story="Mulan") == 0


def test_count_card_type_filter(repo):
    assert repo.count(card_type="character") == 4
    assert repo.count(card_type="action") == 1
    assert repo.count(card_type="item") == 0


def test_search_pagination(repo):
    page1 = repo.search(limit=3, offset=0)
    page2 = repo.search(limit=3, offset=3)

    assert len(page1) == 3
    assert len(page2) == 2
    assert {r["id"] for r in page1}.isdisjoint({r["id"] for r in page2})

    all_ids = {r["id"] for r in page1} | {r["id"] for r in page2}
    assert all_ids == {1, 2, 3, 4, 5}


def test_search_sorting(repo):
    asc = repo.search(sort_by="cost", sort_order="asc")
    costs_asc = [r["cost"] for r in asc]
    assert costs_asc == sorted(costs_asc)

    desc = repo.search(sort_by="cost", sort_order="desc")
    costs_desc = [r["cost"] for r in desc]
    assert costs_desc == sorted(costs_desc, reverse=True)


def test_search_sort_invalid_field_falls_back_to_id(repo):
    results = repo.search(sort_by="not_a_column")
    ids = [r["id"] for r in results]
    assert ids == sorted(ids)


def test_in_memory_cache_persistence(tmp_path: Path):
    cache = tmp_path / "cards.json"
    repo = InMemoryCardRepository(cache_path=cache)
    repo.load_cards(SAMPLE_CARDS)
    assert cache.exists()

    repo2 = InMemoryCardRepository(cache_path=cache)
    assert repo2.has_cards is True
    assert repo2.total_cards == 5
    mickey = repo2.search(name="mickey")
    assert len(mickey) == 1
    assert mickey[0]["name"] == "Mickey Mouse"
