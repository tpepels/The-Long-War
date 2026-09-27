from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import product
from statistics import mean, pstdev
from typing import Any

from .cards import cards_by_type


@dataclass(frozen=True)
class FormationScore:
    force: str
    bond: str
    name: str
    static_strength: int
    has_dynamic_effects: bool


def score_static_formation(
    force: dict[str, Any],
    bond: dict[str, Any],
    name: dict[str, Any],
) -> FormationScore:
    """Score only unconditional printed Force/Bond/Name Strength."""
    strength = int(force["strength"])
    bond_rules = bond.get("rules", {})
    strength += int(bond_rules.get("strength_bonus", 0))
    strength += int(
        bond_rules.get(
            "named_additional_strength_bonus",
            bond_rules.get("named_strength_bonus", 0),
        )
    )
    strength += int(
        name["hero_name_strength"]
        if name.get("hero")
        else name["strength"]
    )

    dynamic = any(
        bool(card.get("balance", {}).get("dynamic"))
        for card in (force, bond, name)
    )

    return FormationScore(
        force=force["id"],
        bond=bond["id"],
        name=name["id"],
        static_strength=strength,
        has_dynamic_effects=dynamic,
    )


def build_report(data: dict[str, Any]) -> dict[str, Any]:
    forces = cards_by_type(data, "force")
    bonds = cards_by_type(data, "bond")
    heroes = [card for card in forces if card.get("hero")]
    names = [*cards_by_type(data, "name"), *heroes]

    formations = [
        score_static_formation(force, bond, name)
        for force, bond, name in product(forces, bonds, names)
        if force["id"] != name["id"]
    ]

    values = [formation.static_strength for formation in formations]
    avg = mean(values)
    sd = pstdev(values) if len(values) > 1 else 0.0

    def z(value: float) -> float:
        return 0.0 if sd == 0 else (value - avg) / sd

    ranked = sorted(
        formations,
        key=lambda item: item.static_strength,
        reverse=True,
    )

    per_card: dict[str, list[int]] = {}
    per_card_mode: dict[str, dict[str, list[int]]] = {}
    for formation in formations:
        for mode, card_id in (
            ("force", formation.force),
            ("bond", formation.bond),
            ("name", formation.name),
        ):
            per_card.setdefault(card_id, []).append(formation.static_strength)
            per_card_mode.setdefault(card_id, {}).setdefault(mode, []).append(
                formation.static_strength
            )

    marginal = [
        {
            "card": card_id,
            "mean_static_formation_strength": mean(card_values),
            "delta_from_global_mean": mean(card_values) - avg,
            "modes": {
                mode: {
                    "mean_static_formation_strength": mean(mode_values),
                    "delta_from_global_mean": mean(mode_values) - avg,
                }
                for mode, mode_values in sorted(per_card_mode[card_id].items())
            },
        }
        for card_id, card_values in per_card.items()
    ]
    marginal.sort(
        key=lambda item: item["delta_from_global_mean"],
        reverse=True,
    )

    return {
        "schema_version": data["schema_version"],
        "formation_count": len(formations),
        "static_strength": {
            "mean": avg,
            "population_sd": sd,
            "min": min(values),
            "max": max(values),
        },
        "all_static_formations": [
            {**asdict(item), "z_score": z(item.static_strength)}
            for item in ranked
        ],
        "highest_static_formations": [
            {**asdict(item), "z_score": z(item.static_strength)}
            for item in ranked[:10]
        ],
        "lowest_static_formations": [
            {**asdict(item), "z_score": z(item.static_strength)}
            for item in ranked[-10:]
        ],
        "card_static_marginals": marginal,
        "limitations": [
            "This report scores only unconditional printed Strength.",
            "Position, timing, hand economy, movement, persistence, Narratives, Stratagems, and dynamic effects require game simulation.",
            "Static outliers are diagnostics, not automatic balance failures.",
        ],
    }


def validate_command_costs(card_data: dict[str, Any]) -> None:
    """Validate printed Command costs without rebalancing canonical card data."""
    invalid = []
    for card in card_data["cards"]:
        cost = card.get("command_cost")
        if isinstance(cost, bool) or not isinstance(cost, int) or cost < 1:
            invalid.append(f"{card['id']}: invalid command_cost={cost!r}")
    if invalid:
        raise ValueError("Invalid Command cost: " + ", ".join(invalid))
