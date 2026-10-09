"""Static final audit of the 131-card physical-print pool.

Checks comparative pricing corrections and six published deck compositions.
This is NOT a physical game simulator or an observed win-rate analysis.
"""
from __future__ import annotations

from collections import Counter
from math import comb
import json
import re

from print_cards import ROOT, load_print_cards


SUPPORT = {
    "the-white-hands-of-elara", "the-relief-column",
    "the-banner-singers", "the-lantern-scouts",
}
NAME_COSTS = {
    "kael-the-roadless": 1,
    "alda-keeper-of-the-ford": 2,
    "yara-the-chronicler": 2,
    "serai-queen-of-crows": 2,
    "doros-the-last-spear": 1,
}
TYPE_COUNTS = {
    "force": 33, "bond": 24, "name": 20, "hero": 11,
    "tactic": 14, "stratagem": 11, "narrative": 12, "order": 6,
}


def check() -> None:
    printed = load_print_cards()
    canonical = json.loads((ROOT / "cards/cards.json").read_text(encoding="utf-8"))
    ledger = json.loads((ROOT / "cards/force-pricing.json").read_text(encoding="utf-8"))
    decks = json.loads((ROOT / "cards/playtest-decks.json").read_text(encoding="utf-8"))
    by_id = {c["id"]: c for c in printed["cards"]}
    source = {c["id"]: c for c in canonical["cards"]}
    assert len(by_id) == len(source) == 131
    assert set(by_id) == set(source)
    assert Counter(c["type"] for c in printed["cards"]) == TYPE_COUNTS
    assert printed["print_only"] is True
    assert printed["print_strength_adjustment_count"] == 4

    for cid in SUPPORT:
        c = by_id[cid]
        assert c["type"] == "force"
        assert source[cid]["strength"] == 2 and c["strength"] == 3, cid
        assert c["command_cost"] == 3
        assert c["effects"], cid

    # Force tariff: 1 + ceil(Strength / 2) + ability premium - permitted
    # plain odd-Strength unused-half-point credit (Thirty Spears).
    rows = {row["id"]: row for row in ledger["forces"]}
    assert set(rows) == {c["id"] for c in printed["cards"] if c["type"] == "force"}
    for cid, row in rows.items():
        c = by_id[cid]
        assert row["premium"] in (0, 1)
        expected = 1 + (c["strength"] + 1) // 2 + row["premium"] - row.get(
            "unused_half_point_credit", 0
        )
        assert c["command_cost"] == expected, (cid, expected, c["command_cost"])
        if cid in SUPPORT:
            assert row["premium"] == 0

    # Independently priced Hero modes must keep their Force prices and Force
    # effects while improving the alternative Name-mode choice.
    for cid, name_cost in NAME_COSTS.items():
        c = by_id[cid]
        assert c["type"] == "hero" and c["unique"], cid
        assert c["hero_name_command_cost"] == name_cost
        assert c["modes"]["name"]["command_cost"] == name_cost
        assert c["command_cost"] == c["hero_force_command_cost"]
        assert c["modes"]["force"]["command_cost"] == c["hero_force_command_cost"]
        assert c["modes"]["force"]["effects"] == source[cid]["modes"]["force"]["effects"]
        assert c["force_strength"] == source[cid]["force_strength"]

    # Detect an obvious limitless free Strength engine on repeatable ACTIONs.
    for card in printed["cards"]:
        effects = (
            [e for mode in card["modes"].values() for e in mode["effects"]]
            if card["type"] == "hero" else card.get("effects", [])
        )
        for effect in effects:
            if (effect["timing"] == "action"
                    and re.search(r"\\+\\d+ Strength this Battle", effect["text"])
                    and "Pay " not in effect["text"]):
                assert effect.get("limit") == "once_per_battle", card["id"]

    assert len(decks["decks"]) == 6
    for deck in decks["decks"]:
        entries = deck["cards"]
        assert sum(e["copies"] for e in entries) == 48, deck["id"]
        assert all(e["id"] in by_id and e["copies"] >= 1 for e in entries)
        assert all(not by_id[e["id"]]["unique"] or e["copies"] == 1 for e in entries)
        forces = sum(
            e["copies"] for e in entries if by_id[e["id"]]["type"] == "force"
        )
        assert 16 <= forces <= 18, deck["id"]
        p_zero = comb(48 - forces, 10) / comb(48, 10)
        assert p_zero < 0.011, (deck["id"], p_zero)
        force_spend = sum(
            e["copies"] * by_id[e["id"]]["command_cost"]
            for e in entries if by_id[e["id"]]["type"] == "force"
        )
        print(f"  {deck['title']}: {forces} Forces, "
              f"{force_spend}C for all Force copies, "
              f"{p_zero:.1%} zero-Force opening-hand probability")

    assert all(c["command_cost"] == 1 for c in printed["cards"] if c["type"] == "bond")
    assert all(0 <= c["command_cost"] <= 5 for c in printed["cards"])
    print("PASS: 131-card family census, Force tariff, 4 support Strength boosts, "
          "5 Hero Name prices, 6 published decks and repeatable Strength hazard")
    print("LIMIT: no physical play results; this is a static balance audit.")


if __name__ == "__main__":
    check()
