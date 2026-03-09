from __future__ import annotations

import re
from typing import Any


def derive_tags(card: dict[str, Any]) -> list[str]:
    """Derive heuristic gameplay tags from a card dict."""
    tags: list[str] = []
    action = str(card.get("action") or "").lower()
    card_type = str(card.get("type") or "").lower()
    cost = card.get("cost")
    stars = card.get("stars")  # lore value
    attack = card.get("attack")
    defence = card.get("defence")
    inkwell = card.get("inkwell")

    # --- Keyword abilities (deterministic) ---
    keywords = {
        "evasive": r"\bevasive\b",
        "rush": r"\brush\b",
        "ward": r"\bward\b",
        "bodyguard": r"\bbodyguard\b",
        "singer": r"\bsinger\b",
        "challenger": r"\bchallenger\b",
        "support": r"\bsupport\b",
        "shift": r"\bshift\b",
        "resist": r"\bresist\b",
        "reckless": r"\breckless\b",
        "vanish": r"\bvanish\b",
    }
    for tag, pattern in keywords.items():
        if re.search(pattern, action):
            tags.append(tag)

    # --- Behavioral patterns ---
    if re.search(r"return .{0,60} (to|into) .{0,30} hand", action):
        tags.append("bounce")

    if re.search(r"draw \d+ cards?", action) or re.search(r"draw a card", action):
        tags.append("draw")

    if re.search(r"\bbanish\b", action):
        tags.append("removal")

    if re.search(r"deal \d+ damage", action):
        tags.append("damage_dealer")

    if re.search(r"remove \d+ damage", action):
        tags.append("heal")

    if re.search(r"\bready\b", action):
        tags.append("ready")

    if re.search(r"\bexert\b", action) and re.search(r"\b(chosen|target)\b", action):
        tags.append("exert")

    if re.search(r"\bdiscards?\b", action):
        tags.append("discard")

    if re.search(r"search your deck", action):
        tags.append("tutor")

    if re.search(r"gain \d+ lore", action):
        tags.append("lore_gain")

    if re.search(r"look at the top \d+", action):
        tags.append("scry")

    if re.search(r"costs? \d+ (ink )?less", action) or re.search(r"you pay \d+ less", action):
        tags.append("cost_reduction")

    if re.search(r"gets? \+\d+ (strength|willpower)", action):
        tags.append("stat_boost")

    if re.search(r"put .{0,40} into (your )?inkwell", action):
        tags.append("ink_ramp")

    # --- Stats-based tags ---
    if card_type == "song":
        tags.append("song")

    if inkwell == 0 or inkwell is False:
        tags.append("non_inkable")

    if cost is not None and stars is not None:
        try:
            c, s = int(cost), int(stars)
            if c <= 2 and s >= 2:
                tags.append("high_quester")
            if c > 0 and (s / c) >= 1.0:
                tags.append("efficient_quester")
        except (TypeError, ValueError, ZeroDivisionError):
            pass

    if defence is not None:
        try:
            if int(defence) >= 5:
                tags.append("tank")
        except (TypeError, ValueError):
            pass

    if attack is not None and defence is not None:
        try:
            if int(attack) >= 5 and int(defence) <= 2:
                tags.append("glass_cannon")
        except (TypeError, ValueError):
            pass

    return tags
