"""Report executable-engine differences from the currently printed paper cards.

Read-only: this tool neither rewrites authored cards nor guesses executable
semantics from natural-language print text. Use `--strict` as a parity gate
when converting the paper effects to native operations.
"""
from __future__ import annotations

import argparse
import json

from print_cards import CANONICAL, load_print_cards


def _effects(card: dict) -> list[dict]:
    if card["type"] == "hero":
        return [
            {"mode": mode, **effect}
            for mode in ("force", "name")
            for effect in card["modes"][mode]["effects"]
        ]
    return card.get("effects", [])


def audit() -> dict:
    source = json.loads(CANONICAL.read_text(encoding="utf-8"))
    printed = load_print_cards(base=source)
    originals = {card["id"]: card for card in source["cards"]}
    changes: list[dict] = []

    if {c["id"] for c in printed["cards"]} != set(originals):
        raise ValueError("Paper and executable card identities do not agree")

    for card in printed["cards"]:
        baseline = originals[card["id"]]
        fields: dict = {}
        for key in (
            "command_cost",
            "strength",
            "strength_modifier",
            "force_strength",
            "name_strength_modifier",
            "allowed_rows",
        ):
            if card.get(key) != baseline.get(key):
                fields[key] = {
                    "executable": baseline.get(key),
                    "paper": card.get(key),
                }

        if card["type"] == "hero":
            printed_prices = {
                "force": card.get("hero_force_command_cost", card["command_cost"]),
                "name": card.get("hero_name_command_cost", card["command_cost"]),
            }
            baseline_prices = {
                "force": baseline["command_cost"],
                "name": baseline["command_cost"],
            }
            if printed_prices != baseline_prices:
                fields["hero_mode_command_costs"] = {
                    "executable": baseline_prices,
                    "paper": printed_prices,
                }

        old = _effects(baseline)
        new = _effects(card)
        old_rules = [
            (entry.get("mode"), entry.get("timing"), entry.get("limit"), entry.get("text"))
            for entry in old
        ]
        new_rules = [
            (entry.get("mode"), entry.get("timing"), entry.get("limit"), entry.get("text"))
            for entry in new
        ]
        if old_rules != new_rules:
            fields["printed_effects"] = {
                "executable_count": len(old),
                "paper_count": len(new),
                "executable": [
                    {"mode": e.get("mode"), "timing": e.get("timing"), "limit": e.get("limit"), "text": e.get("text")}
                    for e in old
                ],
                "paper": [
                    {"mode": e.get("mode"), "timing": e.get("timing"), "limit": e.get("limit"), "text": e.get("text")}
                    for e in new
                ],
            }

        if fields:
            changes.append({
                "id": card["id"], "title": card["title"],
                "differences": fields,
            })

    counts: dict[str, int] = {}
    for item in changes:
        for field in item["differences"]:
            counts[field] = counts.get(field, 0) + 1

    return {
        "source": str(CANONICAL.relative_to(CANONICAL.parents[1])),
        "paper_source": "cards/print-overrides.json via tools/print_cards.py",
        "card_count": len(source["cards"]),
        "different_cards": len(changes),
        "difference_counts": counts,
        "cards": changes,
        "core_rule_gaps": [
            "Voluntary Pass must happen before drawing, but the native engine draws automatically at turn start",
            "The current native action set has no basic Attack action",
            "Shaken, Depleted, Guarded, Inspired, Empowered and used-Attack require authoritative engine state",
            "Flanking currently creates Exhaustion after an Action rather than a positional -1 Strength condition",
            "Battle-end lost-Front Exhaustion must offer a single selected Force per lost Front",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Include all per-card differences")
    parser.add_argument("--strict", action="store_true", help="Exit nonzero while parity work remains")
    args = parser.parse_args()
    result = audit()
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Paper catalogue: {result['card_count']} cards")
        print(f"Different from executable input: {result['different_cards']} cards")
        for key, count in sorted(result["difference_counts"].items()):
            print(f"  {key}: {count}")
        print("Core engine gaps:")
        for gap in result["core_rule_gaps"]:
            print(f"  - {gap}")
        print("Use --json for per-card details.")
    return 1 if args.strict and (result["different_cards"] or result["core_rule_gaps"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
