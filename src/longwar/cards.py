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
    "constraint",
    "cost",
    "replacement",
}

RANKS = {"front", "rear"}
_NONNEGATIVE = range(128)
_SIGNED = range(-128, 128)

# design_rules is executable card data, not free-form design prose. Keep its
# vocabulary explicit so ordinary cards can reuse existing mechanics without
# touching engine code, while typos and genuinely new mechanics fail at load
# time instead of silently compiling to no behavior.
_DESIGN_OBJECT_PATHS = {
    "after_maneuver",
    "after_maneuver_into_empty",
    "after_maneuver_swap",
    "at_battle_end",
    "force",
    "force.after_maneuver",
    "front_resolution",
    "lost_front",
    "name",
    "name.on_completion",
    "on_completion",
    "on_play_onto_force",
}

_DESIGN_BOOL_PATHS = {
    "abandoned_front_strength_ignored",
    "accumulates",
    "can_maneuver_while_unnamed",
    "cannot_be_swap_target",
    "choose_direction",
    "choose_friendly_named_formation",
    "chosen_edge_front",
    "chosen_front",
    "chosen_front_requires_friendly_named_formation",
    "destination_must_have_been_empty_before_effect",
    "discard_after_both_players_trigger",
    "at_battle_end.discard_self",
    "discard_after_next_turn_constraint",
    "discard_self",
    "discard_when_named_formation_retreated",
    "first_maneuver_each_player_must_use_direction_if_possible",
    "force.can_maneuver_while_unnamed",
    "formations_cannot_maneuver_away_from_chosen_front",
    "immobile",
    "later_maneuvers_same_direction_if_possible",
    "lost_front.if_frontline_friendly_named",
    "move_any_number",
    "maneuver_while_unnamed",
    "named_formations_cannot_maneuver_away",
    "next_battle_first_operation_must_be_maneuver_if_possible",
    "next_operation_each_player_must_affect_chosen_front_if_possible",
    "next_operation_must_affect_chosen_front_if_possible",
    "next_turn_forced_maneuver_if_legal",
    "per_player_first_card_in_front_each_battle",
    "prevent_opponent_card_effect_move_into_front_from_adjacent",
    "prevent_opponent_card_effect_movement",
    "same_rank",
    "strength_cannot_be_ignored_by_opponent",
    "unnamed_formations_can_maneuver",
}

_DESIGN_INT_PATHS = {
    "additional_move_extra_cost",
    "additional_strength_after_first_maneuver_this_battle",
    "adjacent_front_formation_strength_bonus",
    "amount",
    "at_battle_end.gain_command",
    "chosen_fronts",
    "cost",
    "discard_cards",
    "discounted_cost",
    "distance_fronts",
    "draw_after_forced_maneuver",
    "draw_cards",
    "extra_cost",
    "first_card_each_turn_discount",
    "first_maneuver_each_battle_cost",
    "first_maneuver_each_player_cost",
    "first_move_extra_cost",
    "first_self_maneuver_each_battle_cost",
    "force.amount",
    "forced_maneuver_cost",
    "friendly_named_maneuver_cost",
    "gain_command",
    "lost_front_adjustment",
    "maneuver_cost",
    "minimum_cost",
    "named_additional_strength_bonus",
    "named_strength_bonus",
    "normal_cost",
    "on_completion.gain_command",
    "open_bond_strength_bonus",
    "strength_bonus",
}

_DESIGN_STRING_VALUES: dict[str, set[str]] = {
    "affected_player": {"player_who_won_at_least_three_fronts"},
    "affects": {"both_players"},
    "after_maneuver.effect": {
        "optional_swap_two_adjacent_friendly_formations_excluding_self",
    },
    "after_maneuver_into_empty.effect": {
        "optional_move_adjacent_friendly_to_vacated_position",
    },
    "after_maneuver_swap.effect": {
        "optional_zero_cost_maneuver_swapped_formation",
    },
    "after_self_maneuver": {
        "optional_zero_cost_other_friendly_named_maneuver",
    },
    "at_battle_end.bonus_if_won": {"return_one_bond_from_discard_to_hand"},
    "at_battle_end.condition": {
        "chosen_front_not_lost",
        "chosen_front_won",
        "chosen_formation_still_on_battlefield",
    },
    "at_battle_end.secondary": {"draw_1"},
    "baseline_force": {"vanilla"},
    "build_around": {
        "empty_front",
        "hero_retinue",
        "narrative",
        "open_bond",
        "open_bond_transfer",
        "prepared_position",
        "succession",
        "wide_line",
    },
    "combat": {
        "breakthrough",
        "capture",
        "first_strike",
        "frontline_only_comparison",
        "interception",
        "sacrifice",
        "skirmish",
        "tie_control",
    },
    "command": {
        "card_for_command",
        "catch_up_discount",
        "completion_discount",
        "completion_refund",
        "high_cost_battle_investment",
        "improve_recovery",
        "local_catch_up_discount",
        "optional_extra_payment",
    },
    "condition": {
        "adjacent_friendly_formation_contains_hero",
        "bond_is_open",
        "controller_command_lower_than_opponent",
        "controller_has_front_with_no_force",
        "friendly_force_in_all_four_fronts",
        "front_tied_and_exactly_one_side_has_frontline_named",
        "has_bond_and_no_name",
        "played_on_force_with_bond",
        "win_front_and_opponent_rear_has_no_force",
        "win_middle_and_both_adjacent_fronts",
    },
    "deploy_rank": RANKS,
    "destination": {"empty_frontline_same_front"},
    "duration": {"battle", "until_each_player_completes_next_operation_or_battle_ends"},
    "effect": {
        "chosen_opposing_formation_does_not_contribute_this_resolution",
        "drive_off_opposing_frontline_named_instead_of_retreat",
        "draw_2",
        "ignore_rear_formations_when_comparing_strength",
        "losing_frontline_named_driven_off_instead_of_retreating",
        "middle_opposing_frontline_named_driven_off_instead_of_retreating",
        "next_maneuver_cost_zero_this_battle",
        "optional_move_into_vacated_position",
        "optional_move_this_bond_to_adjacent_friendly_force_without_bond",
        "optional_swap_friendly_frontline_and_rear_formations_one_front",
        "optional_zero_cost_friendly_named_maneuver",
        "optional_zero_cost_maneuver_even_if_unnamed",
        "optional_zero_cost_maneuver_this_formation",
        "return_retreating_formation_bond_to_owner_hand",
        "suppress_opposing_rear_force_for_resolution",
        "target_does_not_contribute_this_resolution",
        "that_side_wins_front",
    },
    "force.after_frontline_retreat": {"optional_sideways_rear_move"},
    "force.after_maneuver.effect": {
        "free_maneuver_adjacent_friendly_named_formation",
    },
    "force.after_maneuver_into_empty": {
        "optional_move_one_more_front_if_empty",
    },
    "force.combat": {"optional_ignore_opposing_rear_strength"},
    "force.command": {
        "frontline_force_discount_1_min_1",
        "lost_front_here_does_not_reduce_recovery",
    },
    "force.deploy_rank": RANKS,
    "force.effect": {
        "optional_drive_off_self_prevent_frontline_named_retreat",
    },
    "force.on_play": {"optional_take_adjacent_prepared_bond_or_name"},
    "force.printed_role_effect": {"frontline_strength_bonus"},
    "force.story": {"first_story_each_battle_discount_1_min_1"},
    "front_resolution.choose": {"own_or_adjacent_front"},
    "front_resolution.contribution": {"chosen_front_instead_of_own"},
    "identity": {
        "frontline_people",
        "mobile_people",
        "named_people",
        "open_bond_people",
        "steadfast_people",
    },
    "lost_front.effect": {"drive_off_self_prevent_frontline_retreat"},
    "name.after_self_retreat": {"optional_sideways_rear_move"},
    "name.combat": {"breakthrough_if_opponent_no_rear_force"},
    "name.command": {"first_card_in_front_each_battle_discount_1_min_1"},
    "name.effect": {
        "optional_zero_cost_maneuver",
        "return_hero_to_hand_if_driven_off",
    },
    "name.on_completion": {
        "return_one_bond_from_discard_to_hand",
        "return_one_story_from_discard_to_hand",
    },
    "name.on_completion.effect": {"free_maneuver_self"},
    "name.on_play": {"optional_take_adjacent_open_bond"},
    "name.trigger": {"opponent_maneuvers_into_adjacent_front"},
    "narrative_form": NARRATIVE_FORMS,
    "on_completion.effect": {"optional_swap_adjacent_friendly_formation"},
    "on_play_condition": {"position_has_prepared_bond_or_name"},
    "on_play_onto_force.effect": {
        "optional_move_formation_adjacent_empty_position",
    },
    "outcome": {"higher_combined_strength_wins_both"},
    "persistence": {
        "bond_returns_to_hand_when_force_driven_off",
        "inherited_bond",
        "name_returns_to_hand_when_formation_driven_off",
        "rear_rebuild_cost_reduction",
        "retreat_command_compensation",
        "retreat_sideways",
        "start_battle_reposition",
        "voluntary_retreat_if_rear_empty",
    },
    "placement": {"chosen_front", "chosen_named_formation"},
    "printed_role_effect": {
        "frontline_strength_bonus",
        "frontline_strength_bonus_if_force_behind",
        "rear_strength_bonus",
        "rear_strength_bonus_if_force_ahead",
        "support_force_ahead_strength_bonus",
    },
    "replacement": {
        "optional_move_name_to_adjacent_friendly_force_with_bond_no_name",
        "this_formation_does_not_contribute_instead",
    },
    "restriction": {"chosen_direction"},
    "role": FORCE_ROLES,
    "scope": {"this_formation", "this_front"},
    "secondary": {
        "optional_move_adjacent_friendly_into_vacated_position",
        "optional_sideways_rear_move",
        "optional_zero_cost_friendly_named_maneuver",
        "optional_zero_cost_maneuver_that_formation",
    },
    "stratagem": {
        "all_reserves_forward",
        "battle_turns_direction",
        "combine_two_adjacent_fronts",
        "encirclement",
        "every_banner_turned",
        "feigned_retreat",
        "line_begun_to_move",
        "no_retreat_front",
        "no_road_back",
        "refuse_flank",
        "wheel_line",
    },
    "target": {"opposing_frontline_force_with_lower_printed_strength"},
    "timing": {
        "after_retreat",
        "after_retreat_resolves",
        "battle_end_before_strength_comparison",
    },
    "trigger": {
        "adjacent_friendly_formation_retreats",
        "adjacent_friendly_named_formation_maneuvers_away",
        "battle_end_player_won_at_least_three_fronts",
        "first_friendly_maneuver_into_empty_each_battle",
        "force_moves_or_maneuvers",
        "formation_driven_off",
        "friendly_formation_becomes_named",
        "friendly_named_formation_retreats",
        "opponent_effect_would_prevent_other_friendly_formation_contribution",
        "opponent_has_force_in_both_ranks_same_front",
        "opposing_formation_becomes_named",
        "opposing_formation_in_same_front_becomes_named",
        "opposing_formation_maneuvers_into_same_front",
        "own_front_wins_and_opposing_frontline_named_retreats",
        "regain_command_from_narrative",
    },
}

_DESIGN_LIST_VALUES: dict[str, set[str]] = {
    "direction_choice": {"left", "right"},
}


def _validate_design_rule_value(value: Any, path: str, card_id: str) -> None:
    location = f"{card_id}.design_rules.{path}"

    # Two established mechanics deliberately accept either a shorthand scalar
    # or a structured form. Keep that compatibility explicit rather than
    # weakening validation for every design-rule path.
    if path == "cost":
        if (
            (type(value) is int and value in _SIGNED)
            or value == "discard_own_force_and_all_attached_cards"
        ):
            return
        raise ValueError(f"{location}: unsupported value {value!r}")
    if path == "name.on_completion" and isinstance(value, str):
        if value in _DESIGN_STRING_VALUES[path]:
            return
        raise ValueError(f"{location}: unsupported value {value!r}")

    if path in _DESIGN_OBJECT_PATHS:
        if not isinstance(value, dict):
            raise ValueError(f"{location}: must be an object")
        for key, item in value.items():
            _validate_design_rule_value(item, f"{path}.{key}", card_id)
        return
    if path in _DESIGN_BOOL_PATHS:
        if type(value) is not bool:
            raise ValueError(f"{location}: must be boolean")
        return
    if path in _DESIGN_INT_PATHS:
        if type(value) is not int or value not in _SIGNED:
            raise ValueError(
                f"{location}: must be an integer between "
                f"{_SIGNED.start} and {_SIGNED.stop - 1}"
            )
        return
    if path in _DESIGN_STRING_VALUES:
        allowed = _DESIGN_STRING_VALUES[path]
        if not isinstance(value, str) or value not in allowed:
            raise ValueError(f"{location}: unsupported value {value!r}")
        return
    if path in _DESIGN_LIST_VALUES:
        allowed = _DESIGN_LIST_VALUES[path]
        if (
            not isinstance(value, list)
            or not value
            or any(not isinstance(item, str) or item not in allowed for item in value)
            or len(value) != len(set(value))
        ):
            raise ValueError(f"{location}: unsupported list {value!r}")
        return
    raise ValueError(f"{location}: unsupported mechanic")


def _validate_design_rules(card: dict[str, Any]) -> None:
    design = card.get("design_rules")
    if design is None:
        return
    if not isinstance(design, dict):
        raise ValueError(f"{card['id']}.design_rules: must be an object")
    for key, value in design.items():
        _validate_design_rule_value(value, key, card["id"])


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


CARD_CAPABILITY_BITS = {
    "adjacent_retreat_free_maneuver": 1 << 0,
    "after_frontline_retreat_sideways_force": 1 << 1,
    "after_maneuver_swap_other_friendlies": 1 << 2,
    "after_self_maneuver_free_other_named_if_wide_name": 1 << 3,
    "after_self_retreat_sideways_name": 1 << 4,
    "follow_into_vacated_after_adjacent_maneuver": 1 << 5,
    "narrative_command_gain_free_maneuver_force": 1 << 6,
    "on_play_take_adjacent_open_bond_name": 1 << 7,
    "on_play_take_adjacent_prepared_component_force": 1 << 8,
    "opposing_maneuver_same_front_free_maneuver": 1 << 9,
    "opposing_named_same_front_free_maneuver": 1 << 10,
    "optional_self_drive_prevent_frontline_retreat_force": 1 << 11,
    "prepared_on_play_free_maneuver_force": 1 << 12,
    "succession_on_drive_off_name": 1 << 13,
    "transfer_open_bond_after_move_bond": 1 << 14,
}
CARD_CAPABILITY_NAMES = frozenset(CARD_CAPABILITY_BITS)


def _validate_card_capability_registry() -> None:
    bits = tuple(CARD_CAPABILITY_BITS.values())
    if len(bits) > 64:
        raise RuntimeError("Native card capability bitset supports at most 64 capabilities")
    if len(bits) != len(set(bits)):
        raise RuntimeError("Card capability bits must be unique")
    if any(bit <= 0 or bit & (bit - 1) for bit in bits):
        raise RuntimeError("Card capability values must be single positive bits")
    if bits and max(bits).bit_length() > 64:
        raise RuntimeError("Card capability bit exceeds native uint64 capacity")


_validate_card_capability_registry()


def _compile_card_capabilities(design: dict[str, Any]) -> tuple[str, ...]:
    """Translate reusable design vocabulary into engine capability names."""
    force_design = design.get("force") or design
    name_design = design.get("name") or {}
    capabilities: set[str] = set()

    if design.get("trigger") == "opposing_formation_in_same_front_becomes_named":
        capabilities.add("opposing_named_same_front_free_maneuver")
    if design.get("trigger") == "adjacent_friendly_named_formation_maneuvers_away":
        capabilities.add("follow_into_vacated_after_adjacent_maneuver")
    if design.get("trigger") == "adjacent_friendly_formation_retreats":
        capabilities.add("adjacent_retreat_free_maneuver")
    if (
        (design.get("after_maneuver") or {}).get("effect")
        == "optional_swap_two_adjacent_friendly_formations_excluding_self"
    ):
        capabilities.add("after_maneuver_swap_other_friendlies")
    if design.get("trigger") == "opposing_formation_maneuvers_into_same_front":
        capabilities.add("opposing_maneuver_same_front_free_maneuver")
    if (
        force_design.get("after_frontline_retreat")
        == "optional_sideways_rear_move"
    ):
        capabilities.add("after_frontline_retreat_sideways_force")
    if name_design.get("after_self_retreat") == "optional_sideways_rear_move":
        capabilities.add("after_self_retreat_sideways_name")
    if (
        force_design.get("on_play")
        == "optional_take_adjacent_prepared_bond_or_name"
    ):
        capabilities.add("on_play_take_adjacent_prepared_component_force")
    if name_design.get("on_play") == "optional_take_adjacent_open_bond":
        capabilities.add("on_play_take_adjacent_open_bond_name")
    if (
        force_design.get("effect")
        == "optional_drive_off_self_prevent_frontline_named_retreat"
    ):
        capabilities.add("optional_self_drive_prevent_frontline_retreat_force")
    if design.get("build_around") == "prepared_position":
        capabilities.add("prepared_on_play_free_maneuver_force")
    if (
        design.get("after_self_maneuver")
        == "optional_zero_cost_other_friendly_named_maneuver"
    ):
        capabilities.add("after_self_maneuver_free_other_named_if_wide_name")
    if design.get("trigger") == "regain_command_from_narrative":
        capabilities.add("narrative_command_gain_free_maneuver_force")
    if design.get("build_around") == "open_bond_transfer":
        capabilities.add("transfer_open_bond_after_move_bond")
    if design.get("build_around") == "succession":
        capabilities.add("succession_on_drive_off_name")

    unknown = capabilities - CARD_CAPABILITY_NAMES
    if unknown:
        raise ValueError(
            "Compiler produced unsupported card capabilities: "
            + ", ".join(sorted(unknown))
        )
    return tuple(sorted(capabilities))


def compile_card_mechanics(card: dict[str, Any]) -> dict[str, Any]:
    """Compile one card's executable design vocabulary for the native engine.

    Native code consumes only this validated compiler output, never raw
    design_rules from catalogue JSON. Existing structured design data remains
    available during the migration to reusable capability primitives.
    """
    _validate_design_rules(card)
    design = copy.deepcopy(card.get("design_rules") or {})
    capabilities = _compile_card_capabilities(design)
    design["_capabilities"] = capabilities
    design["_capability_bits"] = sum(
        CARD_CAPABILITY_BITS[capability]
        for capability in capabilities
    )
    return design


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
        _validate_design_rules(card)


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
