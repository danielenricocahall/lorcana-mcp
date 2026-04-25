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
        "color": "Amber",
        "subtypes": "Hero • Captain",
        "set_code": "1",
        "type": "Character",
        "strength": 2,
        "willpower": 3,
        "lore": 1,
        "full_text": "Evasive",
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
        "color": "Amethyst",
        "subtypes": "Storyborn • Queen",
        "set_code": "2",
        "type": "Character",
        "strength": 4,
        "willpower": 4,
        "lore": 3,
        "full_text": "Ward",
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
        "color": "Amber",
        "subtypes": "Storyborn • Princess • Hero",
        "set_code": "2",
        "type": "Character",
        "strength": 1,
        "willpower": 2,
        "lore": 1,
        "full_text": None,
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
        "color": "Amethyst",
        "subtypes": None,
        "set_code": "1",
        "type": "Action",
        "strength": None,
        "willpower": None,
        "lore": 0,
        "full_text": "Each opponent loses 2 lore.",
    },
]


def test_repository_load_and_query(repo):
    assert repo.has_cards is True
    assert repo.total_cards == 4

    search_results = repo.search(name="elsa")
    assert len(search_results) == 1
    assert search_results[0]["id"] == 2


def test_repository_aggregations(repo):
    rarity_counts = repo.count_by("rarity")
    assert rarity_counts["Common"] == 2
    assert rarity_counts["Legendary"] == 1

    top_traits = repo.top_traits(limit=3)
    assert top_traits["Hero"] == 2

    color_distribution = repo.color_distribution()
    assert color_distribution["amber"] == 2
    assert color_distribution["amethyst"] == 2


def test_search_card_type_filter(repo):
    characters = repo.search(card_type="character")
    assert len(characters) == 3
    assert all(c["type"] == "Character" for c in characters)

    actions = repo.search(card_type="action")
    assert len(actions) == 1
    assert actions[0]["name"] == "Let It Go"

    assert len(repo.search(card_type="Character")) == 3


def test_count_card_type_filter(repo):
    assert repo.count(card_type="character") == 3
    assert repo.count(card_type="action") == 1
    assert repo.count(card_type="item") == 0


def test_search_pagination(repo):
    page1 = repo.search(limit=2, offset=0)
    page2 = repo.search(limit=2, offset=2)

    assert len(page1) == 2
    assert len(page2) == 2
    assert {r["id"] for r in page1}.isdisjoint({r["id"] for r in page2})

    all_ids = {r["id"] for r in page1} | {r["id"] for r in page2}
    assert all_ids == {1, 2, 3, 4}


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
    assert repo2.total_cards == 4
    mickey = repo2.search(name="mickey")
    assert len(mickey) == 1
    assert mickey[0]["name"] == "Mickey Mouse"
