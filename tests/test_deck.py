from lorcana_mcp.deck import (
    MalformedLine,
    ParsedLine,
    deck_stats,
    dump_deck,
    parse_lines,
    validate_deck,
)


def _card(
    name: str,
    *,
    color: list[str],
    cost: int = 3,
    inkwell: bool = True,
    type_: str = "Character",
    keywords: list[str] | None = None,
    subtypes: str | None = None,
) -> dict:
    return {
        "full_name": name,
        "color": color,
        "cost": cost,
        "inkwell": inkwell,
        "type": type_,
        "abilities": [{"name": k} for k in keywords or []],
        "subtypes": subtypes,
    }


def _entry(card: dict | None, count: int, name: str | None = None) -> dict:
    return {"count": count, "name": name if name is not None else (card or {}).get("full_name", ""), "card": card}


def test_dump_deck_basic():
    deck = [
        {"name": "Mickey Mouse - Brave Little Tailor", "count": 4},
        {"name": "Be Prepared", "count": 3},
    ]
    assert dump_deck(deck) == ("4 Mickey Mouse - Brave Little Tailor\n3 Be Prepared\n")


def test_dump_deck_empty():
    assert dump_deck([]) == ""


def test_dump_deck_skips_zero_and_negative_counts():
    deck = [
        {"name": "Mickey Mouse - Brave Little Tailor", "count": 4},
        {"name": "Skipped Zero", "count": 0},
        {"name": "Skipped Negative", "count": -1},
        {"name": "Be Prepared", "count": 1},
    ]
    out = dump_deck(deck)
    assert "Skipped Zero" not in out
    assert "Skipped Negative" not in out
    assert out.splitlines() == [
        "4 Mickey Mouse - Brave Little Tailor",
        "1 Be Prepared",
    ]


def test_parse_lines_basic():
    text = "4 Mickey Mouse - Brave Little Tailor\n3 Be Prepared\n"
    out = parse_lines(text)
    assert out == [
        ParsedLine(count=4, name="Mickey Mouse - Brave Little Tailor", raw="4 Mickey Mouse - Brave Little Tailor"),
        ParsedLine(count=3, name="Be Prepared", raw="3 Be Prepared"),
    ]


def test_parse_lines_handles_x_variant_and_whitespace():
    text = "  4x   Mickey Mouse - Brave Little Tailor  \n   2 Be Prepared\n"
    out = parse_lines(text)
    assert [(line.count, line.name) for line in out] == [
        (4, "Mickey Mouse - Brave Little Tailor"),
        (2, "Be Prepared"),
    ]


def test_parse_lines_skips_blanks_comments_totals_and_sections():
    text = "\n".join(
        [
            "# my deck",
            "// alt comment",
            "[Main Deck]",
            "",
            "4 Mickey Mouse - Brave Little Tailor",
            "Total: 60",
            "Total 60",
            "",
        ]
    )
    out = parse_lines(text)
    assert len(out) == 1
    assert isinstance(out[0], ParsedLine)
    assert out[0].name == "Mickey Mouse - Brave Little Tailor"


def test_parse_lines_normalizes_em_and_en_dashes():
    text = "4 Mickey Mouse – Brave Little Tailor\n3 Maui — Hero to All\n"
    out = parse_lines(text)
    assert [line.name for line in out] == [
        "Mickey Mouse - Brave Little Tailor",
        "Maui - Hero to All",
    ]


def test_parse_lines_marks_malformed():
    text = "not a card line\n4 Mickey Mouse - Brave Little Tailor\n"
    out = parse_lines(text)
    assert isinstance(out[0], MalformedLine)
    assert out[0].raw == "not a card line"
    assert isinstance(out[1], ParsedLine)


def test_validate_deck_legal_mono_amber():
    # 15 distinct Amber cards × 4 copies = 60.
    deck = [_entry(_card(f"Amber Card {i}", color=["Amber"]), 4) for i in range(15)]
    result = validate_deck(deck)
    assert result == {
        "legal": True,
        "total_cards": 60,
        "inks": ["Amber"],
        "violations": [],
    }


def test_validate_deck_oversized_is_legal():
    # 60 is the minimum, not the cap. A 64-card mono-Amber deck is legal.
    deck = [_entry(_card(f"Amber Card {i}", color=["Amber"]), 4) for i in range(16)]
    result = validate_deck(deck)
    assert result["total_cards"] == 64
    assert result["legal"] is True
    assert result["violations"] == []


def test_validate_deck_legal_two_colors_with_dual_ink():
    amber_cards = [_entry(_card(f"Amber {i}", color=["Amber"]), 4) for i in range(7)]
    amethyst_cards = [_entry(_card(f"Amethyst {i}", color=["Amethyst"]), 4) for i in range(7)]
    pongo = _entry(_card("Pongo - Ol' Rascal", color=["Amber", "Amethyst"]), 4)
    result = validate_deck([*amber_cards, *amethyst_cards, pongo])
    assert result["legal"] is True
    assert result["inks"] == ["Amber", "Amethyst"]
    assert result["violations"] == []


def test_validate_deck_dual_ink_in_mono_deck_flags_ink_limit():
    # A Ruby/Sapphire dual-ink in a deck whose other cards are Ruby+Steel pushes
    # the ink set to {Ruby, Sapphire, Steel} — three colors → ink_limit violation.
    ruby_cards = [_entry(_card(f"Ruby {i}", color=["Ruby"]), 4) for i in range(7)]
    steel_cards = [_entry(_card(f"Steel {i}", color=["Steel"]), 4) for i in range(7)]
    dual = _entry(_card("Pongo - Ol' Rascal", color=["Ruby", "Sapphire"]), 4)
    result = validate_deck([*ruby_cards, *steel_cards, dual])
    assert result["legal"] is False
    ink_violation = next(v for v in result["violations"] if v["type"] == "ink_limit")
    assert ink_violation == {"type": "ink_limit", "inks": ["Ruby", "Sapphire", "Steel"], "max": 2}


def test_validate_deck_size_and_copy_violations():
    amber = _card("Mickey - Brave Little Tailor", color=["Amber"])
    other = _card("Anna - Heir to Arendelle", color=["Amber"])
    deck = [_entry(amber, 5), _entry(other, 50)]  # 55 cards, Mickey x5
    result = validate_deck(deck)
    assert result["legal"] is False
    types = {v["type"] for v in result["violations"]}
    assert "deck_size" in types
    assert "max_copies" in types
    size = next(v for v in result["violations"] if v["type"] == "deck_size")
    assert size == {"type": "deck_size", "total": 55, "min": 60}
    copies = next(v for v in result["violations"] if v["type"] == "max_copies")
    assert copies == {"type": "max_copies", "card": "Mickey - Brave Little Tailor", "count": 5, "max": 4}


def test_validate_deck_unknown_card():
    amber = _card("Mickey - Brave Little Tailor", color=["Amber"])
    deck = [_entry(amber, 56), _entry(None, 4, name="Bogus - Not Real")]
    result = validate_deck(deck)
    assert result["legal"] is False
    unknown = next(v for v in result["violations"] if v["type"] == "unknown_card")
    assert unknown == {"type": "unknown_card", "name": "Bogus - Not Real", "count": 4}


def test_deck_stats_basic_curve_and_breakdown():
    char_a = _card("Mickey - Brave Little Tailor", color=["Amber"], cost=3, inkwell=True, type_="Character")
    char_b = _card("Anna - Heir to Arendelle", color=["Amber"], cost=2, inkwell=True, type_="Character")
    action = _card("Let It Go", color=["Amethyst"], cost=4, inkwell=False, type_="Action")
    deck = [_entry(char_a, 4), _entry(char_b, 3), _entry(action, 2)]
    stats = deck_stats(deck)
    assert stats["total_cards"] == 9
    assert stats["ink_curve"] == {2: 3, 3: 4, 4: 2}
    assert stats["type_breakdown"] == {"Character": 7, "Action": 2}
    assert stats["inkable_count"] == 7
    assert stats["uninkable_count"] == 2
    assert stats["color_split"] == {"Amber": 7, "Amethyst": 2}
    assert stats["inks"] == ["Amber", "Amethyst"]
    assert stats["unresolved"] == []


def test_deck_stats_dual_ink_contributes_to_both_color_buckets():
    pongo = _card("Pongo - Ol' Rascal", color=["Amber", "Amethyst"], cost=4)
    deck = [_entry(pongo, 4)]
    stats = deck_stats(deck)
    # 4 copies, but each contributes to both Amber and Amethyst — sum exceeds total.
    assert stats["color_split"] == {"Amber": 4, "Amethyst": 4}
    assert stats["total_cards"] == 4


def test_deck_stats_unresolved_excluded_from_stats_but_counted_in_total():
    amber = _card("Mickey - Brave Little Tailor", color=["Amber"], cost=3, inkwell=True)
    deck = [_entry(amber, 4), _entry(None, 2, name="Bogus")]
    stats = deck_stats(deck)
    assert stats["total_cards"] == 6
    assert stats["unresolved"] == ["Bogus"]
    # Ink curve / type / color reflect only the resolved 4 copies.
    assert stats["ink_curve"] == {3: 4}
    assert stats["color_split"] == {"Amber": 4}
    assert stats["inkable_count"] == 4
    assert stats["uninkable_count"] == 0


def test_deck_stats_keyword_counts_tally_copies_not_distinct_cards():
    pegasus = _card("Pegasus - Gift for Hercules", color=["Amethyst"], keywords=["Evasive"])
    gwythaint = _card("Gwythaint - Savage Hunter", color=["Amethyst"], keywords=["Evasive"])
    dumbo = _card("Dumbo - Ninth Wonder", color=["Amber"], keywords=["Evasive", "Ward"])
    vanilla = _card("Anna - Heir to Arendelle", color=["Amber"])
    deck = [_entry(pegasus, 4), _entry(gwythaint, 4), _entry(dumbo, 3), _entry(vanilla, 2)]
    stats = deck_stats(deck)
    # 11 Evasive copies across 3 distinct cards; Dumbo lands in both keyword buckets.
    assert stats["keyword_counts"] == {"Evasive": 11, "Ward": 3}
    assert stats["total_cards"] == 13


def test_deck_stats_keyword_counts_omits_cards_with_no_keywords():
    vanilla = _card("Anna - Heir to Arendelle", color=["Amber"])
    stats = deck_stats([_entry(vanilla, 4)])
    assert stats["keyword_counts"] == {}
    assert stats["card_keywords"] == []


def test_deck_stats_card_keywords_lists_per_card_tags():
    dumbo = _card("Dumbo - Ninth Wonder", color=["Amber"], keywords=["Ward", "Evasive"])
    vanilla = _card("Anna - Heir to Arendelle", color=["Amber"])
    stats = deck_stats([_entry(dumbo, 3), _entry(vanilla, 2)])
    assert stats["card_keywords"] == [
        {"name": "Dumbo - Ninth Wonder", "count": 3, "keywords": ["Evasive", "Ward"]},
    ]


def test_deck_stats_subtype_counts_split_on_bullet_delimiter():
    hook = _card("Captain Hook - Forceful Duelist", color=["Steel"], subtypes="Dreamborn • Villain • Pirate")
    stats = deck_stats([_entry(hook, 4)])
    assert stats["subtype_counts"] == {"Dreamborn": 4, "Villain": 4, "Pirate": 4}


def test_deck_stats_unresolved_excluded_from_keyword_and_subtype_counts():
    dumbo = _card("Dumbo - Ninth Wonder", color=["Amber"], keywords=["Evasive"], subtypes="Storyborn")
    deck = [_entry(dumbo, 4), _entry(None, 2, name="Bogus")]
    stats = deck_stats(deck)
    assert stats["keyword_counts"] == {"Evasive": 4}
    assert stats["subtype_counts"] == {"Storyborn": 4}
    assert stats["total_cards"] == 6


def test_dump_then_parse_roundtrip():
    deck = [
        {"name": "Mickey Mouse - Brave Little Tailor", "count": 4},
        {"name": "Be Prepared", "count": 3},
        {"name": "Hakuna Matata", "count": 2},
    ]
    text = dump_deck(deck)
    parsed = parse_lines(text)
    assert all(isinstance(line, ParsedLine) for line in parsed)
    assert [(line.count, line.name) for line in parsed] == [(e["count"], e["name"]) for e in deck]
