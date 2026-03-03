from pathlib import Path

from lorcana_mcp.repository import SQLiteCardRepository


SAMPLE_CARDS = [
    {
        "id": 1,
        "name": "Mickey Mouse",
        "cost": 3,
        "inkwell": 1,
        "rarity": "Common",
        "colors": "Amber",
        "traits": '["Hero", "Captain"]',
        "card_set_id": 1,
    },
    {
        "id": 2,
        "name": "Elsa",
        "cost": 5,
        "inkwell": 0,
        "rarity": "Legendary",
        "colors": "Amethyst",
        "traits": '["Queen"]',
        "card_set_id": 2,
    },
    {
        "id": 3,
        "name": "Anna",
        "cost": 2,
        "inkwell": 1,
        "rarity": "Common",
        "colors": "Amber",
        "traits": "Princess|Hero",
        "card_set_id": 2,
    },
]


def test_sqlite_repository_load_and_query(tmp_path: Path):
    repo = SQLiteCardRepository(tmp_path / "cards.db")
    loaded = repo.load_cards(SAMPLE_CARDS)

    assert loaded == 3
    assert repo.has_cards() is True
    assert repo.total_cards() == 3

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
    assert color_distribution["Amber"] == 2
    assert color_distribution["Amethyst"] == 1
