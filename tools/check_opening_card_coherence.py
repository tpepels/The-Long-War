"""131-card paper-game coherence gate for Opening Orders and Maneuver simplification.

This checks printed cards and decks, not executable native-engine behavior or
gameplay win rates. Run: python tools/check_opening_card_coherence.py
"""
from __future__ import annotations

from collections import Counter
import json
import re

from print_cards import ROOT, load_print_cards

AUDIT = ROOT / "cards/whole-pool-opening-audit.json"
MAIN_DECKS = ROOT / "cards/playtest-decks.json"
LAB_DECKS = ROOT / "cards/mechanic-coverage-decks.json"
RULES = (ROOT / "rules/rulebook.md").read_text(encoding="utf-8")
PLAYER_RULES = (ROOT / "rules/player-rulebook.md").read_text(encoding="utf-8")

EXPECTED = {
    "force": 33, "bond": 24, "name": 20, "hero": 11,
    "tactic": 14, "stratagem": 11, "narrative": 12, "order": 6,
}
OPENING = {"had-been-ordered-forward", "the-long-march", "iria"}
EDITED = OPENING | {
    "the-dust-riders", "the-grey-riders", "teren",
    "the-center-must-hold", "the-flank-was-refused",
}
STRATAGEM_ROLES = {
    "the-ground-was-held", "the-lines-held", "no-step-back",
    "the-center-must-hold", "the-flank-was-refused",
    "the-trap-closed", "the-battle-turned-east", "there-was-no-road-back",
    "every-banner-turned-toward-them", "the-archers-were-ready",
    "the-scouts-had-warned-them",
}

def effects(card: dict) -> list[dict]:
    if card["type"] == "hero":
        return card["modes"]["force"]["effects"] + card["modes"]["name"]["effects"]
    return card.get("effects", [])

def text(card: dict) -> str:
    return " ".join(e["text"] for e in effects(card))

def contains(card: dict, *terms: str) -> bool:
    body = text(card)
    return all(term in body for term in terms)

def run() -> None:
    printed = load_print_cards()
    cards = {card["id"]: card for card in printed["cards"]}
    ledger = json.loads(AUDIT.read_text(encoding="utf-8"))
    rows = ledger["rows"]
    assert len(cards) == len(rows) == 131
    assert Counter(c["type"] for c in cards.values()) == EXPECTED
    assert ledger["card_counts"] == EXPECTED
    assert len({row["id"] for row in rows}) == 131
    assert {row["id"] for row in rows} == set(cards)
    assert set(ledger["opening_card_ids"]) == OPENING
    assert set(ledger["edited_card_ids"]) == EDITED
    assert set(ledger["stratagem_roles"]) == STRATAGEM_ROLES
    assert ledger["rules"]["narrative_cap"] == 4
    assert ledger["rules"]["stratagem_cap"].startswith("one set Stratagem")

    for row in rows:
        c = cards[row["id"]]
        es = effects(c)
        assert row["title"] == c["title"] and row["type"] == c["type"]
        assert row["effect_count"] == len(es), row["id"]
        assert row["max_effect_chars"] == max((len(e["text"]) for e in es), default=0), row["id"]
        cost = (
            {"force": c["modes"]["force"]["command_cost"],
             "name": c["modes"]["name"]["command_cost"]}
            if c["type"] == "hero" else c["command_cost"]
        )
        assert row["command"] == cost, row["id"]
        assert row["role"] and row["opening_relation"]
        if row["id"] in OPENING:
            assert row["status"] == "opening-order-redesign"
            assert row["max_effect_chars"] <= 160

    # No ordinary card may sell permission that the core Maneuver now gives
    # for free to every formation; exhaustion-only exceptions are different.
    obsolete = re.compile(
        r"(?:maneuver.{0,28}(?:without (?:a )?name|without being named|while unnamed)"
        r"|unnamed.{0,28}maneuver)", re.I
    )
    for c in cards.values():
        assert not obsolete.search(text(c)), (c["id"], text(c))
        for e in effects(c):
            assert not obsolete.search(e.get("exposed", "")), c["id"]

    assert contains(cards["had-been-ordered-forward"],
                    "Opening Maneuver", "up to two legal steps")
    assert contains(cards["the-long-march"],
                    "Opening Maneuver", "two different friendly Riders")
    assert contains(cards["iria"], "Opening Orders are revealed", "redirect one Strike",
                    "if this formation is Named")
    assert contains(cards["the-dust-riders"], "first Maneuver", "0 Command")
    assert contains(cards["the-grey-riders"], "while Exhausted",
                    "unused basic Rider Attack")
    assert contains(cards["teren"], "not set a Stratagem this Battle",
                    "without another Action")

    # All 11 stratagems have an auditable job different from a mere
    # post-reveal replay of a generic opening Maneuver + Commit.
    strat = [c for c in cards.values() if c["type"] == "stratagem"]
    assert len(strat) == 11
    assert {c["id"] for c in strat} == STRATAGEM_ROLES
    assert all(len(effects(c)) >= 1 for c in strat)
    assert contains(cards["the-lines-held"], "At resolution", "Move", "+2 Strength")
    assert contains(cards["the-center-must-hold"],
                    "At resolution", "King or Captain", "swap", "adjacent active Front")
    assert contains(cards["the-flank-was-refused"],
                    "At resolution in an outer Front",
                    "flanked Frontline Force", "ignores its flank penalty")
    assert not contains(cards["the-center-must-hold"], "give it +2 Strength")
    assert not contains(cards["the-flank-was-refused"], "You may Move")

    assert "**Any formation**" in PLAYER_RULES
    assert "**Any formation** may initiate" in RULES
    assert "set one Stratagem total per player per Battle" in PLAYER_RULES
    assert "set only one Stratagem card total per Battle" in RULES
    assert "Returning or revealing it does not" in PLAYER_RULES
    assert "The same sequence applies to every Battle, including Battle I" in RULES
    assert "up to **4 Narratives**" in RULES or "up to **4** Narratives" in RULES or "at most **4** Narratives" in RULES

    def decks(path):
        return json.loads(path.read_text(encoding="utf-8"))["decks"]
    decks_main, decks_lab = decks(MAIN_DECKS), decks(LAB_DECKS)
    assert len(decks_main) == 6 and len(decks_lab) == 4
    for d in decks_main + decks_lab:
        assert sum(x["copies"] for x in d["cards"]) == 48, d["id"]
        assert len({x["id"] for x in d["cards"]}) == len(d["cards"])
        assert all(x["id"] in cards and x["copies"] >= 1 for x in d["cards"])
    # Three repurposed identities appear in the actual reference deck;
    # they were not created as unrepresented, extra entries.
    broken = next(d for d in decks_main if d["id"] == "broken-oaths")
    in_broken = {x["id"] for x in broken["cards"]}
    assert OPENING <= in_broken
    rider = next(d for d in decks_lab if d["id"] == "rider-flank-lab")
    assert "the-long-march" in {x["id"] for x in rider["cards"]}
    seer = next(d for d in decks_lab if d["id"] == "seer-hidden-lab")
    assert "iria" in {x["id"] for x in seer["cards"]}

    print("PASS: 131 physical identities, 8 revised/revalued, 3 existing Opening Order cards")
    print("PASS: no redundant Named-only Maneuver privileges; one Stratagem/person/Battle")
    print("PASS: all 11 Stratagem roles remain distinct from Opening Order choices")
    print("PASS: all 10 playtest decks remain 48 cards; three revised cards included")
    print("LIMIT: does not prove tabletop balance, activation rates or native-engine behavior")


if __name__ == "__main__":
    run()
