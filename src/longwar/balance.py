from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import product
from math import sqrt
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
    link_balance = link.get("balance", {})
    name_balance = name.get("balance", {})

    strength += int(link_balance.get("strength_bonus", 0))
    strength += int(link_balance.get("named_strength_bonus", 0))
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
