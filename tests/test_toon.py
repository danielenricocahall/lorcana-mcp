from lorcana_mcp.toon import to_toon


def test_empty_rows():
    assert to_toon([]) == "rows[0]{}:\n"
    assert to_toon([], name="cards") == "cards[0]{}:\n"


def test_basic_homogeneous_rows():
    rows = [
        {"id": 1, "name": "Mickey", "cost": 3},
        {"id": 2, "name": "Elsa", "cost": 5},
    ]
    out = to_toon(rows, name="cards")
    assert out == ("cards[2]{id,name,cost}:\n1,Mickey,3\n2,Elsa,5\n")


def test_missing_keys_render_as_empty_cells():
    rows = [
        {"id": 1, "name": "Mickey", "strength": 2},
        {"id": 2, "name": "Let It Go"},
    ]
    out = to_toon(rows)
    lines = out.splitlines()
    assert lines[0] == "rows[2]{id,name,strength}:"
    assert lines[1] == "1,Mickey,2"
    assert lines[2] == "2,Let It Go,"


def test_none_values_render_as_empty():
    rows = [{"id": 1, "strength": None}]
    out = to_toon(rows)
    assert out.splitlines()[1] == "1,"


def test_bool_values():
    rows = [{"id": 1, "inkwell": True}, {"id": 2, "inkwell": False}]
    out = to_toon(rows)
    body = out.splitlines()[1:]
    assert body == ["1,true", "2,false"]


def test_quoting_for_comma_and_newline():
    rows = [
        {"id": 1, "text": "hello, world"},
        {"id": 2, "text": "line1\nline2"},
        {"id": 3, "text": 'he said "hi"'},
    ]
    out = to_toon(rows)
    body = out.splitlines()
    assert body[1] == '1,"hello, world"'
    # newline inside a quoted field; splitlines splits the embedded newline too
    assert body[2].startswith('2,"line1')
    # internal double-quote at the start gets escaped
    assert body[4] == '3,he said "hi"'


def test_first_seen_column_order_across_rows():
    rows = [
        {"a": 1, "b": 2},
        {"c": 3, "a": 4},
    ]
    out = to_toon(rows)
    assert out.splitlines()[0] == "rows[2]{a,b,c}:"


def test_column_count_matches_header():
    rows = [
        {"id": 1, "name": "Mickey", "cost": 3, "strength": 2, "willpower": 3, "lore": 1},
        {"id": 2, "name": "Let It Go", "cost": 4},
    ]
    out = to_toon(rows)
    cols = out.splitlines()[0].split("{")[1].split("}")[0].split(",")
    for body_line in out.splitlines()[1:]:
        # commas == cols-1 (allowing for empty trailing cells)
        assert body_line.count(",") == len(cols) - 1
