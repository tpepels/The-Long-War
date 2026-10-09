"""Audit printed Force costs against the explicit strength and ability tariff.

This is a deterministic price consistency report, *not* a physical combat or
balance simulation. Abilities and attack/position rules are not rewritten.
"""
from __future__ import annotations

import json
from collections import Counter

from print_cards import ROOT, load_print_cards

LEDGER = ROOT / "cards" / "force-pricing.json"


def main() -> None:
    catalogue = load_print_cards()["cards"]
    cards = {c["id"]: c for c in catalogue}
    forces = {c["id"]: c for c in catalogue if c["type"] == "force"}
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    assert ledger["scope"] == "physical-print-forces-only"
    rows = ledger["forces"]
    assert len(rows) == len(forces) == 33
    assert len({row["id"] for row in rows}) == len(rows)
    assert {row["id"] for row in rows} == set(forces)

    previous = current = 0
    changed = 0
    costs = Counter()
    for row in rows:
        card = forces[row["id"]]
        strength = card["strength"]
        assert type(strength) is int and 1 <= strength <= 9, row
        base = 1 + (strength + 1) // 2
        premium = row["premium"]
        assert type(premium) is int and premium in (0, 1), row
        assert len(row["rationale"]) >= 25, row
        assert type(row["previous_printed_command"]) is int, row
        expected = base + premium
        assert card["command_cost"] == expected, (
            card["id"], card["command_cost"], base, premium
        )
        # Even Strength has no unused half-point, so its real printed
        # or class-native special advantage has an explicit premium.
        if strength % 2 == 0 and (card.get("effects") or "guard" in card.get("classes", [])):
            assert premium == 1, card["id"] + ": missing even-Strength special premium"
        if not card.get("effects") and "guard" not in card.get("classes", []):
            assert premium == 0, card["id"] + ": plain body unexpectedly surcharged"
        previous += row["previous_printed_command"]
        current += expected
        changed += (row["previous_printed_command"] != expected)
        costs[expected] += 1

    assert previous == 70 and current == 117 and changed == 33
    assert all(c["command_cost"] >= 3 for c in forces.values())
    assert all(c["command_cost"] <= 5 for c in forces.values())
    assert len(cards) == 131
    print(f"PASS: {len(forces)} Forces priced at 1 + ceil(STR / 2) + premium (0 or 1)")
    print(f"  Print costs: {dict(sorted(costs.items()))}")
    print(f"  Total per-single-copy Force costs: {previous} -> {current} "
          f"(+{current-previous} Command over all distinct identities)")
    print("  Remaining 98 physical identities retain their existing card-specific pricing")
    print("  NOT a win-rate, game duration, late-war Command or card-combo simulation")


if __name__ == "__main__":
    main()
