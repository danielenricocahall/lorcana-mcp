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


# ---- printings array: cross-printing filter and aggregate semantics ----


# A card with three printings: canonical Set 9 Super Rare, plus an Enchanted
# variant in the same set, plus a Gateway promo. Top-level fields reflect the
# canonical printing; `printings` carries all three.
ARIEL_WITH_PRINTINGS = {
    "id": "crd_ariel_9",
    "name": "Ariel",
    "version": "Adventurous Collector",
    "full_name": "Ariel - Adventurous Collector",
    "simple_name": "ariel adventurous collector",
    "cost": 4,
    "inkwell": True,
    "rarity": "Super Rare",  # canonical
    "color": ["Ruby"],
    "subtypes": "Storyborn • Hero • Princess",
    "set_code": "9",  # canonical
    "type": "Character",
    "strength": 3,
    "willpower": 4,
    "lore": 2,
    "full_text": "Test text",
    "printings": [
        {"id": "crd_ariel_9", "set_code": "9", "rarity": "Super Rare"},
        {"id": "crd_ariel_9_e", "set_code": "9", "rarity": "Enchanted"},
        {"id": "crd_ariel_p3", "set_code": "P3", "rarity": "Super Rare"},
    ],
}


@pytest.fixture
def repo_with_printings():
    r = InMemoryCardRepository()
    r.load_cards([ARIEL_WITH_PRINTINGS])
    return r


def test_rarity_filter_matches_any_printing_not_just_canonical(repo_with_printings):
    # Canonical rarity is "Super Rare", but Ariel also has an Enchanted printing.
    # rarity="Enchanted" should still find her.
    assert len(repo_with_printings.search(rarity="Enchanted")) == 1
    assert len(repo_with_printings.search(rarity="Super Rare")) == 1
    # Rarities not in any printing don't match.
    assert repo_with_printings.search(rarity="Common") == []


def test_set_code_filter_matches_any_printing_not_just_canonical(repo_with_printings):
    # Canonical set is 9, but Ariel also has a P3 (Gateway) printing.
    assert len(repo_with_printings.search(set_code="9")) == 1
    assert len(repo_with_printings.search(set_code="P3")) == 1
    assert repo_with_printings.search(set_code="1") == []


def test_count_by_aggregates_per_printing_for_set_code_and_rarity(repo_with_printings):
    # Three printings: Set 9 (Super Rare) + Set 9 (Enchanted) + Set P3 (Super Rare).
    set_counts = repo_with_printings.count_by("set_code")
    assert set_counts == {"9": 2, "P3": 1}
    rarity_counts = repo_with_printings.count_by("rarity")
    assert rarity_counts == {"Super Rare": 2, "Enchanted": 1}


def test_legacy_cards_without_printings_array_still_work(repo):
    # The original fixture cards have no `printings` field. Filters should
    # fall back to the top-level set_code/rarity transparently.
    assert len(repo.search(set_code="1")) == 2  # Mickey + Let It Go
    assert len(repo.search(rarity="Legendary")) == 1  # Elsa
    assert repo.count_by("rarity") == {"Common": 2, "Legendary": 1, "Rare": 2}
