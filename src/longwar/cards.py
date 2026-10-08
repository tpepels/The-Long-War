from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from .protocol import (
    CARD_TYPES,
    NARRATIVE_FORMS,
    RULE_BLOCK_KINDS,
    CardField,
    CardType,
    RuleBlockField,
)

RANKS = frozenset({"front", "middle", "rear"})

# Stable native classification bits. These are game semantics: class-dependent
# card text must use these bits instead of string comparisons in search code.
CARD_CLASS_BITS = {
    "archer": 1 << 0,
    "builder": 1 << 1,
    "captain": 1 << 2,
    "guard": 1 << 3,
    "healer": 1 << 4,
    "heir": 1 << 5,
    "human": 1 << 6,
    "king": 1 << 7,
    "raider": 1 << 8,
    "rider": 1 << 9,
    "scout": 1 << 10,
    "seer": 1 << 11,
    "ship": 1 << 12,
    "skirmisher": 1 << 13,
    "spearman": 1 << 14,
    "steward": 1 << 15,
    "stronghold": 1 << 16,
    "veteran": 1 << 17,
}

# Kept as a public compatibility symbol while the old capability-bit compiler
# is removed. V2 mechanics compile through explicit effect specs instead.
CARD_CAPABILITY_BITS: dict[str, int] = {}

V2_EFFECT_OPS = frozenset({
    "action_tax",
    "add_class",
    "add_strength_marker",
    "attach_prepared",
    "choose_class_strength",
    "choose_strength_targets",
    "class_play_discount",
    "class_strength_aura",
    "class_strength_markers",
    "component_strength",
    "discard_draw",
    "disrupt_stratagem",
    "draw",
    "draw_discard",
    "draw_put_top",
    "front_card_tax",
    "front_presence_discount",
    "front_tactic_discount",
    "gain_command",
    "global_discount",
    "global_discount_split",
    "grant_name_suppression_immunity",
    "hidden_buff_after_marker",
    "hidden_buff_all",
    "hidden_buff_moved_source",
    "hidden_buff_on_tactic",
    "hidden_buff_targets",
    "hidden_cancel_tactic",
    "hidden_draw_discard",
    "hidden_protect_lost_fronts",
    "hidden_spy_on_stratagem",
    "hidden_tie_named_wins",
    "local_class_aura",
    "look_hand",
    "look_stratagem",
    "maneuver_cost_class",
    "maneuver_unnamed",
    "move",
    "move_then_front_bonus",
    "name_suppression_immunity",
    "next_slot_discount",
    "optional_extra_payment_draw",
    "pick_top_to_hand_bottom_rest",
    "play_bond_from_hand",
    "prepared_attach_tax",
    "prepared_pay_or_return",
    "prevent_negative_marker",
    "prevent_tactic_strength_reduction",
    "recover",
    "redirect_tactic",
    "remove_exhaustion",
    "remove_negative_marker",
    "remove_strength_marker",
    "reorder_top",
    "reserve",
    "return_prepared",
    "self_strength",
    "set_stratagem_from_hand",
    "slot_discount",
    "stratagem_visibility",
    "status_strength_aura",
    "steal_command",
    "exhaust",
    "flank_guard",
    "return_component",
    "swap_fronts",
    "swap_bonds",
    "supply",
    "support",
    "suppress_action",
    "suppress_bond",
    "suppress_bond_strength",
    "suppress_component",
    "suppress_limited",
    "suppress_name",
    "swap",
    "tactic_front_presence_discount",
    "tactic_tax",
    "tax",
    "tireless",
    "trigger_draw",
    "trigger_draw_discard",
    "trigger_gain_command",
    "trigger_look_stratagem",
})

V2_TIMINGS = frozenset({
    "play",
    "action",
    "becomes_named",
    "bonded",
    "continuous",
    "hidden",
    "trigger",
    "reaction",
    "while_named",
    "front",
    "middle",
    "rear",
    "exhausted",
    "tireless",
    "mobile",
})

V2_EFFECT_LIMITS = frozenset({None, "once_per_battle"})

V2_TARGETS = frozenset({
    "self",
    "directly_ahead",
    "directly_behind",
    "friendly_any_class",
    "friendly_same_front",
    "opponent_all",
    "opponent_random",
    "opposing_any",
    "opposing_any_class",
    "opposing_bonded_any",
    "opposing_bonded_same_front",
    "opposing_class_front_with_friendly_class",
    "opposing_component_same_front",
    "opposing_front_with_friendly_class",
    "opposing_named_any",
    "opposing_prepared_any",
    "opposing_prepared_front_with_friendly_class",
    "opposing_prepared_same_front",
    "opposing_rear",
    "opposing_same_front",
    "opposing_same_front_without_negative_strength",
    "opposite",
    "other_friendly_human_same_front",
    "other_friendly_same_front",
    "prepared_component_same_front",
    "prepared_name_same_front",
    "same_front",
    "self_or_directly_ahead",
    "self_or_directly_behind",
    "self_vertical_friend",
    "unbonded_friendly_same_front",
    "friendly_exhausted_front_with_friendly_class",
    "friendly_pair_same_front_with_class",
    "friendly_front_of_source_class",
    "opposing_exhausted_same_front",
    "opposing_support_open_front",
    "friendly_any",
})



def class_mask(values: list[str] | tuple[str, ...]) -> int:
    mask = 0
    for value in values:
        try:
            mask |= CARD_CLASS_BITS[value]
        except KeyError as exc:
            raise ValueError(f"Unknown V2 classification: {value!r}") from exc
    return mask


def _require_fields(value: dict[str, Any], fields: tuple[str, ...], path: str) -> None:
    missing = set(fields) - value.keys()
    if missing:
        raise ValueError(
            f"{path}: missing required fields: {', '.join(sorted(missing))}"
        )


def _validate_effect_spec(
    effect: dict[str, Any],
    *,
    card_id: str,
    path: str,
) -> None:
    if not isinstance(effect, dict):
        raise ValueError(f"{card_id}.{path}: effect must be an object")
    timing = effect.get("timing")
    if timing not in V2_TIMINGS:
        raise ValueError(f"{card_id}.{path}: unsupported timing {timing!r}")
    if effect.get("limit") not in V2_EFFECT_LIMITS:
        raise ValueError(
            f"{card_id}.{path}: unsupported limit {effect.get('limit')!r}"
        )
    op = effect.get("op")
    if op == "unimplemented":
        raise ValueError(f"{card_id}.{path}: effect is not executable")
    if op not in V2_EFFECT_OPS:
        raise ValueError(f"{card_id}.{path}: unsupported operation {op!r}")

    for selector_key in ("target", "destination", "requires_friendly"):
        selector = effect.get(selector_key)
        if selector is not None and selector not in V2_TARGETS:
            raise ValueError(
                f"{card_id}.{path}: unsupported {selector_key} {selector!r}"
            )

    for key in (
        "classes",
        "requires_any_class",
        "required_any_class",
        "source_classes",
        "target_classes",
    ):
        values = effect.get(key)
        if values is not None:
            if not isinstance(values, list):
                raise ValueError(f"{card_id}.{path}.{key}: must be a list")
            class_mask(values)
    for key in ("required_friendly_class", "requires_other_friendly_class", "class"):
        value = effect.get(key)
        if value is not None:
            class_mask([value])


def _validate_design_rules(card: dict[str, Any]) -> None:
    card_id = card["id"]
    design = card.get(CardField.DESIGN_RULES)
    if not isinstance(design, dict):
        raise ValueError(f"{card_id}.design_rules: must be an object")

    effects = design.get("effects")
    modes = design.get("modes")
    if not isinstance(effects, list) or not isinstance(modes, dict):
        raise ValueError(
            f"{card_id}.design_rules: requires effects list and modes object"
        )

    printed = card.get(CardField.EFFECTS, [])
    if len(effects) != len(printed):
        raise ValueError(
            f"{card_id}: every printed effect requires one executable effect"
        )
    for index, effect in enumerate(effects):
        _validate_effect_spec(effect, card_id=card_id, path=f"design_rules.effects[{index}]")
        if effect["timing"] != printed[index].get("timing"):
            raise ValueError(f"{card_id}: executable/printed effect timing mismatch")

    printed_modes = card.get(CardField.MODES, {})
    if set(modes) != set(printed_modes):
        raise ValueError(f"{card_id}: executable/printed hero modes differ")
    for mode, compiled in modes.items():
        if mode not in {"force", "name"}:
            raise ValueError(f"{card_id}: unsupported card mode {mode!r}")
        printed_effects = printed_modes[mode].get("effects", [])
        if len(compiled) != len(printed_effects):
            raise ValueError(
                f"{card_id}.{mode}: every printed effect requires one executable effect"
            )
        for index, effect in enumerate(compiled):
            _validate_effect_spec(
                effect,
                card_id=card_id,
                path=f"design_rules.modes.{mode}[{index}]",
            )
            if effect["timing"] != printed_effects[index].get("timing"):
                raise ValueError(
                    f"{card_id}.{mode}: executable/printed effect timing mismatch"
                )


def normalize_card_data(data: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(data)


def compile_card_mechanics(card: dict[str, Any]) -> dict[str, Any]:
    """Return validated V2 executable mechanics plus native-ready class masks."""
    _validate_design_rules(card)
    design = copy.deepcopy(card[CardField.DESIGN_RULES])
    design["_class_mask"] = class_mask(card.get(CardField.CLASSES, []))
    design["_capabilities"] = ()
    design["_capability_bits"] = 0
    return design


def load_card_file(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    validate_card_data(data)
    return normalize_card_data(data)


def _validate_effect_presentation(card: dict[str, Any]) -> None:
    card_id = card["id"]
    effects = card.get(CardField.EFFECTS, [])
    if not isinstance(effects, list):
        raise ValueError(f"{card_id}.effects must be a list")
    for index, effect in enumerate(effects):
        if not isinstance(effect, dict):
            raise ValueError(f"{card_id}.effects[{index}] must be an object")
        if effect.get("timing") not in V2_TIMINGS:
            raise ValueError(
                f"{card_id}.effects[{index}]: invalid timing {effect.get('timing')!r}"
            )
        if not isinstance(effect.get("text"), str) or not effect["text"].strip():
            raise ValueError(f"{card_id}.effects[{index}]: text must be non-empty")

    modes = card.get(CardField.MODES, {})
    if not isinstance(modes, dict):
        raise ValueError(f"{card_id}.modes must be an object")
    for mode, payload in modes.items():
        if mode not in {"force", "name"} or not isinstance(payload, dict):
            raise ValueError(f"{card_id}: invalid mode {mode!r}")
        mode_effects = payload.get("effects", [])
        if not isinstance(mode_effects, list):
            raise ValueError(f"{card_id}.{mode}.effects must be a list")
        for index, effect in enumerate(mode_effects):
            if effect.get("timing") not in V2_TIMINGS:
                raise ValueError(
                    f"{card_id}.{mode}.effects[{index}]: invalid timing"
                )


def validate_card_data(data: dict[str, Any]) -> None:
    if not isinstance(data, dict):
        raise ValueError("Card data must be an object")
    if data.get("schema_version") != 4:
        raise ValueError("Unsupported card schema_version")
    if data.get("status") != "canonical":
        raise ValueError("Canonical card data must have status='canonical'")

    cards = data.get("cards")
    if not isinstance(cards, list) or not cards:
        raise ValueError("cards must be a non-empty list")

    seen_ids: set[str] = set()
    for card in cards:
        if not isinstance(card, dict):
            raise ValueError("Every card must be an object")
        _require_fields(
            card,
            ("id", "title", "type", "unique", "classes", "text", "design_rules", "rule_blocks"),
            "card",
        )
        card_id = card["id"]
        if not isinstance(card_id, str) or not card_id.strip() or card_id != card_id.strip():
            raise ValueError("Every card requires a non-empty id")
        if card_id in seen_ids:
            raise ValueError(f"Duplicate card id: {card_id}")
        seen_ids.add(card_id)

        card_type = card["type"]
        if card_type not in CARD_TYPES:
            raise ValueError(f"{card_id}: invalid card type {card_type!r}")
        if not isinstance(card["title"], str) or not card["title"].strip():
            raise ValueError(f"{card_id}: missing title")
        if type(card["unique"]) is not bool:
            raise ValueError(f"{card_id}: unique must be boolean")
        if not isinstance(card["classes"], list):
            raise ValueError(f"{card_id}: classes must be a list")
        if len(card["classes"]) != len(set(card["classes"])):
            raise ValueError(f"{card_id}: duplicate classes")
        class_mask(card["classes"])
        # A former non-executable "references" list duplicated effect classes
        # and went stale when cards were rewritten. Conditions now belong only
        # in design_rules; printed labels come from the effect text.
        if "references" in card:
            raise ValueError(
                f"{card_id}: obsolete references metadata; "
                "write class conditions in design_rules"
            )

        if not isinstance(card["text"], str):
            raise ValueError(f"{card_id}: text must be a string")
        cost = card.get(CardField.COMMAND_COST)
        if type(cost) is not int or not 0 <= cost <= 127:
            raise ValueError(f"{card_id}: command_cost must be 0..127")

        rows = card.get(CardField.ALLOWED_ROWS)
        if rows is not None:
            if (
                not isinstance(rows, list)
                or not rows
                or set(rows) - RANKS
                or len(rows) != len(set(rows))
            ):
                raise ValueError(f"{card_id}: invalid allowed_rows")

        if card_type == CardType.FORCE:
            strength = card.get(CardField.STRENGTH)
            if type(strength) is not int or not 0 <= strength <= 127:
                raise ValueError(
                    f"{card_id}: Force strength must be an integer in 0..127"
                )
        elif card_type in {CardType.BOND, CardType.NAME}:
            strength = card.get(CardField.STRENGTH_MODIFIER)
            if type(strength) is not int or not -128 <= strength <= 127:
                raise ValueError(
                    f"{card_id}: {card_type} strength_modifier must fit signed int8"
                )
            if card_type == CardType.NAME and not card["unique"]:
                raise ValueError(f"{card_id}: every Name must be Unique")
        elif card_type == CardType.HERO:
            if not card["unique"]:
                raise ValueError(f"{card_id}: every Hero must be Unique")
            force_strength = card.get(CardField.FORCE_STRENGTH)
            name_strength = card.get(CardField.NAME_STRENGTH_MODIFIER)
            if type(force_strength) is not int or not 0 <= force_strength <= 127:
                raise ValueError(
                    f"{card_id}: Hero force_strength must be an integer in 0..127"
                )
            if type(name_strength) is not int or not -128 <= name_strength <= 127:
                raise ValueError(
                    f"{card_id}: Hero name_strength_modifier must fit signed int8"
                )
            if set(card.get(CardField.MODES, {})) != {"force", "name"}:
                raise ValueError(f"{card_id}: Hero requires force and name modes")

        _validate_effect_presentation(card)
        _validate_design_rules(card)

        blocks = card["rule_blocks"]
        if not isinstance(blocks, list):
            raise ValueError(f"{card_id}: rule_blocks must be a list")
        for block in blocks:
            if not isinstance(block, dict):
                raise ValueError(f"{card_id}: rule block must be an object")
            if block.get(RuleBlockField.KIND) not in RULE_BLOCK_KINDS:
                raise ValueError(f"{card_id}: invalid rule block kind")
            if not isinstance(block.get(RuleBlockField.TEXT), str):
                raise ValueError(f"{card_id}: invalid rule block text")


def cards_by_type(data: dict[str, Any], card_type: str) -> list[dict[str, Any]]:
    if card_type not in CARD_TYPES:
        raise ValueError(f"Unknown card type: {card_type}")
    return [card for card in data["cards"] if card["type"] == card_type]


def card_index(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {card["id"]: card for card in data["cards"]}
