from __future__ import annotations

import difflib
import json
import re
from abc import ABC, abstractmethod
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any, NamedTuple

_JSON_COLUMNS = {"abilities"}

_SEARCH_FIELDS = frozenset(
    {
        "id",
        "name",
        "version",
        "full_name",
        "cost",
        "inkwell",
        "strength",
        "willpower",
        "color",
        "type",
        "full_text",
        "lore",
        "rarity",
        "set_code",
        "subtypes",
    }
)


def _slim_card(card: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in card.items() if k in _SEARCH_FIELDS}


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

    return [part.strip() for part in re.split(r"[,|•]", text) if part.strip()]


class _SearchRow(NamedTuple):
    name_lc: str
    color_lc: str
    type_lc: str
    rarity_lc: str
    subtypes_lc: str
    full_text_lc: str
    set_code_str: str


def _make_row(card: dict[str, Any]) -> _SearchRow:
    return _SearchRow(
        name_lc=(card.get("name") or "").lower(),
        color_lc=(card.get("color") or "").lower(),
        type_lc=(card.get("type") or "").lower(),
        rarity_lc=(card.get("rarity") or "").lower(),
        subtypes_lc=(card.get("subtypes") or "").lower(),
        full_text_lc=(card.get("full_text") or "").lower(),
        set_code_str=str(card.get("set_code") or ""),
    )


_Predicate = Callable[[dict[str, Any], _SearchRow], bool]


class CardRepository(ABC):
    @abstractmethod
    def load_cards(self, cards: list[dict[str, Any]]) -> int:
        raise NotImplementedError

    @property
    @abstractmethod
    def total_cards(self) -> int:
        raise NotImplementedError

    @property
    def has_cards(self) -> bool:
        return self.total_cards > 0

    @abstractmethod
    def search(
        self,
        *,
        name: str | None = None,
        color: str | None = None,
        cost: int | None = None,
        min_cost: int | None = None,
        max_cost: int | None = None,
        trait: str | None = None,
        rarity: str | None = None,
        inkwell: bool | None = None,
        set_code: str | None = None,
        min_attack: int | None = None,
        max_attack: int | None = None,
        min_defence: int | None = None,
        max_defence: int | None = None,
        body_text: str | None = None,
        lore: int | None = None,
        min_lore: int | None = None,
        max_lore: int | None = None,
        card_type: str | None = None,
        limit: int = 20,
        offset: int = 0,
        sort_by: str = "id",
        sort_order: str = "asc",
    ) -> list[dict[str, Any]]:
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

    @property
    @abstractmethod
    def _all_cards(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    def resolve_card(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        query_lower = query.lower().strip()
        tokens = [t for t in re.split(r"[\s\-]+", re.sub(r"[^\w\s\-]", " ", query_lower)) if t]
        scored = []
        for card in self._all_cards:
            full = (card.get("full_name") or "").lower()
            name = (card.get("name") or "").lower()
            token_hits = sum(1 for t in tokens if t in full or t in name)
            token_score = token_hits / max(len(tokens), 1)
            seq_score = max(
                difflib.SequenceMatcher(None, query_lower, full).ratio(),
                difflib.SequenceMatcher(None, query_lower, name).ratio(),
            )
            score = 0.6 * token_score + 0.4 * seq_score
            if score > 0:
                scored.append((score, card))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [card for _, card in scored[:limit]]

    @abstractmethod
    def count(
        self,
        *,
        name: str | None = None,
        color: str | None = None,
        cost: int | None = None,
        min_cost: int | None = None,
        max_cost: int | None = None,
        trait: str | None = None,
        rarity: str | None = None,
        inkwell: bool | None = None,
        set_code: str | None = None,
        min_attack: int | None = None,
        max_attack: int | None = None,
        min_defence: int | None = None,
        max_defence: int | None = None,
        body_text: str | None = None,
        lore: int | None = None,
        min_lore: int | None = None,
        max_lore: int | None = None,
        card_type: str | None = None,
    ) -> int:
        raise NotImplementedError


class InMemoryCardRepository(CardRepository):
    def __init__(self, cache_path: Path | None = None) -> None:
        self._cache_path = cache_path
        self._cards: list[dict[str, Any]] = []
        self._rows: list[_SearchRow] = []
        if cache_path and cache_path.exists():
            self._set_cards(json.loads(cache_path.read_text(encoding="utf-8")))

    def _set_cards(self, cards: list[dict[str, Any]]) -> None:
        self._cards = list(cards)
        self._rows = [_make_row(c) for c in self._cards]

    def load_cards(self, cards: list[dict[str, Any]]) -> int:
        self._set_cards(cards)
        if self._cache_path:
            self._cache_path.write_text(json.dumps(self._cards, ensure_ascii=False), encoding="utf-8")
        return len(self._cards)

    @property
    def total_cards(self) -> int:
        return len(self._cards)

    _SORTABLE_FIELDS = {"id", "name", "cost", "strength", "willpower", "lore", "rarity", "set_code"}

    @staticmethod
    def _build_predicates(
        *,
        name: str | None,
        color: str | None,
        cost: int | None,
        min_cost: int | None,
        max_cost: int | None,
        trait: str | None,
        rarity: str | None,
        inkwell: bool | None,
        set_code: str | None,
        min_attack: int | None,
        max_attack: int | None,
        min_defence: int | None,
        max_defence: int | None,
        body_text: str | None,
        lore: int | None,
        min_lore: int | None,
        max_lore: int | None,
        card_type: str | None,
    ) -> list[_Predicate]:
        checks: list[_Predicate] = []
        if name:
            checks.append(lambda c, r, v=name.lower(): v in r.name_lc)
        if color:
            checks.append(lambda c, r, v=color.lower(): r.color_lc == v)
        if cost is not None:
            checks.append(lambda c, r, v=int(cost): c.get("cost") == v)
        if min_cost is not None:
            checks.append(lambda c, r, v=int(min_cost): (c.get("cost") or 0) >= v)
        if max_cost is not None:
            checks.append(lambda c, r, v=int(max_cost): (c.get("cost") or 0) <= v)
        if trait:
            checks.append(lambda c, r, v=trait.lower(): v in r.subtypes_lc)
        if rarity:
            checks.append(lambda c, r, v=rarity.lower(): r.rarity_lc == v)
        if inkwell is not None:
            checks.append(lambda c, r, v=bool(inkwell): bool(c.get("inkwell")) == v)
        if set_code is not None:
            checks.append(lambda c, r, v=str(set_code): r.set_code_str == v)
        if min_attack is not None:
            checks.append(lambda c, r, v=int(min_attack): c.get("strength") is not None and c["strength"] >= v)
        if max_attack is not None:
            checks.append(lambda c, r, v=int(max_attack): c.get("strength") is not None and c["strength"] <= v)
        if min_defence is not None:
            checks.append(lambda c, r, v=int(min_defence): c.get("willpower") is not None and c["willpower"] >= v)
        if max_defence is not None:
            checks.append(lambda c, r, v=int(max_defence): c.get("willpower") is not None and c["willpower"] <= v)
        if body_text:
            checks.append(lambda c, r, v=body_text.lower(): v in r.full_text_lc)
        if lore is not None:
            checks.append(lambda c, r, v=int(lore): c.get("lore") == v)
        if min_lore is not None:
            checks.append(lambda c, r, v=int(min_lore): c.get("lore") is not None and c["lore"] >= v)
        if max_lore is not None:
            checks.append(lambda c, r, v=int(max_lore): c.get("lore") is not None and c["lore"] <= v)
        if card_type:
            checks.append(lambda c, r, v=card_type.lower(): v in r.type_lc)
        return checks

    def _iter_matching(self, checks: list[_Predicate]):
        if not checks:
            yield from self._cards
            return
        for card, row in zip(self._cards, self._rows):
            if all(check(card, row) for check in checks):
                yield card

    @staticmethod
    def _sort(cards: list[dict[str, Any]], field: str, reverse: bool) -> list[dict[str, Any]]:
        none_cards = [c for c in cards if c.get(field) is None]
        value_cards = [c for c in cards if c.get(field) is not None]
        value_cards.sort(key=lambda c: c[field], reverse=reverse)
        return value_cards + none_cards

    def search(
        self,
        *,
        name: str | None = None,
        color: str | None = None,
        cost: int | None = None,
        min_cost: int | None = None,
        max_cost: int | None = None,
        trait: str | None = None,
        rarity: str | None = None,
        inkwell: bool | None = None,
        set_code: str | None = None,
        min_attack: int | None = None,
        max_attack: int | None = None,
        min_defence: int | None = None,
        max_defence: int | None = None,
        body_text: str | None = None,
        lore: int | None = None,
        min_lore: int | None = None,
        max_lore: int | None = None,
        card_type: str | None = None,
        limit: int = 20,
        offset: int = 0,
        sort_by: str = "id",
        sort_order: str = "asc",
    ) -> list[dict[str, Any]]:
        limited = max(1, min(limit, 200))
        paged = max(0, offset)
        sort_field = sort_by if sort_by in self._SORTABLE_FIELDS else "id"
        checks = self._build_predicates(
            name=name,
            color=color,
            cost=cost,
            min_cost=min_cost,
            max_cost=max_cost,
            trait=trait,
            rarity=rarity,
            inkwell=inkwell,
            set_code=set_code,
            min_attack=min_attack,
            max_attack=max_attack,
            min_defence=min_defence,
            max_defence=max_defence,
            body_text=body_text,
            lore=lore,
            min_lore=min_lore,
            max_lore=max_lore,
            card_type=card_type,
        )
        results = list(self._iter_matching(checks))
        results = self._sort(results, sort_field, reverse=sort_order.lower() == "desc")
        return [_slim_card(c) for c in results[paged : paged + limited]]

    def count(
        self,
        *,
        name: str | None = None,
        color: str | None = None,
        cost: int | None = None,
        min_cost: int | None = None,
        max_cost: int | None = None,
        trait: str | None = None,
        rarity: str | None = None,
        inkwell: bool | None = None,
        set_code: str | None = None,
        min_attack: int | None = None,
        max_attack: int | None = None,
        min_defence: int | None = None,
        max_defence: int | None = None,
        body_text: str | None = None,
        lore: int | None = None,
        min_lore: int | None = None,
        max_lore: int | None = None,
        card_type: str | None = None,
    ) -> int:
        checks = self._build_predicates(
            name=name,
            color=color,
            cost=cost,
            min_cost=min_cost,
            max_cost=max_cost,
            trait=trait,
            rarity=rarity,
            inkwell=inkwell,
            set_code=set_code,
            min_attack=min_attack,
            max_attack=max_attack,
            min_defence=min_defence,
            max_defence=max_defence,
            body_text=body_text,
            lore=lore,
            min_lore=min_lore,
            max_lore=max_lore,
            card_type=card_type,
        )
        if not checks:
            return len(self._cards)
        return sum(1 for _ in self._iter_matching(checks))

    def count_by(self, field: str) -> dict[str, int]:
        counter: Counter = Counter(str(c.get(field) or "") for c in self._cards)
        return dict(counter.most_common())

    def top_traits(self, limit: int = 10) -> dict[str, int]:
        limited = max(1, min(limit, 100))
        counter: Counter = Counter()
        for card in self._cards:
            for trait in _parse_listish(card.get("subtypes")):
                counter[trait] += 1
        return dict(counter.most_common(limited))

    def color_distribution(self) -> dict[str, int]:
        counter: Counter = Counter()
        for card in self._cards:
            color = card.get("color")
            if color:
                counter[color.lower()] += 1
        return dict(counter.most_common())

    @property
    def _all_cards(self) -> list[dict[str, Any]]:
        return self._cards
