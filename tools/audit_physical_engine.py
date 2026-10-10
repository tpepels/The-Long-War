"""Report physical-print versus current executable catalogue discrepancies.

This is advisory while cards change rapidly. The audited conditions are
separate from balance/power-level concerns: they measure whether clicking a
card in the game executes the same rules as printed on the physical card.

Usage:
  python tools/audit_physical_engine.py
  python tools/audit_physical_engine.py --json
  python tools/audit_physical_engine.py --strict  # explicit release gate
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path

from print_cards import load_print_cards
from longwar.physical_values import apply_printed_numeric_values
from longwar.physical_effects import apply_reviewed_physical_effects

ROOT = Path(__file__).resolve().parents[1]
STAT_FIELDS = (
    "command_cost", "strength", "strength_modifier", "allowed_rows",
    "hero_force_command_cost", "hero_name_command_cost",
)


def inspect() -> dict:
    source = json.loads((ROOT / "cards" / "cards.json").read_text())
    printed = load_print_cards(base=source)
    runtime = apply_reviewed_physical_effects(
        apply_printed_numeric_values(source)
    )
    expected = {card["id"]: card for card in printed["cards"]}
    actual = {card["id"]: card for card in runtime["cards"]}
    defects: dict[str, list[str]] = defaultdict(list)
    if expected.keys() != actual.keys():
        raise ValueError("Printed/runtime card identities disagree")
    for cid, card in expected.items():
        compiled = actual[cid]
        for field in STAT_FIELDS:
            if card.get(field) != compiled.get(field):
                defects[cid].append(f"printed {field} mismatch")
        if card.get("effects", []) != compiled.get("effects", []):
            defects[cid].append("printed effect is not compiled")
        if card["type"] == "hero":
            for mode in ("force", "name"):
                printed_mode = card["modes"][mode]
                actual_mode = compiled["modes"][mode]
                if printed_mode.get("effects", []) != actual_mode.get("effects", []):
                    defects[cid].append(f"{mode} Hero effect wording diverges")
                if printed_mode.get("command_cost") != actual_mode.get("command_cost"):
                    defects[cid].append(f"{mode} Hero Command cost differs")
    by_reason = defaultdict(list)
    for cid, reasons in sorted(defects.items()):
        for reason in reasons:
            by_reason[reason].append(cid)
    return {
        "total_cards": len(expected),
        "exact_printed_value_and_text_cards": len(expected) - len(defects),
        "cards_with_parity_gaps": len(defects),
        "ready_for_physical_rules": not defects,
        "gaps_by_reason": dict(by_reason),
        "gaps_by_card": dict(sorted(defects.items())),
        "limitations": (
            "Matching printed words is necessary but not sufficient: every "
            "compiled effect must also be tested in gameplay, including "
            "Stratagem simultaneous reveal and reactions."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    report = inspect()
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(
            f"Physical card parity: {report['exact_printed_value_and_text_cards']}/"
            f"{report['total_cards']} match printed values and effect words; "
            f"{report['cards_with_parity_gaps']} card identities still differ."
        )
        for reason, ids in report["gaps_by_reason"].items():
            print(f" - {reason}: {len(ids)}")
            for cid in ids:
                print(f"   {cid}")
        print(report["limitations"])
    return 1 if args.strict and not report["ready_for_physical_rules"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
