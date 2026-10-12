"""Cost-band contract for the physical D6 edition.

Prices are curated design hypotheses, not statistically established win rates.
This intentionally does not change Command recovery or the executable engine.
"""
from collections import Counter
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]

CANONICAL = dict(line.split() for line in """the-fifty-men 4
seven-black-ships 4
the-white-hands-of-elara 3
the-red-shields 4
the-crow-archers 4
the-house-of-reed 4
the-grey-riders 4
the-dust-riders 3
the-black-company 4
the-red-duelists 3
the-thornbow-hunters 4
the-iron-boars 5
the-first-spear 3
the-old-guard 2
the-unnamed-host 4
the-late-banner 3
the-banner-singers 3
thirty-spears 3
a-hundred-shields 5
the-vardai 2
the-aradai 4
the-ilyri 2
the-damar 4
the-serekh 2
the-relief-column 3
the-field-train 2
the-signal-company 3
avaros-the-bronze-king 5
kael-the-roadless 3
rovan-the-gatebreaker 5
alda-keeper-of-the-ford 4
tovan-the-quartermaster 2
nara-builder-of-walls 4
neris-the-ferryman 4
veyra-keeper-of-oaths 4
yara-the-chronicler 3
the-ash-bowmen 4
the-lantern-scouts 3
the-river-raiders 4
the-kings-spears 2
the-salt-road-fleet 3
the-watchtowers-of-eren 3
serai-queen-of-crows 4
doros-the-last-spear 5""".splitlines())


def main() -> None:
    cards = json.loads((ROOT / "cards/paper-d6.json").read_text())["cards"]
    price = {c["id"]: c["command_cost"] for c in cards}
    assert len(price) == len(CANONICAL) == 44
    assert all(v == int(CANONICAL[k]) for k, v in price.items())
    assert Counter(price.values()) == {2: 7, 3: 14, 4: 18, 5: 5}
    assert all(c["command_cost"] == 2 or c["command_cost"] >= 3 for c in cards)
    assert all(c["force"] <= 3 for c in cards if c["command_cost"] == 2)
    assert all(c["force"] >= 5 for c in cards if c["command_cost"] == 5)

    # Three playable demo lists stay complete and remain inside a deliberately
    # varied but compatible deployment economy with 20 starting Command.
    decks = json.loads((ROOT / "cards/paper-d6-decks.json").read_text())["decks"]
    assert {d["id"] for d in decks} == {
        "shield-and-volley", "riders-and-raids", "sustain-and-control"
    }
    totals = {}
    for deck in decks:
        assert sum(e["copies"] for e in deck["cards"]) == 24
        totals[deck["id"]] = sum(e["copies"] * price[e["id"]]
                                 for e in deck["cards"])
    assert totals == {
        "shield-and-volley": 84,
        "riders-and-raids": 81,
        "sustain-and-control": 77,
    }

    rulebook = (ROOT / "rules/rulebook.md").read_text()
    assert "20 Command" in rulebook and "5 Command" in rulebook
    assert "1 Command" in rulebook and "Never spend below zero" in rulebook
    print("PASS: 44 prices in cost bands 2/3/4/5; three starter budgets; unchanged Command rules.")


if __name__ == "__main__":
    main()
