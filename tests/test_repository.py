from pathlib import Path

from lorcana_mcp.repository import SQLiteCardRepository


SAMPLE_CARDS = [
    {
        "id": 1,
        "name": "Mickey Mouse",
        "cost": 3,
        "inkwell": 1,
        "rarity": "Common",
        "color": 4,  # amber
        "colors": "4",
        "traits": '["Hero", "Captain"]',
        "card_set_id": 1,
        "type": "Character",
        "attack": 2,
        "defence": 3,
        "stars": 1,
        "action": "Evasive",
    },
    {
        "id": 2,
        "name": "Elsa",
        "cost": 5,
        "inkwell": 0,
        "rarity": "Legendary",
        "color": 5,  # amethyst
        "colors": "5",
        "traits": '["Queen"]',
        "card_set_id": 2,
        "type": "Character",
        "attack": 4,
        "defence": 4,
        "stars": 3,
        "action": "Ward",
    },
    {
        "id": 3,
        "name": "Anna",
        "cost": 2,
        "inkwell": 1,
        "rarity": "Common",
        "color": 4,  # amber
        "colors": "4",
        "traits": "Princess|Hero",
        "card_set_id": 2,
        "type": "Character",
        "attack": 1,
        "defence": 2,
        "stars": 1,
        "action": None,
    },
    {
        "id": 4,
        "name": "Let It Go",
        "cost": 4,
        "inkwell": 1,
        "rarity": "Rare",
        "color": 5,  # amethyst
        "colors": "5",
        "traits": "[]",
        "card_set_id": 1,
        "type": "Song",
        "attack": None,
        "defence": None,
        "stars": 0,
        "action": "Each opponent loses 2 lore.",
    },
]


def test_sqlite_repository_load_and_query(tmp_path: Path):
    repo = SQLiteCardRepository(tmp_path / "cards.db")
    loaded = repo.load_cards(SAMPLE_CARDS)

    assert loaded == 4
    assert repo.has_cards() is True
    assert repo.total_cards() == 4

    search_results = repo.search(name="elsa")
    assert len(search_results) == 1
    assert search_results[0]["id"] == 2

    by_id = repo.get_by_id(1)
    assert by_id is not None
    assert by_id["name"] == "Mickey Mouse"


def test_sqlite_repository_aggregations(tmp_path: Path):
    repo = SQLiteCardRepository(tmp_path / "cards.db")
    repo.load_cards(SAMPLE_CARDS)

    rarity_counts = repo.count_by("rarity")
    assert rarity_counts["Common"] == 2
    assert rarity_counts["Legendary"] == 1

    top_traits = repo.top_traits(limit=2)
    assert top_traits["Hero"] == 2

    color_distribution = repo.color_distribution()
    assert color_distribution["amber"] == 2
    assert color_distribution["amethyst"] == 2


def test_search_card_type_filter(tmp_path: Path):
    repo = SQLiteCardRepository(tmp_path / "cards.db")
    repo.load_cards(SAMPLE_CARDS)

    characters = repo.search(card_type="Character")
    assert len(characters) == 3
    assert all(c["type"] == "Character" for c in characters)

    songs = repo.search(card_type="Song")
    assert len(songs) == 1
    assert songs[0]["name"] == "Let It Go"

    # case-insensitive
    assert len(repo.search(card_type="character")) == 3


def test_count_card_type_filter(tmp_path: Path):
    repo = SQLiteCardRepository(tmp_path / "cards.db")
    repo.load_cards(SAMPLE_CARDS)

    assert repo.count(card_type="Character") == 3
    assert repo.count(card_type="Song") == 1
    assert repo.count(card_type="Item") == 0


def test_search_pagination(tmp_path: Path):
    repo = SQLiteCardRepository(tmp_path / "cards.db")
    repo.load_cards(SAMPLE_CARDS)

    page1 = repo.search(limit=2, offset=0)
    page2 = repo.search(limit=2, offset=2)

    assert len(page1) == 2
    assert len(page2) == 2
    assert {r["id"] for r in page1}.isdisjoint({r["id"] for r in page2})

    all_ids = {r["id"] for r in page1} | {r["id"] for r in page2}
    assert all_ids == {1, 2, 3, 4}


def test_search_sorting(tmp_path: Path):
    repo = SQLiteCardRepository(tmp_path / "cards.db")
    repo.load_cards(SAMPLE_CARDS)

    asc = repo.search(sort_by="cost", sort_order="asc")
    costs_asc = [r["cost"] for r in asc]
    assert costs_asc == sorted(costs_asc)

    desc = repo.search(sort_by="cost", sort_order="desc")
    costs_desc = [r["cost"] for r in desc]
    assert costs_desc == sorted(costs_desc, reverse=True)


def test_search_sort_invalid_field_falls_back_to_id(tmp_path: Path):
    repo = SQLiteCardRepository(tmp_path / "cards.db")
    repo.load_cards(SAMPLE_CARDS)

    results = repo.search(sort_by="not_a_column")
    ids = [r["id"] for r in results]
    assert ids == sorted(ids)
