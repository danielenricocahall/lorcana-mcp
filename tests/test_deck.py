from lorcana_mcp.deck import MalformedLine, ParsedLine, dump_deck, parse_lines


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
