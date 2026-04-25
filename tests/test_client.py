from lorcana_mcp.client import _normalize_card


def test_normalize_card_extracts_marketplace_urls():
    raw = {
        "id": 1,
        "name": "Ariel",
        "fullName": "Ariel - On Human Legs",
        "externalLinks": {
            "tcgPlayerId": 494102,
            "tcgPlayerUrl": "https://www.tcgplayer.com/product/494102",
            "cardmarketId": 727081,
            "cardmarketUrl": "https://www.cardmarket.com/en/Lorcana/Products/Singles/The-First-Chapter/Ariel-On-Human-Legs",
            "cardTraderId": 258961,
            "cardTraderUrl": "https://www.cardtrader.com/cards/258961",
        },
    }
    out = _normalize_card(raw)
    assert out["tcgplayer_url"] == "https://www.tcgplayer.com/product/494102"
    assert out["cardmarket_url"].startswith("https://www.cardmarket.com/")
    assert out["cardtrader_url"] == "https://www.cardtrader.com/cards/258961"


def test_normalize_card_missing_external_links_yields_none():
    out = _normalize_card({"id": 2, "name": "Anna"})
    assert out["tcgplayer_url"] is None
    assert out["cardmarket_url"] is None
    assert out["cardtrader_url"] is None
