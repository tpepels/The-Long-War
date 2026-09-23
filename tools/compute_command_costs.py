from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def card_value(card: dict[str, Any]) -> float:
    rules = card.get("rules", {})
    card_type = card["type"]

    if card_type == "subject":
        value = float(card.get("strength", 0))
        value += float(rules.get("adjacent_strength_aura", 0)) * 1.2
        value += sum(
            max(0.0, float(modifier.get("amount", 0))) * 0.45
            for modifier in rules.get("strength_modifiers", [])
        )
        value += float(
            rules.get("on_link_attached", {}).get("temporary_strength", 0)
        ) * 0.45
        if rules.get("placement", {}).get("rank"):
            value -= 0.35
        if card.get("hero", False):
            value += 0.6
        return max(0.0, value)

    if card_type == "name":
        value = float(card.get("strength", 0))
        if rules.get("on_name_attached") == "move_adjacent_optional":
            value += 1.2
        completion = rules.get("on_completion", {})
        effect = completion.get("effect")
        if effect == "gain_command":
            value += 0.6 * float(completion.get("amount", 1))
        elif effect == "grant_free_cycle":
            value += 0.9
        elif effect == "reveal_enemy_scheme":
            value += 0.45
        elif effect == "recover_recent_link":
            value += 1.2
        if rules.get("complete_protection_from_opponent_plot"):
            value += 1.4
        value += 1.8 * float(rules.get("adjacent_command_discount", 0))
        return value

    if card_type == "link":
        value = float(rules.get("strength_bonus", 0))
        value += float(rules.get("named_strength_bonus", 0)) * 0.6
        value += abs(float(rules.get("opposing_front_modifier", 0))) * 0.8
        if rules.get("protect_subject_from_opponent_plot"):
            value += 1.4
        discard_bonus = rules.get("discard_strength_bonus")
        if discard_bonus:
            value += float(discard_bonus.get("maximum", 0)) * 0.35
        return value

    if card_type == "plot":
        if card.get("veiled", False):
            scheme = rules.get("scheme", {})
            value = float(scheme.get("face_down_front_bonus", 0))
            effect = scheme.get("effect")
            if effect == "discard_played_link":
                value += 2.0
            elif effect in {"penalize_played_subject", "reinforce_front"}:
                value += float(scheme.get("amount", 0)) * 0.65
            else:
                value += 1.0
            return value
        return {
            "discredit_subject": 3.0,
            "return_name_or_weaken": 2.6,
            "move_subject": 2.4,
        }.get(rules.get("effect"), 2.2)

    if card_type == "stratagem":
        stratagem = rules.get("stratagem", {})
        continuous = stratagem.get("continuous", {})
        reveal = stratagem.get("reveal_effect", {})
        value = 2.8
        for group in (
            "role_strength_modifiers",
            "rank_strength_modifiers",
            "controller_rank_strength_modifiers",
        ):
            value += sum(
                abs(float(amount)) * 0.25
                for amount in continuous.get(group, {}).values()
            )
        value += abs(float(continuous.get("named_subject_modifier", 0))) * 0.3
        value += abs(float(continuous.get("unnamed_subject_modifier", 0))) * 0.3
        if continuous.get("disable_line_defense"):
            value += 0.6
        if reveal.get("cancel_story"):
            value += 1.0
        if reveal.get("effect") == "penalize_trigger_subject":
            value += float(reveal.get("amount", 0)) * 0.4
        if continuous.get("controller_immediate_story_lock"):
            value -= 0.4
        return max(0.0, value)

    return 2.5


def command_cost(value: float) -> int:
    if value < 2.5:
        return 1
    if value < 5.5:
        return 2
    return 3


def computed_cost(card: dict[str, Any]) -> int:
    return command_cost(card_value(card))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cards", type=Path, nargs="?", default=Path("cards/cards.json"))
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    data = json.loads(args.cards.read_text(encoding="utf-8"))
    mismatches = []
    for card in data["cards"]:
        expected = computed_cost(card)
        if card.get("command_cost") != expected:
            mismatches.append((card["id"], card.get("command_cost"), expected))
            if args.write:
                card["command_cost"] = expected

    if args.write:
        args.cards.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return

    if mismatches:
        details = ", ".join(
            f"{card_id}: stored={stored} computed={expected}"
            for card_id, stored, expected in mismatches
        )
        raise SystemExit(f"Command cost drift: {details}")

    counts = {}
    for card in data["cards"]:
        counts[card["command_cost"]] = counts.get(card["command_cost"], 0) + 1
    print("Command costs match model:", counts)


if __name__ == "__main__":
    main()
