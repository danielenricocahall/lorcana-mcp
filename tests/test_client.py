from lorcana_mcp.client import _normalize_card


def test_normalize_card_extracts_tcgplayer_url():
    raw = {
        "id": 1,
        "name": "Ariel",
        "fullName": "Ariel - On Human Legs",
        "externalLinks": {
            "tcgPlayerId": 494102,
            "tcgPlayerUrl": "https://www.tcgplayer.com/product/494102",
        },
    }
    assert _normalize_card(raw)["tcgplayer_url"] == "https://www.tcgplayer.com/product/494102"


def test_normalize_card_missing_external_links_yields_none():
    assert _normalize_card({"id": 2, "name": "Anna"})["tcgplayer_url"] is None
