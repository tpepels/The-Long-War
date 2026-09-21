from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CARD_TYPES = {"subject", "link", "name", "plot"}


def load_card_file(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    validate_card_data(data)
    return data


def validate_card_data(data: dict[str, Any]) -> None:
    if data.get("schema_version") != 1:
        raise ValueError("Unsupported card schema_version")

    cards = data.get("cards")
    if not isinstance(cards, list) or not cards:
        raise ValueError("cards must be a non-empty list")

    seen_ids: set[str] = set()
    for card in cards:
        card_id = card.get("id")
        title = card.get("title")
        card_type = card.get("type")

        if not isinstance(card_id, str) or not card_id:
            raise ValueError("Every card requires a non-empty id")
        if card_id in seen_ids:
            raise ValueError(f"Duplicate card id: {card_id}")
        seen_ids.add(card_id)

        if not isinstance(title, str) or not title:
            raise ValueError(f"{card_id}: missing title")
        if card_type not in CARD_TYPES:
            raise ValueError(f"{card_id}: invalid card type {card_type!r}")
        if not isinstance(card.get("unique"), bool):
            raise ValueError(f"{card_id}: unique must be boolean")

        if card_type in {"subject", "name"}:
            strength = card.get("strength")
            if not isinstance(strength, int) or strength < 0:
                raise ValueError(f"{card_id}: subject/name strength must be a non-negative integer")

        if card_type == "name" and card.get("unique") is not True:
            raise ValueError(f"{card_id}: every Name must be Unique")


def cards_by_type(data: dict[str, Any], card_type: str) -> list[dict[str, Any]]:
    return [card for card in data["cards"] if card["type"] == card_type]


def card_index(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {card["id"]: card for card in data["cards"]}
