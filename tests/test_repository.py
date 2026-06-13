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


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("mickey", "Mickey Mouse - Brave Little Tailor"),
        ("Elsa - Spirit of Winter", "Elsa - Spirit of Winter"),
        ("let it go", "Let It Go"),
    ],
    ids=["partial-name", "exact-full-name", "song-name"],
)
def test_resolve_card_ranks_best_match_first(repo, query, expected):
    assert repo.resolve_card(query)[0]["full_name"] == expected


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("micky mouse", "Mickey Mouse - Brave Little Tailor"),
        ("ana arendelle", "Anna - Heir to Arendelle"),
    ],
    ids=["missing-letter", "doubled-letter-dropped"],
)
def test_resolve_card_tolerates_typos(repo, query, expected):
    # Fuzzy matching should recover from a misspelling, not just substring hits.
    assert repo.resolve_card(query)[0]["full_name"] == expected


def test_resolve_card_respects_limit(repo):
    assert len(repo.resolve_card("a", limit=2)) <= 2


def test_repository_aggregations(repo):
    rarity_counts = repo.count_by("rarity")
    assert rarity_counts["Common"] == 2
    assert rarity_counts["Legendary"] == 1
    assert rarity_counts["Rare"] == 2

    top_traits = repo.top_traits(limit=3)
    assert top_traits["Hero"] == 3  # Mickey, Anna, Pongo

    # Dual-ink Pongo contributes to both Amber and Amethyst — count_by flattens
    # the color list so dual-ink cards count under both buckets.
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


# ---- structured keyword filter ----


CARDS_WITH_ABILITIES = [
    {
        "id": "kw_1",
        "name": "Stitch",
        "full_name": "Stitch - Carefree Surfer",
        "cost": 3,
        "color": ["Ruby"],
        "type": "Character",
        "abilities": [{"name": "Evasive"}, {"name": "Rush"}],
    },
    {
        "id": "kw_2",
        "name": "Mickey Mouse",
        "full_name": "Mickey Mouse - Brave Little Tailor",
        "cost": 8,
        "color": ["Amber"],
        "type": "Character",
        "abilities": [{"name": "Bodyguard"}],
    },
    {
        "id": "kw_3",
        "name": "Sven",
        "full_name": "Sven - Reindeer Steed",
        "cost": 5,
        "color": ["Amber"],
        "type": "Character",
        "abilities": [{"name": "Rush"}, {"name": "Bodyguard"}],
    },
    {
        "id": "kw_4",
        "name": "Vanilla Card",
        "full_name": "Vanilla Card",
        "cost": 1,
        "color": ["Steel"],
        "type": "Action",
        "abilities": [],
    },
]


@pytest.fixture
def repo_keywords():
    r = InMemoryCardRepository()
    r.load_cards(CARDS_WITH_ABILITIES)
    return r


def test_keyword_filter_matches_cards_with_that_ability(repo_keywords):
    rush = repo_keywords.search(keyword="Rush")
    assert {c["full_name"] for c in rush} == {"Stitch - Carefree Surfer", "Sven - Reindeer Steed"}

    bodyguard = repo_keywords.search(keyword="Bodyguard")
    assert {c["full_name"] for c in bodyguard} == {
        "Mickey Mouse - Brave Little Tailor",
        "Sven - Reindeer Steed",
    }

    # Vanilla card with no abilities never matches.
    for kw in ("Rush", "Bodyguard", "Evasive"):
        assert "Vanilla Card" not in {c["full_name"] for c in repo_keywords.search(keyword=kw)}


def test_keyword_filter_is_case_insensitive(repo_keywords):
    # "evasive", "EVASIVE", "Evasive" should all hit the same card.
    expected = {"Stitch - Carefree Surfer"}
    for variant in ("Evasive", "evasive", "EVASIVE", "  Evasive  "):
        assert {c["full_name"] for c in repo_keywords.search(keyword=variant)} == expected


def test_keyword_filter_no_matches_returns_empty(repo_keywords):
    assert repo_keywords.search(keyword="Reckless") == []


def test_count_with_keyword_matches_search(repo_keywords):
    assert repo_keywords.count(keyword="Rush") == 2
    assert repo_keywords.count(keyword="Bodyguard") == 2
    assert repo_keywords.count(keyword="Evasive") == 1
    assert repo_keywords.count(keyword="Reckless") == 0


def test_keyword_combines_with_other_filters(repo_keywords):
    # Rush characters in Amber: just Sven (Stitch is Ruby).
    results = repo_keywords.search(keyword="Rush", color="amber")
    assert {c["full_name"] for c in results} == {"Sven - Reindeer Steed"}


# ---- set_name filter (case-insensitive substring; works with or without printings) ----


CARDS_WITH_SET_NAMES = [
    {
        "id": "sn_1",
        "name": "Mickey",
        "full_name": "Mickey - The Apprentice",
        "color": ["Amber"],
        "type": "Character",
        "set_code": "1",
        "set_name": "The First Chapter",
    },
    {
        "id": "sn_2",
        "name": "Anna",
        "full_name": "Anna - Heir to Arendelle",
        "color": ["Amber"],
        "type": "Character",
        # Reprint card: canonical Set 1, with a Set 12 printing too. set_name filter
        # should match against ANY printing's set_name (parallel to set_code).
        "set_code": "1",
        "set_name": "The First Chapter",
        "printings": [
            {"set_code": "1", "set_name": "The First Chapter", "rarity": "Common"},
            {"set_code": "12", "set_name": "Wilds Unknown", "rarity": "Rare"},
        ],
    },
    {
        "id": "sn_3",
        "name": "New Card",
        "full_name": "New Card - Wilds Native",
        "color": ["Steel"],
        "type": "Character",
        "set_code": "12",
        "set_name": "Wilds Unknown",
    },
]


@pytest.fixture
def repo_set_names():
    r = InMemoryCardRepository()
    r.load_cards(CARDS_WITH_SET_NAMES)
    return r


def test_set_name_filter_substring_case_insensitive(repo_set_names):
    # Exact name with proper casing.
    results = repo_set_names.search(set_name="Wilds Unknown")
    assert {c["full_name"] for c in results} == {"Anna - Heir to Arendelle", "New Card - Wilds Native"}

    # Lowercase, partial — both should still match.
    for variant in ("wilds unknown", "wilds", "  WILDS  "):
        assert {c["full_name"] for c in repo_set_names.search(set_name=variant)} == {
            "Anna - Heir to Arendelle",
            "New Card - Wilds Native",
        }


def test_set_name_filter_matches_any_printing(repo_set_names):
    # Anna's CANONICAL set_name is "The First Chapter" but she has a Wilds Unknown
    # reprint in her printings array — a set_name filter for Wilds should still hit her.
    wilds = repo_set_names.search(set_name="wilds")
    assert "Anna - Heir to Arendelle" in {c["full_name"] for c in wilds}

    first = repo_set_names.search(set_name="First Chapter")
    assert {c["full_name"] for c in first} == {"Mickey - The Apprentice", "Anna - Heir to Arendelle"}


def test_set_name_filter_no_matches_returns_empty(repo_set_names):
    assert repo_set_names.search(set_name="Ravnica") == []


def test_count_with_set_name_matches_search(repo_set_names):
    assert repo_set_names.count(set_name="Wilds Unknown") == 2
    assert repo_set_names.count(set_name="First Chapter") == 2
    assert repo_set_names.count(set_name="Ravnica") == 0
