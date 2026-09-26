from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

CARD_TYPES = {"force", "bond", "name", "story", "stratagem"}
_TYPE_ALIASES = {
    "subject": "force",
    "link": "bond",
    "plot": "story",
}

FORCE_ROLES = {
    "swordsman",
    "spearman",
    "archer",
    "healer",
    "ship",
    "stronghold",
    "skirmisher",
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

RULE_BLOCK_KINDS = {"property", "timing", "trigger", "effect", "continuous", "cost", "replacement"}

# This is the data contract accepted by the canonical engine, not an
# implementation of the effects. Unknown keys must fail rather than silently
# turn a misspelled rule into a vanilla card. Numeric card fields are packed as
# signed bytes by the engine.
RANKS = {"front", "rear"}
_NONNEGATIVE = range(128)
_SIGNED = range(-128, 128)
_COMPLETION = {
    "effect": {"gain_command", "grant_free_cycle", "draw_card", "reveal_enemy_scheme", "recover_recent_link"},
    "amount": _NONNEGATIVE,
}
_SCHEME = {
    "trigger": {"opponent_plays_subject", "opponent_plays_link", "opponent_passes", "opponent_plot_targets_your_card", "never"},
    "effect": {"penalize_played_subject", "discard_played_link", "reinforce_front", "none"},
    "amount": _NONNEGATIVE,
    "face_down_front_bonus": _NONNEGATIVE,
    "requires_own_subject": bool,
}
_STRATAGEM = {
    "trigger": {
        "event": {"subject_played", "pass", "immediate_story_played", "name_played", "played", "never"},
        "actor": {"either", "opponent", "controller"},
        "roles": [FORCE_ROLES],
        "ranks": [RANKS],
    },
    "reveal_effect": {"effect": {"penalize_trigger_subject"}, "amount": _NONNEGATIVE, "cancel_story": bool},
    "continuous": {
        "role_strength_modifiers": {role: _SIGNED for role in FORCE_ROLES},
        "rank_strength_modifiers": {rank: _SIGNED for rank in RANKS},
        "controller_rank_strength_modifiers": {rank: _SIGNED for rank in RANKS},
        "named_subject_modifier": _SIGNED,
        "unnamed_subject_modifier": _SIGNED,
        "disable_line_defense": bool,
        "controller_immediate_story_lock": bool,
        "global_immediate_story_lock": bool,
    },
}
_RULE_SCHEMAS = {
    "force": {
        "placement": {"rank": RANKS},
        "on_link_attached": {"temporary_strength": _SIGNED},
        "adjacent_strength_aura": _SIGNED,
        "aura_requires_rank": RANKS,
        "strength_modifiers": [{
            "amount": _SIGNED,
            "when": {"own_discard_at_least": _NONNEGATIVE, "adjacent_subject_has_name": bool},
        }],
    },
    "bond": {
        "strength_bonus": _SIGNED,
        "named_strength_bonus": _SIGNED,
        "opposing_front_modifier": _SIGNED,
        "protect_subject_from_opponent_plot": bool,
        "discard_strength_bonus": {"per_card": _NONNEGATIVE, "maximum": _NONNEGATIVE},
    },
    "name": {
        "rank_strength_bonus": {"rank": RANKS, "amount": _SIGNED},
        "on_name_attached": {"move_adjacent_optional", "reveal_enemy_scheme"},
        "on_completion": _COMPLETION,
        "adjacent_command_discount": _NONNEGATIVE,
        "complete_protection_from_opponent_plot": bool,
    },
    "story": {"effect": {"discredit_subject", "return_name_or_weaken", "move_subject"}, "scheme": _SCHEME},
    "stratagem": {"stratagem": _STRATAGEM},
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
            raise ValueError(f"{path}: must be an integer between {schema.start} and {schema.stop - 1}")
    elif not isinstance(value, str) or value not in schema:
        raise ValueError(f"{path}: unsupported value {value!r}")


def _require_fields(value: dict[str, Any], fields: tuple[str, ...], path: str) -> None:
    missing = set(fields) - value.keys()
    if missing:
        raise ValueError(f"{path}: missing required fields: {', '.join(sorted(missing))}")


def _validate_rules(card: dict[str, Any]) -> None:
    rules = card["rules"]
    path = f"{card['id']}.rules"
    _validate_rule_value(rules, _RULE_SCHEMAS[card["type"]], path)
    for key, fields in {
        "placement": ("rank",),
        "on_link_attached": ("temporary_strength",),
        "rank_strength_bonus": ("rank", "amount"),
        "discard_strength_bonus": ("per_card", "maximum"),
        "on_completion": ("effect",),
        "scheme": ("trigger", "effect"),
        "stratagem": ("trigger",),
    }.items():
        if key in rules:
            _require_fields(rules[key], fields, f"{path}.{key}")
    modifiers = rules.get("strength_modifiers", [])
    if len(modifiers) > 1:
        raise ValueError(f"{path}.strength_modifiers: the engine supports at most one modifier")
    for modifier in modifiers:
        _require_fields(modifier, ("amount", "when"), f"{path}.strength_modifiers")
        if not modifier["when"]:
            raise ValueError(f"{path}.strength_modifiers: a condition is required")
    if card["type"] == "stratagem":
        _require_fields(rules, ("stratagem",), path)
        _require_fields(rules["stratagem"]["trigger"], ("event",), f"{path}.stratagem.trigger")
    if card["type"] == "story":
        if card.get("ongoing", False):
            # Old veiled Story data is accepted only as a public ongoing Story
            # compatibility representation while cards are being redesigned.
            if "scheme" in rules:
                _require_fields(rules, ("scheme",), path)
        elif "scheme" in rules:
            raise ValueError(f"{path}: ongoing Story rules require ongoing=true")


def normalize_card_data(data: dict[str, Any]) -> dict[str, Any]:
    """Return canonical in-memory card data without rewriting source files."""
    normalized = copy.deepcopy(data)
    for card in normalized.get("cards", []):
        raw_type = card.get("type")
        card["type"] = _TYPE_ALIASES.get(raw_type, raw_type)
        if card.get("type") == "story":
            if "ongoing" not in card:
                card["ongoing"] = bool(card.get("veiled", False))
        if card.get("type") == "force" and card.get("hero"):
            classes = card.get("classes", [])
            if "hero" not in classes:
                classes.append("hero")
    return normalized


def load_card_file(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    with path.open("r", encoding="utf-8") as handle:
        data = normalize_card_data(json.load(handle))
    validate_card_data(data)
    return data


def validate_card_data(data: dict[str, Any]) -> None:
    data = normalize_card_data(data)
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
        _require_fields(card, ("id", "title", "type", "unique", "classes", "text", "rules", "rule_blocks"), "card")
        card_id = card.get("id")
        title = card.get("title")
        card_type = card.get("type")

        if not isinstance(card_id, str) or not card_id.strip() or card_id != card_id.strip():
            raise ValueError("Every card requires a non-empty id")
        if card_id in seen_ids:
            raise ValueError(f"Duplicate card id: {card_id}")
        seen_ids.add(card_id)

        if not isinstance(title, str) or not title.strip():
            raise ValueError(f"{card_id}: missing title")
        if not isinstance(card_type, str) or card_type not in CARD_TYPES:
            raise ValueError(f"{card_id}: invalid card type {card_type!r}")
        if not isinstance(card.get("unique"), bool):
            raise ValueError(f"{card_id}: unique must be boolean")
        if not isinstance(card["text"], str):
            raise ValueError(f"{card_id}: text must be a string")
        if "command_cost" in card:
            _validate_rule_value(card["command_cost"], range(1, 128), f"{card_id}.command_cost")

        classes = card.get("classes")
        if (
            not isinstance(classes, list)
            or not classes
            or any(not isinstance(value, str) or not value.strip() for value in classes)
        ):
            raise ValueError(f"{card_id}: classes must be a non-empty list of strings")
        if len(classes) != len(set(classes)):
            raise ValueError(f"{card_id}: classes must not contain duplicates")

        hero = card.get("hero", False)
        if not isinstance(hero, bool):
            raise ValueError(f"{card_id}: hero must be boolean when present")
        if hero:
            if card_type != "force":
                raise ValueError(f"{card_id}: only Forces may be Heroes")
            if card.get("unique") is not True:
                raise ValueError(f"{card_id}: every Hero must be Unique")
            if "hero" not in classes:
                raise ValueError(f"{card_id}: Hero classification is required")
            if "hero_name_strength" not in card:
                raise ValueError(f"{card_id}: Hero requires hero_name_strength")
            _validate_rule_value(
                card["hero_name_strength"],
                _NONNEGATIVE,
                f"{card_id}.hero_name_strength",
            )

        rule_blocks = card["rule_blocks"]
        if not isinstance(rule_blocks, list):
            raise ValueError(f"{card_id}: rule_blocks must be a list")
        for block in rule_blocks:
            if not isinstance(block, dict):
                raise ValueError(f"{card_id}: rule_blocks entries must be objects")
            if not isinstance(block.get("kind"), str) or block["kind"] not in RULE_BLOCK_KINDS:
                raise ValueError(f"{card_id}: invalid rule block kind {block.get('kind')!r}")
            if not isinstance(block.get("text"), str) or not block["text"].strip():
                raise ValueError(f"{card_id}: rule block text must be non-empty")

        if card_type == "force":
            role = card.get("role")
            if role is not None and (
                not isinstance(role, str)
                or not role.strip()
                or role != role.strip()
            ):
                raise ValueError(f"{card_id}: Force role must be a non-empty string when present")

        if card_type == "story":
            form = card.get("story_form")
            if not isinstance(form, str) or form not in STORY_FORMS:
                raise ValueError(f"{card_id}: invalid Story form {form!r}")
            if not isinstance(card.get("ongoing"), bool):
                raise ValueError(f"{card_id}: Story ongoing must be boolean")

        if card_type in {"force", "name"}:
            _validate_rule_value(card.get("strength"), _NONNEGATIVE, f"{card_id}.strength")

        if card_type == "name" and card.get("unique") is not True:
            raise ValueError(f"{card_id}: every Name must be Unique")
        _validate_rules(card)


def cards_by_type(data: dict[str, Any], card_type: str) -> list[dict[str, Any]]:
    canonical = _TYPE_ALIASES.get(card_type, card_type)
    return [card for card in normalize_card_data(data)["cards"] if card["type"] == canonical]


def card_index(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    normalized = normalize_card_data(data)
    return {card["id"]: card for card in normalized["cards"]}
