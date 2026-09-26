from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

CARD_TYPES = {"force", "bond", "name", "story", "stratagem"}

FORCE_ROLES = {
    "swordsman",
    "spearman",
    "archer",
    "healer",
    "ship",
    "stronghold",
    "skirmisher",
}

NARRATIVE_FORMS = {
    "legend",
    "myth",
    "saga",
    "omen",
    "prophecy",
    "warning",
    "conspiracy",
}

RULE_BLOCK_KINDS = {
    "property",
    "timing",
    "trigger",
    "effect",
    "continuous",
    "cost",
    "replacement",
}

RANKS = {"front", "rear"}
_NONNEGATIVE = range(128)
_SIGNED = range(-128, 128)

_RULE_SCHEMAS: dict[str, dict[str, Any]] = {
    "force": {
        "placement": {"rank": RANKS},
    },
    "bond": {
        "strength_bonus": _SIGNED,
        "named_strength_bonus": _SIGNED,
    },
    "name": {
        "on_completion": {
            "effect": {"gain_command", "draw_card"},
            "amount": _NONNEGATIVE,
        },
    },
    "story": {},
    "stratagem": {},
}


def _validate_rule_value(value: Any, schema: Any, path: str) -> None:
    if isinstance(schema, dict):
        if not isinstance(value, dict):
            raise ValueError(f"{path}: must be an object")
        for key, item in value.items():
            if key not in schema:
                raise ValueError(f"{path}: unsupported rule {key!r}")
            _validate_rule_value(item, schema[key], f"{path}.{key}")
    elif isinstance(schema, list):
        if not isinstance(value, list):
            raise ValueError(f"{path}: must be a list")
        for index, item in enumerate(value):
            _validate_rule_value(item, schema[0], f"{path}[{index}]")
    elif schema is bool:
        if type(value) is not bool:
            raise ValueError(f"{path}: must be boolean")
    elif isinstance(schema, range):
        if type(value) is not int or value not in schema:
            raise ValueError(
                f"{path}: must be an integer between {schema.start} and {schema.stop - 1}"
            )
    elif not isinstance(value, str) or value not in schema:
        raise ValueError(f"{path}: unsupported value {value!r}")


def _require_fields(value: dict[str, Any], fields: tuple[str, ...], path: str) -> None:
    missing = set(fields) - value.keys()
    if missing:
        raise ValueError(
            f"{path}: missing required fields: {', '.join(sorted(missing))}"
        )


def _validate_rules(card: dict[str, Any]) -> None:
    rules = card["rules"]
    path = f"{card['id']}.rules"
    _validate_rule_value(rules, _RULE_SCHEMAS[card["type"]], path)

    if "placement" in rules:
        _require_fields(rules["placement"], ("rank",), f"{path}.placement")
    if "on_completion" in rules:
        _require_fields(
            rules["on_completion"],
            ("effect", "amount"),
            f"{path}.on_completion",
        )


def normalize_card_data(data: dict[str, Any]) -> dict[str, Any]:
    """Return an isolated copy of canonical card data."""
    return copy.deepcopy(data)


def load_card_file(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    validate_card_data(data)
    return normalize_card_data(data)


def validate_card_data(data: dict[str, Any]) -> None:
    if not isinstance(data, dict):
        raise ValueError("Card data must be an object")
    if type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        raise ValueError("Unsupported card schema_version")

    cards = data.get("cards")
    if not isinstance(cards, list) or not cards:
        raise ValueError("cards must be a non-empty list")

    seen_ids: set[str] = set()
    for card in cards:
        if not isinstance(card, dict):
            raise ValueError("Every card must be an object")

        _require_fields(
            card,
            (
                "id",
                "title",
                "type",
                "unique",
                "classes",
                "text",
                "rules",
                "rule_blocks",
            ),
            "card",
        )

        card_id = card["id"]
        title = card["title"]
        card_type = card["type"]

        if not isinstance(card_id, str) or not card_id.strip() or card_id != card_id.strip():
            raise ValueError("Every card requires a non-empty id")
        if card_id in seen_ids:
            raise ValueError(f"Duplicate card id: {card_id}")
        seen_ids.add(card_id)

        if not isinstance(title, str) or not title.strip():
            raise ValueError(f"{card_id}: missing title")
        if not isinstance(card_type, str) or card_type not in CARD_TYPES:
            raise ValueError(f"{card_id}: invalid card type {card_type!r}")
        if not isinstance(card["unique"], bool):
            raise ValueError(f"{card_id}: unique must be boolean")
        if not isinstance(card["text"], str):
            raise ValueError(f"{card_id}: text must be a string")

        if "command_cost" in card:
            _validate_rule_value(
                card["command_cost"],
                range(1, 128),
                f"{card_id}.command_cost",
            )

        classes = card["classes"]
        if (
            not isinstance(classes, list)
            or not classes
            or any(
                not isinstance(value, str) or not value.strip()
                for value in classes
            )
        ):
            raise ValueError(
                f"{card_id}: classes must be a non-empty list of strings"
            )
        if len(classes) != len(set(classes)):
            raise ValueError(f"{card_id}: classes must not contain duplicates")

        hero = card.get("hero", False)
        if not isinstance(hero, bool):
            raise ValueError(f"{card_id}: hero must be boolean when present")
        if hero:
            if card_type != "force":
                raise ValueError(f"{card_id}: only Forces may be Heroes")
            if card["unique"] is not True:
                raise ValueError(f"{card_id}: every Hero must be Unique")
            if "hero" not in classes:
                raise ValueError(f"{card_id}: Hero classification is required")
            _validate_rule_value(
                card.get("hero_name_strength"),
                _NONNEGATIVE,
                f"{card_id}.hero_name_strength",
            )

        rule_blocks = card["rule_blocks"]
        if not isinstance(rule_blocks, list):
            raise ValueError(f"{card_id}: rule_blocks must be a list")
        for block in rule_blocks:
            if not isinstance(block, dict):
                raise ValueError(
                    f"{card_id}: rule_blocks entries must be objects"
                )
            if (
                not isinstance(block.get("kind"), str)
                or block["kind"] not in RULE_BLOCK_KINDS
            ):
                raise ValueError(
                    f"{card_id}: invalid rule block kind {block.get('kind')!r}"
                )
            if (
                not isinstance(block.get("text"), str)
                or not block["text"].strip()
            ):
                raise ValueError(
                    f"{card_id}: rule block text must be non-empty"
                )

        if card_type == "force":
            role = card.get("role")
            if role is not None and (
                not isinstance(role, str)
                or not role.strip()
                or role != role.strip()
            ):
                raise ValueError(
                    f"{card_id}: Force role must be a non-empty string when present"
                )

        if card_type == "story":
            form = card.get("narrative_form")
            if not isinstance(form, str) or form not in NARRATIVE_FORMS:
                raise ValueError(
                    f"{card_id}: invalid Narrative form {form!r}"
                )
            if not isinstance(card.get("ongoing"), bool):
                raise ValueError(
                    f"{card_id}: Narrative ongoing must be boolean"
                )

        if card_type in {"force", "name"}:
            _validate_rule_value(
                card.get("strength"),
                _NONNEGATIVE,
                f"{card_id}.strength",
            )

        if card_type == "name" and card["unique"] is not True:
            raise ValueError(f"{card_id}: every Name must be Unique")

        _validate_rules(card)


def cards_by_type(
    data: dict[str, Any],
    card_type: str,
) -> list[dict[str, Any]]:
    if card_type not in CARD_TYPES:
        raise ValueError(f"Unknown card type: {card_type}")
    return [
        card
        for card in data["cards"]
        if card["type"] == card_type
    ]


def card_index(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {card["id"]: card for card in data["cards"]}
