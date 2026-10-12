"""Guard the 44-card identity pass without introducing new rules.

No engine dependency. This tests the physical printed Force pool against the
unchanged D6 probabilities and the existing card-local action vocabulary.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
POOL = ROOT / "cards/paper-d6.json"
DECKS = ROOT / "cards/paper-d6-decks.json"

FORBIDDEN = re.compile(
    r"\b(?:Pressure|Pin|Shaken|Exhausted|Tactical Read|Opportunity|"
    r"Bond|Named|marker|token|reroll|re-roll|reaction|interrupt|stun|"
    r"wound|charge counter)\b", re.I
)
ACTION = re.compile(r"^(?:Attack|Defend|Save|Draw)\b")

# Explicit zero-rule-change boundaries: no statuses, new phases, markers,
# counters, permanent abilities, or mandatory keywords in printed effects.
def test_all_44_have_distinct_printed_tactics() -> None:
    cards = json.loads(POOL.read_text(encoding="utf-8"))["cards"]
    assert len(cards) == 44
    assert len({c["id"] for c in cards}) == 44
    specials = [c["outcomes"]["S"]["effect"] for c in cards]
    assert len(set(specials)) == 44, "Every Force must have its own signature result"
    assert all(ACTION.match(text) for text in specials)
    for card in cards:
        effects = card["outcomes"]
        assert set(effects) == set(card["faces"]) == {"A", "D", "F", "S"} or (
            set(effects) == set(card["faces"]) == {"D", "F", "R", "S"}
        ), card["id"]
        assert len(card["faces"]) == 6
        assert effects["F"]["effect"].startswith(("Defend", "Save", "Draw"))
        assert "Nothing" not in " ".join(x["effect"] for x in effects.values())
        assert effects["D"]["effect"].startswith("Defend")
        if "A" in effects:
            assert effects["A"]["effect"].startswith("Attack")
        else:
            assert effects["R"]["effect"].startswith("Save")
        for outcome in effects.values():
            wording = outcome["effect"]
            assert 1 <= len(wording) <= 80, (card["id"], wording)
            assert not FORBIDDEN.search(wording), (card["id"], wording)
            assert not re.search(r"\b(?:this turn|permanent|next Battle)\b", wording, re.I)

    assert sum("If" in s for s in specials) >= 32
    assert sum("ally" in s.lower() for s in specials) >= 28
    assert sum("Order" in s for s in specials) >= 2
    # Capturing a Front still follows surviving majority; no printed card
    # overrides win conditions, deployment rules, costs or Command maximum.
    assert all("control" not in s.lower() for s in specials)


def test_every_role_has_distinctive_tactics() -> None:
    cards = json.loads(POOL.read_text(encoding="utf-8"))["cards"]
    roles: dict[str, list[str]] = {}
    for card in cards:
        roles.setdefault(card["role"], []).append(card["outcomes"]["S"]["effect"])
    assert len(roles) == 11
    assert all(len(set(entries)) == len(entries) for entries in roles.values())
    assert sum("Save" in s for s in roles["healer"]) >= 2
    assert sum(s.startswith("Attack") for s in roles["raider"]) >= 5
    assert sum(s.startswith("Defend") or s.startswith("Save")
               for s in roles["guard"]) >= 6
    assert sum("Attack" in s for s in roles["archer"]) >= 2


def test_existing_dice_formations_now_activate_card_local_interactions() -> None:
    cards = {c["id"]: c for c in json.loads(POOL.read_text(encoding="utf-8"))["cards"]}
    # These use the *actual* shared die face, not speculative combinations.
    scenarios = [
        (2, ["the-red-shields", "the-crow-archers", "the-white-hands-of-elara"],
         ["Defend", "Attack", "Save"]),
        (6, ["the-red-shields", "the-crow-archers", "the-white-hands-of-elara"],
         ["Attack", "Attack", "Save"]),
        (4, ["the-fifty-men", "thirty-spears", "the-first-spear"],
         ["Attack", "Attack", "Defend"]),
        (2, ["the-grey-riders", "the-dust-riders", "the-aradai"],
         ["Attack", "Attack", "Attack"]),
        (5, ["the-grey-riders", "the-dust-riders", "the-aradai"],
         ["Attack", "Attack", "Attack"]),
        (4, ["the-fifty-men", "the-first-spear", "the-relief-column"],
         ["Attack", "Defend", "Save"]),
    ]
    for die, lineup, actions in scenarios:
        actual = []
        for cid in lineup:
            card = cards[cid]
            text = card["outcomes"][card["faces"][die - 1]]["effect"]
            actual.append(next((action for action in ("Attack", "Defend", "Save")
                                if text.startswith(action)), "Nothing"))
        assert actual == actions, (die, lineup, actual, actions)

    # Specific design dependencies: a trigger and its partner are present
    # on the same die and can target the same enemy.
    assert "If it Attacks" in cards["the-red-shields"]["outcomes"]["S"]["effect"]
    assert "If an ally Defends" in cards["the-crow-archers"]["outcomes"]["A"]["effect"]
    assert "If an ally Attacks Frontline" in cards["the-dust-riders"]["outcomes"]["A"]["effect"]
    assert "If an ally Attacks this target" in cards["the-aradai"]["outcomes"]["S"]["effect"]
    assert "gains +1 Force" in cards["the-first-spear"]["outcomes"]["S"]["effect"]


def test_starter_deck_sizes_and_default_rules_unchanged() -> None:
    data = json.loads(DECKS.read_text(encoding="utf-8"))
    assert len(data["decks"]) == 3
    assert all(sum(item["copies"] for item in deck["cards"]) == 24
               for deck in data["decks"])
    rules = (ROOT / "rules/rulebook.md").read_text(encoding="utf-8")
    assert "one D6 per occupied Front" in rules
    assert "Defend cancels one Attack" in rules
    assert "one Order from their hand" in rules
    assert "no new" not in rules.lower()


def main() -> None:
    test_all_44_have_distinct_printed_tactics()
    test_every_role_has_distinctive_tactics()
    test_existing_dice_formations_now_activate_card_local_interactions()
    test_starter_deck_sizes_and_default_rules_unchanged()
    print("PASS: 44 distinct card-local Specials, coherent roles, six actual shared-roll combinations, no new rules.")


if __name__ == "__main__":
    main()
