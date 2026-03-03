from __future__ import annotations

import json
import re
import sqlite3
from abc import ABC, abstractmethod
from collections import Counter
from pathlib import Path
from typing import Any

from pysqlscribe.aggregate_functions import count
from pysqlscribe.scalar_functions import lower
from pysqlscribe.table import Table

from pysqlscribe.utils.ddl_loader import load_tables_from_ddls

DDL_PATH = Path(__file__).resolve().parent.parent / "ddl" / "create_card_table.sql"


def _to_scalar(value: Any) -> Any:
    if isinstance(value, (list, dict)):
        return json.dumps(value)
    return value


def _normalize_card(card: dict[str, Any]) -> dict[str, Any]:
    return {
        key: _to_scalar(value)
        for key, value in card.items()
    }


def _contains_case_insensitive(value: Any, search: str) -> bool:
    return search.lower() in str(value or "").lower()


def _parse_listish(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]

    text = str(value).strip()
    if not text:
        return []

    try:
        decoded = json.loads(text)
        if isinstance(decoded, list):
            return [str(item).strip() for item in decoded if str(item).strip()]
        if isinstance(decoded, str):
            text = decoded
    except json.JSONDecodeError:
        pass

    return [part.strip() for part in re.split(r"[,|]", text) if part.strip()]


class CardRepository(ABC):
    @abstractmethod
    def load_cards(self, cards: list[dict[str, Any]]) -> int:
        raise NotImplementedError

    @abstractmethod
    def has_cards(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def total_cards(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def search(
        self,
        *,
        name: str | None = None,
        color: str | None = None,
        cost: int | None = None,
        trait: str | None = None,
        rarity: str | None = None,
        inkwell: bool | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, card_id: int) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def count_by(self, field: str) -> dict[str, int]:
        raise NotImplementedError

    @abstractmethod
    def top_traits(self, limit: int = 10) -> dict[str, int]:
        raise NotImplementedError

    @abstractmethod
    def color_distribution(self) -> dict[str, int]:
        raise NotImplementedError



class SQLiteCardRepository(CardRepository):
    def __init__(self, db_path: Path, initial_load: bool = True) -> None:
        self._db_path = db_path
        self._card_table = None
        self._create_schema()
        self.card_table = load_tables_from_ddls(str(DDL_PATH), "sqlite")["lorcana_cards"]

    @property
    def card_table(self) -> Table:
        return self._card_table

    @card_table.setter
    def card_table(self, value):
        self._card_table = value

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _create_schema(self) -> None:
        ddl = DDL_PATH.read_text(encoding="utf-8")
        with self._conn() as conn:
            conn.executescript(ddl)

    def _run_query(self, query: str) -> list[dict[str, Any]]:
        with self._conn() as conn:
            cursor = conn.execute(query)
            rows = cursor.fetchall()
            if not cursor.description:
                return []
            columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in rows]

    def load_cards(self, cards: list[dict[str, Any]]) -> int:
        normalized = [_normalize_card(card) for card in cards]
        if not normalized:
            return 0

        with self._conn() as conn:
            conn.execute("DELETE FROM lorcana_cards")
            columns = sorted(set().union(*(card.keys() for card in normalized)))
            placeholders = ", ".join("?" for _ in columns)
            sql = (
                f"INSERT INTO lorcana_cards ({', '.join(columns)}) "
                f"VALUES ({placeholders})"
            )
            values = [tuple(card.get(column) for column in columns) for card in normalized]
            conn.executemany(sql, values)
        return len(normalized)

    def has_cards(self) -> bool:
        query = self.card_table.select(count(self._card_table.id).as_("count"))
        rows = self._run_query(query.build())
        return int(rows[0].get("count", 0)) > 0 if rows else False

    def total_cards(self) -> int:
        query = self.card_table.select(count(self._card_table.id).as_("count"))
        rows = self._run_query(query.build())
        return int(rows[0].get("count", 0)) if rows else 0

    def search(
        self,
        *,
        name: str | None = None,
        color: str | None = None,
        cost: int | None = None,
        trait: str | None = None,
        rarity: str | None = None,
        inkwell: bool | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        limited = max(1, min(limit, 200))
        clauses = []

        if name:
            clauses.append(lower(self._card_table.name).like(f"%{name}%"))
        if cost is not None:
            clauses.append(self._card_table.cost == int(cost))
        if trait:
            clauses.append(lower(self._card_table.traits).like(f"%{trait}%"))
        if rarity:
            clauses.append(lower(self._card_table.rarity) == rarity)
        if inkwell is not None:
            clauses.append(self._card_table.inkwell == (1 if inkwell else 0))

        query = self._card_table.select("*")
        if clauses:
            query = query.where(*clauses)
        query = query.order_by(self._card_table.id).limit(limited)

        rows = self._run_query(query.build())
        if color:
            rows = [
                row
                for row in rows
                if _contains_case_insensitive(row.get("colors") or row.get("color"), color)
            ]
        return rows[:limited]

    def get_by_id(self, card_id: int) -> dict[str, Any] | None:
        query = self._card_table.select("*").where(self._card_table.id == card_id).limit(1)
        rows = self._run_query(query.build())
        return rows[0] if rows else None

    def count_by(self, field: str) -> dict[str, int]:

        column = getattr(self._card_table, field)
        query = self._card_table.select(column, count(column).as_("count")).group_by(column)
        rows = self._run_query(query.build())
        rows.sort(key=lambda row: int(row.get("count", 0)), reverse=True)
        return {str(row.get(field) or ""): int(row.get("count", 0)) for row in rows}

    def top_traits(self, limit: int = 10) -> dict[str, int]:
        limited = max(1, min(limit, 100))
        query = self._card_table.select(self._card_table.traits)
        rows = self._run_query(query.build())
        counter = Counter()
        for row in rows:
            for trait in _parse_listish(row.get("traits")):
                counter[trait] += 1
        return dict(counter.most_common(limited))

    def color_distribution(self) -> dict[str, int]:
        query = self._card_table.select(self._card_table.colors, self._card_table.color)
        rows = self._run_query(query.build())
        counter = Counter()
        for row in rows:
            colors = _parse_listish(row.get("colors"))
            if colors:
                for color in colors:
                    counter[color] += 1
            elif row.get("color") is not None:
                counter[str(row.get("color"))] += 1
        return dict(counter.most_common())
