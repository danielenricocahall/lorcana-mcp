from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb

from lorcana_mcp.tagger import derive_tags

COLLECTION_NAME = "lorcana_cards"
_COLOR_MAP: dict[int, str] = {
    1: "ruby", 2: "sapphire", 3: "emerald", 4: "amber", 5: "amethyst", 6: "steel"
}
_BATCH_SIZE = 100


def _build_document(card: dict[str, Any], tags: list[str]) -> str:
    color_id = card.get("color")
    color_name = _COLOR_MAP.get(int(color_id), "unknown") if color_id is not None else "unknown"

    name = card.get("name") or ""
    title = card.get("title") or ""
    full_name = f"{name} - {title}" if title else name
    card_type = card.get("type") or ""
    cost = card.get("cost", "?")
    attack = card.get("attack", "?")
    defence = card.get("defence", "?")
    lore = card.get("stars", "?")
    traits = card.get("traits") or ""
    action = card.get("action") or ""

    parts = [
        full_name,
        f"Type: {card_type} | Color: {color_name} | Cost: {cost} | Attack: {attack} | Willpower: {defence} | Lore: {lore}",
    ]
    if traits:
        parts.append(f"Traits: {traits}")
    if action:
        parts.append(f"Abilities: {action}")
    if tags:
        parts.append(f"Tags: {', '.join(tags)}")

    return "\n".join(parts)


class ChromaCardIndex:
    def __init__(self, persist_dir: Path) -> None:
        persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(persist_dir))
        self._collection = self._client.get_or_create_collection(COLLECTION_NAME)

    def is_hydrated(self) -> bool:
        return self._collection.count() > 0

    def hydrate(self, cards: list[dict[str, Any]]) -> None:
        self._client.delete_collection(COLLECTION_NAME)
        self._collection = self._client.get_or_create_collection(COLLECTION_NAME)

        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict[str, Any]] = []

        for card in cards:
            card_id = card.get("id")
            if card_id is None:
                continue

            tags = derive_tags(card)
            doc = _build_document(card, tags)

            color_id = card.get("color")
            color_name = _COLOR_MAP.get(int(color_id), "") if color_id is not None else ""
            rarity = str(card.get("rarity") or "").lower()
            cost = card.get("cost")

            ids.append(str(card_id))
            documents.append(doc)
            metadatas.append({
                "color": color_name,
                "rarity": rarity,
                "cost": int(cost) if cost is not None else 0,
                "card_type": str(card.get("type") or "").lower(),
            })

        for i in range(0, len(ids), _BATCH_SIZE):
            self._collection.add(
                ids=ids[i : i + _BATCH_SIZE],
                documents=documents[i : i + _BATCH_SIZE],
                metadatas=metadatas[i : i + _BATCH_SIZE],
            )

    def search(
        self,
        query: str,
        n_results: int = 10,
        color: str | None = None,
        rarity: str | None = None,
    ) -> list[int]:
        total = self._collection.count()
        if total == 0:
            return []

        capped = min(n_results, total)

        where_clauses: list[dict[str, str]] = []
        if color:
            where_clauses.append({"color": color.lower()})
        if rarity:
            where_clauses.append({"rarity": rarity.lower()})

        kwargs: dict[str, Any] = {
            "query_texts": [query],
            "n_results": capped,
        }
        if len(where_clauses) == 1:
            kwargs["where"] = where_clauses[0]
        elif len(where_clauses) > 1:
            kwargs["where"] = {"$and": where_clauses}

        results = self._collection.query(**kwargs)
        raw_ids: list[str] = results.get("ids", [[]])[0]
        return [int(raw_id) for raw_id in raw_ids]
