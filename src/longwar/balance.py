from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import product
from statistics import mean, pstdev
from typing import Any

from .cards import cards_by_type


@dataclass(frozen=True)
class LegendScore:
    subject: str
    link: str
    name: str
    static_strength: int
    has_dynamic_effects: bool


def score_static_legend(
    subject: dict[str, Any],
    link: dict[str, Any],
    name: dict[str, Any],
) -> LegendScore:
    strength = int(subject["strength"])
    link_rules = link.get("rules", {})

    strength += int(link_rules.get("strength_bonus", 0))
    strength += int(link_rules.get("named_strength_bonus", 0))
    strength += int(name["strength"])

    dynamic = any(
        bool(card.get("balance", {}).get("dynamic"))
        for card in (subject, link, name)
    )

    return LegendScore(
        subject=subject["id"],
        link=link["id"],
        name=name["id"],
        static_strength=strength,
        has_dynamic_effects=dynamic,
    )


def build_report(data: dict[str, Any]) -> dict[str, Any]:
    subjects = cards_by_type(data, "subject")
    links = cards_by_type(data, "link")
    names = cards_by_type(data, "name")

    legends = [
        score_static_legend(subject, link, name)
        for subject, link, name in product(subjects, links, names)
    ]

    values = [legend.static_strength for legend in legends]
    avg = mean(values)
    sd = pstdev(values) if len(values) > 1 else 0.0

    def z(value: float) -> float:
        return 0.0 if sd == 0 else (value - avg) / sd

    ranked = sorted(legends, key=lambda item: item.static_strength, reverse=True)

    per_card: dict[str, list[int]] = {}
    for legend in legends:
        for card_id in (legend.subject, legend.link, legend.name):
            per_card.setdefault(card_id, []).append(legend.static_strength)

    marginal = [
        {
            "card": card_id,
            "mean_static_legend_strength": mean(card_values),
            "delta_from_global_mean": mean(card_values) - avg,
        }
        for card_id, card_values in per_card.items()
    ]
    marginal.sort(key=lambda item: item["delta_from_global_mean"], reverse=True)

    return {
        "schema_version": data["schema_version"],
        "legend_count": len(legends),
        "static_strength": {
            "mean": avg,
            "population_sd": sd,
            "min": min(values),
            "max": max(values),
        },
        "all_static_legends": [
            {**asdict(item), "z_score": z(item.static_strength)}
            for item in ranked
        ],
        "highest_static_legends": [
            {**asdict(item), "z_score": z(item.static_strength)}
            for item in ranked[:10]
        ],
        "lowest_static_legends": [
            {**asdict(item), "z_score": z(item.static_strength)}
            for item in ranked[-10:]
        ],
        "card_static_marginals": marginal,
        "limitations": [
            "This report scores only explicit static Strength.",
            "Position, timing, hand economy, disruption, passing, Veiled Stories, Stratagems, and dynamic effects require game simulation.",
            "Static outliers are diagnostics, not automatic balance failures.",
        ],
    }


# The canonical playtest cost calibration is a static diagnostic, not engine
# legality. Experiment fixtures can use a different calibration explicitly.
def _command_card_value(card: dict[str, Any]) -> float:
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
        elif effect == "draw_card":
            value += float(completion.get("amount", 1))
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


def _command_cost_band(value: float) -> int:
    if value < 2.5:
        return 1
    if value < 5.5:
        return 2
    return 3


def estimated_command_cost(card: dict[str, Any]) -> int:
    return _command_cost_band(_command_card_value(card))



def validate_command_costs(card_data: dict[str, Any]) -> None:
    """Reject drift from the canonical 1/2/3 Command cost calibration."""
    mismatches = []
    for card in card_data["cards"]:
        expected = estimated_command_cost(card)
        if card.get("command_cost") != expected:
            mismatches.append(f"{card['id']}: stored={card.get('command_cost')} expected={expected}")
    if mismatches:
        raise ValueError("Command cost drift: " + ", ".join(mismatches))
