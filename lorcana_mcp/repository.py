from __future__ import annotations

import difflib
import json
import re
from abc import ABC, abstractmethod
from collections import Counter
from functools import reduce
from pathlib import Path
from typing import Any

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
        if cache_path and cache_path.exists():
            self._cards = json.loads(cache_path.read_text(encoding="utf-8"))

    def load_cards(self, cards: list[dict[str, Any]]) -> int:
        self._cards = list(cards)
        if self._cache_path:
            self._cache_path.write_text(json.dumps(self._cards, ensure_ascii=False), encoding="utf-8")
        return len(self._cards)

    @property
    def total_cards(self) -> int:
        return len(self._cards)

    _SORTABLE_FIELDS = {"id", "name", "cost", "strength", "willpower", "lore", "rarity", "set_code"}

    @staticmethod
    def _filter(
        cards: list[dict[str, Any]],
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
    ) -> list[dict[str, Any]]:
        filter_clauses = []
        if name:
            filter_clauses.append(lambda c: name.lower() in (c.get("name") or ""))
        if color:
            filter_clauses.append(lambda c: color.lower() == (c.get("color") or ""))
        if cost is not None:
            filter_clauses.append(lambda c: c.get("cost") == int(cost))
        if min_cost is not None:
            filter_clauses.append(lambda c: (c.get("cost") or 0) >= int(min_cost))
        if max_cost is not None:
            filter_clauses.append(lambda c: (c.get("cost") or 0) <= int(max_cost))
        if trait:
            filter_clauses.append(lambda c: trait.lower() in (c.get("subtypes") or "").lower())
        if rarity:
            filter_clauses.append(lambda c: rarity.lower() == (c.get("rarity") or "").lower())
        if inkwell is not None:
            filter_clauses.append(lambda c: bool(c.get("inkwell")) == inkwell)
        if set_code is not None:
            filter_clauses.append(lambda c: str(c.get("set_code") or "") == str(set_code))
        if min_attack is not None:
            filter_clauses.append(lambda c: c.get("strength") is not None and c["strength"] >= int(min_attack))
        if max_attack is not None:
            filter_clauses.append(lambda c: c.get("strength") is not None and c["strength"] <= int(max_attack))
        if min_defence is not None:
            filter_clauses.append(lambda c: c.get("willpower") is not None and c["willpower"] >= int(min_defence))
        if max_defence is not None:
            filter_clauses.append(lambda c: c.get("willpower") is not None and c["willpower"] <= int(max_defence))
        if body_text:
            filter_clauses.append(lambda c: body_text.lower() in (c.get("full_text") or "").lower())
        if lore is not None:
            filter_clauses.append(lambda c: c.get("lore") == int(lore))
        if min_lore is not None:
            filter_clauses.append(lambda c: c.get("lore") is not None and c["lore"] >= int(min_lore))
        if max_lore is not None:
            filter_clauses.append(lambda c: c.get("lore") is not None and c["lore"] <= int(max_lore))
        if card_type:
            filter_clauses.append(lambda c: card_type.lower() in (c.get("type") or "").lower())
        results = reduce(lambda items, f: filter(f, items), filter_clauses, cards)

        return list(results)

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
        results = self._filter(
            self._cards,
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
        results = self._sort(results, sort_field, reverse=sort_order.lower() == "desc")
        return [_slim_card(c) for c in results[paged : paged + limited]]

    def get_by_id(self, card_id: int) -> dict[str, Any] | None:
        return next((c for c in self._cards if c.get("id") == card_id), None)

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
        return len(
            self._filter(
                self._cards,
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
        )

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
