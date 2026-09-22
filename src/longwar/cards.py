from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CARD_TYPES = {"subject", "link", "name", "plot", "stratagem"}

SUBJECT_ROLES = {
    "swordsman",
    "spearman",
    "archer",
    "healer",
    "ship",
    "stronghold",
}

STORY_FORMS = {
    "legend",
    "myth",
    "saga",
    "omen",
    "prophecy",
    "warning",
    "conspiracy",
}

RULE_BLOCK_KINDS = {"property", "timing", "trigger", "effect", "continuous"}


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

        classes = card.get("classes")
        if (
            not isinstance(classes, list)
            or not classes
            or any(not isinstance(value, str) or not value for value in classes)
        ):
            raise ValueError(f"{card_id}: classes must be a non-empty list of strings")
        if len(classes) != len(set(classes)):
            raise ValueError(f"{card_id}: classes must not contain duplicates")

        hero = card.get("hero", False)
        if not isinstance(hero, bool):
            raise ValueError(f"{card_id}: hero must be boolean when present")
        if hero:
            if card_type != "subject":
                raise ValueError(f"{card_id}: only Subjects may be Heroes")
            if card.get("unique") is not True:
                raise ValueError(f"{card_id}: every Hero must be Unique")
            if "hero" not in classes:
                raise ValueError(f"{card_id}: Hero classification is required")

        rule_blocks = card.get("rule_blocks", [])
        if not isinstance(rule_blocks, list):
            raise ValueError(f"{card_id}: rule_blocks must be a list")
        for block in rule_blocks:
            if not isinstance(block, dict):
                raise ValueError(f"{card_id}: rule_blocks entries must be objects")
            if block.get("kind") not in RULE_BLOCK_KINDS:
                raise ValueError(f"{card_id}: invalid rule block kind {block.get('kind')!r}")
            if not isinstance(block.get("text"), str) or not block["text"]:
                raise ValueError(f"{card_id}: rule block text must be non-empty")

        if card_type == "subject":
            role = card.get("role")
            if role not in SUBJECT_ROLES:
                raise ValueError(f"{card_id}: invalid Subject role {role!r}")

        if card_type == "plot":
            form = card.get("story_form")
            if form not in STORY_FORMS:
                raise ValueError(f"{card_id}: invalid Story form {form!r}")
            if not isinstance(card.get("veiled"), bool):
                raise ValueError(f"{card_id}: Story veiled must be boolean")

        if card_type == "stratagem":
            stratagem = card.get("rules", {}).get("stratagem")
            if not isinstance(stratagem, dict):
                raise ValueError(f"{card_id}: Stratagem rules are required")
            trigger = stratagem.get("trigger")
            if not isinstance(trigger, dict) or not isinstance(trigger.get("event"), str):
                raise ValueError(f"{card_id}: Stratagem requires a trigger event")

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
