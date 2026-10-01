from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from .game.model import Rank
from .protocol import (
    CARD_TYPES,
    FORCE_ROLES,
    NARRATIVE_FORMS,
    RULE_BLOCK_KINDS,
    CardType,
    DesignToken,
)

RANKS = frozenset(rank.value for rank in Rank)
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
    "lost_fronts_protected",
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
    "affected_player": {DesignToken.PLAYER_WHO_WON_AT_LEAST_THREE_FRONTS.value},
    "affects": {DesignToken.BOTH_PLAYERS.value},
    "after_maneuver.effect": {
        DesignToken.OPTIONAL_SWAP_TWO_ADJACENT_FRIENDLY_FORMATIONS_EXCLUDING_SELF.value,
    },
    "after_maneuver_into_empty.effect": {
        DesignToken.OPTIONAL_MOVE_ADJACENT_FRIENDLY_TO_VACATED_POSITION.value,
    },
    "after_maneuver_swap.effect": {
        DesignToken.OPTIONAL_ZERO_COST_MANEUVER_SWAPPED_FORMATION.value,
    },
    "after_self_maneuver": {
        DesignToken.OPTIONAL_ZERO_COST_OTHER_FRIENDLY_NAMED_MANEUVER.value,
    },
    "at_battle_end.bonus_if_won": {DesignToken.RETURN_ONE_BOND_FROM_DISCARD_TO_HAND.value},
    "at_battle_end.condition": {
        DesignToken.CHOSEN_FRONT_NOT_LOST.value,
        DesignToken.CHOSEN_FRONT_WON.value,
        DesignToken.CHOSEN_FORMATION_STILL_ON_BATTLEFIELD.value,
    },
    "at_battle_end.secondary": {DesignToken.DRAW_1.value},
    "baseline_force": {DesignToken.VANILLA.value},
    "build_around": {
        DesignToken.EMPTY_FRONT.value,
        DesignToken.HERO_RETINUE.value,
        DesignToken.NARRATIVE.value,
        DesignToken.OPEN_BOND.value,
        DesignToken.OPEN_BOND_TRANSFER.value,
        DesignToken.PREPARED_POSITION.value,
        DesignToken.SUCCESSION.value,
        DesignToken.WIDE_LINE.value,
    },
    "combat": {
        DesignToken.BREAKTHROUGH.value,
        DesignToken.CAPTURE.value,
        DesignToken.FIRST_STRIKE.value,
        DesignToken.FRONTLINE_ONLY_COMPARISON.value,
        DesignToken.INTERCEPTION.value,
        DesignToken.SACRIFICE.value,
        DesignToken.SKIRMISH.value,
        DesignToken.TIE_CONTROL.value,
    },
    "command": {
        DesignToken.CARD_FOR_COMMAND.value,
        DesignToken.CATCH_UP_DISCOUNT.value,
        DesignToken.COMPLETION_DISCOUNT.value,
        DesignToken.COMPLETION_REFUND.value,
        DesignToken.HIGH_COST_BATTLE_INVESTMENT.value,
        DesignToken.PROTECT_LOST_FRONTS.value,
        DesignToken.LOCAL_CATCH_UP_DISCOUNT.value,
        DesignToken.OPTIONAL_EXTRA_PAYMENT.value,
    },
    "condition": {
        DesignToken.ADJACENT_FRIENDLY_FORMATION_CONTAINS_HERO.value,
        DesignToken.BOND_IS_OPEN.value,
        DesignToken.CONTROLLER_COMMAND_LOWER_THAN_OPPONENT.value,
        DesignToken.CONTROLLER_HAS_FRONT_WITH_NO_FORCE.value,
        DesignToken.FRIENDLY_FORCE_IN_ALL_FOUR_FRONTS.value,
        DesignToken.FRONT_TIED_AND_EXACTLY_ONE_SIDE_HAS_FRONTLINE_NAMED.value,
        DesignToken.HAS_BOND_AND_NO_NAME.value,
        DesignToken.PLAYED_ON_FORCE_WITH_BOND.value,
        DesignToken.WIN_FRONT_AND_OPPONENT_REAR_HAS_NO_FORCE.value,
        DesignToken.WIN_MIDDLE_AND_BOTH_ADJACENT_FRONTS.value,
    },
    "deploy_rank": RANKS,
    "destination": {DesignToken.EMPTY_FRONTLINE_SAME_FRONT.value},
    "duration": {DesignToken.BATTLE.value, DesignToken.UNTIL_EACH_PLAYER_COMPLETES_NEXT_OPERATION_OR_BATTLE_ENDS.value},
    "effect": {
        DesignToken.CHOSEN_OPPOSING_FORMATION_DOES_NOT_CONTRIBUTE_THIS_RESOLUTION.value,
        DesignToken.DRIVE_OFF_OPPOSING_FRONTLINE_NAMED_INSTEAD_OF_RETREAT.value,
        DesignToken.DRAW_2.value,
        DesignToken.IGNORE_REAR_FORMATIONS_WHEN_COMPARING_STRENGTH.value,
        DesignToken.LOSING_FRONTLINE_NAMED_DRIVEN_OFF_INSTEAD_OF_RETREATING.value,
        DesignToken.MIDDLE_OPPOSING_FRONTLINE_NAMED_DRIVEN_OFF_INSTEAD_OF_RETREATING.value,
        DesignToken.NEXT_MANEUVER_COST_ZERO_THIS_BATTLE.value,
        DesignToken.OPTIONAL_MOVE_INTO_VACATED_POSITION.value,
        DesignToken.OPTIONAL_MOVE_THIS_BOND_TO_ADJACENT_FRIENDLY_FORCE_WITHOUT_BOND.value,
        DesignToken.OPTIONAL_SWAP_FRIENDLY_FRONTLINE_AND_REAR_FORMATIONS_ONE_FRONT.value,
        DesignToken.OPTIONAL_ZERO_COST_FRIENDLY_NAMED_MANEUVER.value,
        DesignToken.OPTIONAL_ZERO_COST_MANEUVER_EVEN_IF_UNNAMED.value,
        DesignToken.OPTIONAL_ZERO_COST_MANEUVER_THIS_FORMATION.value,
        DesignToken.RETURN_RETREATING_FORMATION_BOND_TO_OWNER_HAND.value,
        DesignToken.SUPPRESS_OPPOSING_REAR_FORCE_FOR_RESOLUTION.value,
        DesignToken.TARGET_DOES_NOT_CONTRIBUTE_THIS_RESOLUTION.value,
        DesignToken.THAT_SIDE_WINS_FRONT.value,
    },
    "force.after_frontline_retreat": {DesignToken.OPTIONAL_SIDEWAYS_REAR_MOVE.value},
    "force.after_maneuver.effect": {
        DesignToken.FREE_MANEUVER_ADJACENT_FRIENDLY_NAMED_FORMATION.value,
    },
    "force.after_maneuver_into_empty": {
        DesignToken.OPTIONAL_MOVE_ONE_MORE_FRONT_IF_EMPTY.value,
    },
    "force.combat": {DesignToken.OPTIONAL_IGNORE_OPPOSING_REAR_STRENGTH.value},
    "force.command": {
        DesignToken.FRONTLINE_FORCE_DISCOUNT_1_MIN_1.value,
        DesignToken.PROTECT_LOST_FRONT_HERE.value,
    },
    "force.deploy_rank": RANKS,
    "force.effect": {
        DesignToken.OPTIONAL_DRIVE_OFF_SELF_PREVENT_FRONTLINE_NAMED_RETREAT.value,
    },
    "force.on_play": {DesignToken.OPTIONAL_TAKE_ADJACENT_PREPARED_BOND_OR_NAME.value},
    "force.printed_role_effect": {DesignToken.FRONTLINE_STRENGTH_BONUS.value},
    "force.narrative": {DesignToken.FIRST_NARRATIVE_EACH_BATTLE_DISCOUNT_1_MIN_1.value},
    "front_resolution.choose": {DesignToken.OWN_OR_ADJACENT_FRONT.value},
    "front_resolution.contribution": {DesignToken.CHOSEN_FRONT_INSTEAD_OF_OWN.value},
    "identity": {
        DesignToken.FRONTLINE_PEOPLE.value,
        DesignToken.MOBILE_PEOPLE.value,
        DesignToken.NAMED_PEOPLE.value,
        DesignToken.OPEN_BOND_PEOPLE.value,
        DesignToken.STEADFAST_PEOPLE.value,
    },
    "lost_front.effect": {DesignToken.DRIVE_OFF_SELF_PREVENT_FRONTLINE_RETREAT.value},
    "name.after_self_retreat": {DesignToken.OPTIONAL_SIDEWAYS_REAR_MOVE.value},
    "name.combat": {DesignToken.BREAKTHROUGH_IF_OPPONENT_NO_REAR_FORCE.value},
    "name.command": {DesignToken.FIRST_CARD_IN_FRONT_EACH_BATTLE_DISCOUNT_1_MIN_1.value},
    "name.effect": {
        DesignToken.OPTIONAL_ZERO_COST_MANEUVER.value,
        DesignToken.RETURN_HERO_TO_HAND_IF_DRIVEN_OFF.value,
    },
    "name.on_completion": {
        DesignToken.RETURN_ONE_BOND_FROM_DISCARD_TO_HAND.value,
        DesignToken.RETURN_ONE_NARRATIVE_FROM_DISCARD_TO_HAND.value,
    },
    "name.on_completion.effect": {DesignToken.FREE_MANEUVER_SELF.value},
    "name.on_play": {DesignToken.OPTIONAL_TAKE_ADJACENT_OPEN_BOND.value},
    "name.trigger": {DesignToken.OPPONENT_MANEUVERS_INTO_ADJACENT_FRONT.value},
    "narrative_form": NARRATIVE_FORMS,
    "on_completion.effect": {DesignToken.OPTIONAL_SWAP_ADJACENT_FRIENDLY_FORMATION.value},
    "on_play_condition": {DesignToken.POSITION_HAS_PREPARED_BOND_OR_NAME.value},
    "on_play_onto_force.effect": {
        DesignToken.OPTIONAL_MOVE_FORMATION_ADJACENT_EMPTY_POSITION.value,
    },
    "outcome": {DesignToken.HIGHER_COMBINED_STRENGTH_WINS_BOTH.value},
    "persistence": {
        DesignToken.BOND_RETURNS_TO_HAND_WHEN_FORCE_DRIVEN_OFF.value,
        DesignToken.INHERITED_BOND.value,
        DesignToken.NAME_RETURNS_TO_HAND_WHEN_FORMATION_DRIVEN_OFF.value,
        DesignToken.REAR_REBUILD_COST_REDUCTION.value,
        DesignToken.RETREAT_COMMAND_COMPENSATION.value,
        DesignToken.RETREAT_SIDEWAYS.value,
        DesignToken.START_BATTLE_REPOSITION.value,
        DesignToken.VOLUNTARY_RETREAT_IF_REAR_EMPTY.value,
    },
    "placement": {DesignToken.CHOSEN_FRONT.value, DesignToken.CHOSEN_NAMED_FORMATION.value},
    "printed_role_effect": {
        DesignToken.FRONTLINE_STRENGTH_BONUS.value,
        DesignToken.FRONTLINE_STRENGTH_BONUS_IF_FORCE_BEHIND.value,
        DesignToken.REAR_STRENGTH_BONUS.value,
        DesignToken.REAR_STRENGTH_BONUS_IF_FORCE_AHEAD.value,
        DesignToken.SUPPORT_FORCE_AHEAD_STRENGTH_BONUS.value,
    },
    "replacement": {
        DesignToken.OPTIONAL_MOVE_NAME_TO_ADJACENT_FRIENDLY_FORCE_WITH_BOND_NO_NAME.value,
        DesignToken.THIS_FORMATION_DOES_NOT_CONTRIBUTE_INSTEAD.value,
    },
    "restriction": {DesignToken.CHOSEN_DIRECTION.value},
    "role": FORCE_ROLES,
    "scope": {DesignToken.THIS_FORMATION.value, DesignToken.THIS_FRONT.value},
    "secondary": {
        DesignToken.OPTIONAL_MOVE_ADJACENT_FRIENDLY_INTO_VACATED_POSITION.value,
        DesignToken.OPTIONAL_SIDEWAYS_REAR_MOVE.value,
        DesignToken.OPTIONAL_ZERO_COST_FRIENDLY_NAMED_MANEUVER.value,
        DesignToken.OPTIONAL_ZERO_COST_MANEUVER_THAT_FORMATION.value,
    },
    "stratagem": {
        DesignToken.ALL_RESERVES_FORWARD.value,
        DesignToken.BATTLE_TURNS_DIRECTION.value,
        DesignToken.COMBINE_TWO_ADJACENT_FRONTS.value,
        DesignToken.ENCIRCLEMENT.value,
        DesignToken.EVERY_BANNER_TURNED.value,
        DesignToken.FEIGNED_RETREAT.value,
        DesignToken.LINE_BEGUN_TO_MOVE.value,
        DesignToken.NO_RETREAT_FRONT.value,
        DesignToken.NO_ROAD_BACK.value,
        DesignToken.REFUSE_FLANK.value,
        DesignToken.WHEEL_LINE.value,
    },
    "target": {DesignToken.OPPOSING_FRONTLINE_FORCE_WITH_LOWER_PRINTED_STRENGTH.value},
    "timing": {
        DesignToken.AFTER_RETREAT.value,
        DesignToken.AFTER_RETREAT_RESOLVES.value,
        DesignToken.BATTLE_END_BEFORE_STRENGTH_COMPARISON.value,
    },
    "trigger": {
        DesignToken.ADJACENT_FRIENDLY_FORMATION_RETREATS.value,
        DesignToken.ADJACENT_FRIENDLY_NAMED_FORMATION_MANEUVERS_AWAY.value,
        DesignToken.BATTLE_END_PLAYER_WON_AT_LEAST_THREE_FRONTS.value,
        DesignToken.FIRST_FRIENDLY_MANEUVER_INTO_EMPTY_EACH_BATTLE.value,
        DesignToken.FORCE_MOVES_OR_MANEUVERS.value,
        DesignToken.FORMATION_DRIVEN_OFF.value,
        DesignToken.FRIENDLY_FORMATION_BECOMES_NAMED.value,
        DesignToken.FRIENDLY_NAMED_FORMATION_RETREATS.value,
        DesignToken.OPPONENT_EFFECT_WOULD_PREVENT_OTHER_FRIENDLY_FORMATION_CONTRIBUTION.value,
        DesignToken.OPPONENT_HAS_FORCE_IN_BOTH_RANKS_SAME_FRONT.value,
        DesignToken.OPPOSING_FORMATION_BECOMES_NAMED.value,
        DesignToken.OPPOSING_FORMATION_IN_SAME_FRONT_BECOMES_NAMED.value,
        DesignToken.OPPOSING_FORMATION_MANEUVERS_INTO_SAME_FRONT.value,
        DesignToken.OWN_FRONT_WINS_AND_OPPOSING_FRONTLINE_NAMED_RETREATS.value,
        DesignToken.REGAIN_COMMAND_FROM_NARRATIVE.value,
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
            or value == DesignToken.DISCARD_OWN_FORCE_AND_ALL_ATTACHED_CARDS
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

    if design.get("trigger") == DesignToken.OPPOSING_FORMATION_IN_SAME_FRONT_BECOMES_NAMED:
        capabilities.add("opposing_named_same_front_free_maneuver")
    if design.get("trigger") == DesignToken.ADJACENT_FRIENDLY_NAMED_FORMATION_MANEUVERS_AWAY:
        capabilities.add("follow_into_vacated_after_adjacent_maneuver")
    if design.get("trigger") == DesignToken.ADJACENT_FRIENDLY_FORMATION_RETREATS:
        capabilities.add("adjacent_retreat_free_maneuver")
    if (
        (design.get("after_maneuver") or {}).get("effect")
        == DesignToken.OPTIONAL_SWAP_TWO_ADJACENT_FRIENDLY_FORMATIONS_EXCLUDING_SELF
    ):
        capabilities.add("after_maneuver_swap_other_friendlies")
    if design.get("trigger") == DesignToken.OPPOSING_FORMATION_MANEUVERS_INTO_SAME_FRONT:
        capabilities.add("opposing_maneuver_same_front_free_maneuver")
    if (
        force_design.get("after_frontline_retreat")
        == DesignToken.OPTIONAL_SIDEWAYS_REAR_MOVE
    ):
        capabilities.add("after_frontline_retreat_sideways_force")
    if name_design.get("after_self_retreat") == DesignToken.OPTIONAL_SIDEWAYS_REAR_MOVE:
        capabilities.add("after_self_retreat_sideways_name")
    if (
        force_design.get("on_play")
        == DesignToken.OPTIONAL_TAKE_ADJACENT_PREPARED_BOND_OR_NAME
    ):
        capabilities.add("on_play_take_adjacent_prepared_component_force")
    if name_design.get("on_play") == DesignToken.OPTIONAL_TAKE_ADJACENT_OPEN_BOND:
        capabilities.add("on_play_take_adjacent_open_bond_name")
    if (
        force_design.get("effect")
        == DesignToken.OPTIONAL_DRIVE_OFF_SELF_PREVENT_FRONTLINE_NAMED_RETREAT
    ):
        capabilities.add("optional_self_drive_prevent_frontline_retreat_force")
    if design.get("build_around") == DesignToken.PREPARED_POSITION:
        capabilities.add("prepared_on_play_free_maneuver_force")
    if (
        design.get("after_self_maneuver")
        == DesignToken.OPTIONAL_ZERO_COST_OTHER_FRIENDLY_NAMED_MANEUVER
    ):
        capabilities.add("after_self_maneuver_free_other_named_if_wide_name")
    if design.get("trigger") == DesignToken.REGAIN_COMMAND_FROM_NARRATIVE:
        capabilities.add("narrative_command_gain_free_maneuver_force")
    if design.get("build_around") == DesignToken.OPEN_BOND_TRANSFER:
        capabilities.add("transfer_open_bond_after_move_bond")
    if design.get("build_around") == DesignToken.SUCCESSION:
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
                "design_rules",
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
            if card_type != CardType.FORCE:
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

        if card_type == CardType.FORCE:
            role = card.get("role")
            if role is not None and (
                not isinstance(role, str)
                or not role.strip()
                or role != role.strip()
            ):
                raise ValueError(
                    f"{card_id}: Force role must be a non-empty string when present"
                )

        if card_type == CardType.NARRATIVE:
            form = card.get("narrative_form")
            if not isinstance(form, str) or form not in NARRATIVE_FORMS:
                raise ValueError(
                    f"{card_id}: invalid Narrative form {form!r}"
                )
            if not isinstance(card.get("ongoing"), bool):
                raise ValueError(
                    f"{card_id}: Narrative ongoing must be boolean"
                )

        if card_type in {CardType.FORCE, CardType.NAME}:
            _validate_rule_value(
                card.get("strength"),
                _NONNEGATIVE,
                f"{card_id}.strength",
            )

        if card_type == CardType.NAME and card["unique"] is not True:
            raise ValueError(f"{card_id}: every Name must be Unique")

        if "rules" in card:
            raise ValueError(
                f"{card_id}: rules field is unsupported; use design_rules"
            )
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
