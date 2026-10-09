"""Advisory sanity for the four print-only combo playtest decks.

This checks composition, source data and documented payoffs; it does not freeze
a particular deck recipe or claim win-rate balance.
"""
from __future__ import annotations

import json

from print_cards import ROOT, load_print_cards


def run() -> None:
    print_cards = {c["id"]: c for c in load_print_cards()["cards"]}
    assert len(print_cards) == 131
    data = json.loads((ROOT / "cards" / "playtest-decks.json").read_text(encoding="utf-8"))
    decks = data["decks"]
    assert len(decks) == 4
    assert len({d["id"] for d in decks}) == len(decks)
    for deck in decks:
        names = [entry["id"] for entry in deck["cards"]]
        assert len(names) == len(set(names)), deck["id"] + " duplicate entries"
        for entry in deck["cards"]:
            c = print_cards[entry["id"]]
            copies = entry["copies"]
            assert type(copies) is int and 1 <= copies <= (1 if c.get("unique") else 4), (
                deck["id"], entry["id"])
        total = sum(entry["copies"] for entry in deck["cards"])
        assert total == data["deck_size"] == 48, deck["id"]
        count = lambda kind: sum(e["copies"] for e in deck["cards"]
                                 if print_cards[e["id"]]["type"] == kind)
        force_count = count("force")
        name_count = count("name")
        assert force_count >= 14 and name_count >= 5, (
            deck["id"], "insufficient baseline Forces / Names")
        assert len(deck["combo_notes"]) >= 3 and len(deck["hypothesis"]) >= 25
        command = sum(print_cards[e["id"]]["command_cost"] * e["copies"]
                      for e in deck["cards"])
        force_strength = sum(print_cards[e["id"]]["strength"] * e["copies"]
                             for e in deck["cards"]
                             if print_cards[e["id"]]["type"] == "force")
        print(f"  {deck['title']}: {total} cards, {force_count} Forces, "
              f"{name_count} Names, {command} listed Command, "
              f"{force_strength} printed Force Strength, "
              f"{len(deck['combo_notes'])} combo descriptions")

    print("PASS: four physical combo decks structurally legal; win rates unmeasured")


if __name__ == "__main__":
    run()
