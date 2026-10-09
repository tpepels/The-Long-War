"""Static consistency audit for the eleven physical Hero mode prices.

Hero Force mode uses the Force tariff; Hero Name mode is benchmarked
against ordinary printed Names. This does not measure combat balance.
"""
from __future__ import annotations

import json

from print_cards import OVERRIDES, load_print_cards


def main() -> None:
    printed = load_print_cards()["cards"]
    data = {c["id"]: c for c in printed}
    overrides = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    entries = overrides.get("hero_mode_costs", [])
    assert len(entries) == 11
    assert len({e["id"] for e in entries}) == 11
    assert {e["id"] for e in entries} == {
        c["id"] for c in printed if c["type"] == "hero"
    }

    name_prices = [c["command_cost"] for c in printed if c["type"] == "name"]
    assert name_prices and max(name_prices) == 4
    for e in entries:
        card = data[e["id"]]
        assert card["type"] == "hero" and card["unique"]
        expected_force = 1 + (card["force_strength"] + 1) // 2 + e["force_ability_premium"]
        assert e["force_ability_premium"] in (0, 1)
        assert e["force_cost"] == expected_force, e["id"]
        assert 1 <= e["name_cost"] <= 4, e["id"]
        assert 30 <= len(e["force_rationale"]) and 30 <= len(e["name_rationale"])
        assert card["hero_force_command_cost"] == card["command_cost"] == e["force_cost"]
        assert card["hero_name_command_cost"] == e["name_cost"]
        assert card["modes"]["force"]["command_cost"] == e["force_cost"]
        assert card["modes"]["name"]["command_cost"] == e["name_cost"]
        assert card["name_strength_modifier"] == 1
        assert card["force_strength"] == card["strength"]
        assert card["modes"]["force"]["effects"] and card["modes"]["name"]["effects"]
        print(
            f"  {card['title']}: {card['force_strength']} Strength, "
            f"{e['force_cost']}C as Force / {e['name_cost']}C as Name"
        )

    assert len(data) == 131
    print("PASS: all eleven dual-mode Hero prices valid; printed effects unchanged")
    print("These are role-by-role economic appraisals, not verified win rates.")


if __name__ == "__main__":
    main()
