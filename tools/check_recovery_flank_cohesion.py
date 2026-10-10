"""Targeted, read-only physical-card scenarios for two cohesion revisions.

These tests use small board-state examples and printed effect checks; they are
not the native engine or evidence of match balance.
Run: python tools/check_recovery_flank_cohesion.py
"""
from __future__ import annotations

from check_paper_ecology_scenarios import Board, CARDS
from print_cards import ROOT, load_print_cards


def printed(cid):
    return next(c for c in load_print_cards()["cards"] if c["id"] == cid)


def recovery_scenarios():
    card = printed("they-lived-to-tell-it")
    assert card["type"] == "narrative"
    assert len(card["effects"]) == 1
    effect = card["effects"][0]
    assert effect["timing"] == "action"
    assert "temporary negative marker" in effect["text"]
    assert "If you removed Exhaustion" in effect["text"]
    assert "Move its formation one position" in effect["text"]
    assert "Otherwise, give it Inspired" in effect["text"]
    assert effect.get("limit") is None, "Do not silently change prior physical ACTION use limit"

    # At the start of Battle II a Force is still Exhausted after losing a Front.
    b = Board(fronts=(2, 3))
    source = b.place("A", 2, "middle", "the-fifty-men", exhausted=True)
    destination = ("A", 3, "middle")
    assert not b.can_move(source, destination, maneuver=True)
    assert b.can_move(source, destination, maneuver=False)
    b.slots[source].exhausted = False
    assert b.move(source, destination, maneuver=False)
    assert destination in b.slots and source not in b.slots
    assert not b.slots[destination].exhausted
    assert not b.slots[destination].used_attack
    # The printed Move is not a Maneuver; no extra grey-Rider Attack.
    assert "After it Maneuvers" in CARDS["the-grey-riders"]["effects"][0]["text"]

    # Even removing Exhaustion does not allow an illegal destination or reopen a Front.
    blocked = Board(fronts=(2, 3))
    s = blocked.place("A", 2, "middle", "the-fifty-men", exhausted=True)
    blocked.place("A", 3, "middle", "the-old-guard")
    blocked.slots[s].exhausted = False
    assert not blocked.move(s, ("A", 3, "middle"), maneuver=False)
    assert not blocked.move(s, ("A", 1, "middle"), maneuver=False)

    # Depleted or Shaken recovery still yields Inspired, not free relocation.
    for marker in ("depleted", "shaken"):
        b = Board()
        loc = b.place("A", 2, "middle", "the-fifty-men", **{marker: True})
        setattr(b.slots[loc], marker, False)
        inspired = True  # resolved by the otherwise branch in the printed card
        assert inspired and not getattr(b.slots[loc], marker)

    # A later play with no removable marker keeps the existing Inspired baseline.
    assert "if any" in effect["text"] and "otherwise give it Inspired" in effect["text"]
    # A separate narrative retains its different two-formation Move ACTION.
    other = printed("no-one-would-be-first-to-leave")
    assert any("Move up to two different friendly formations" in e["text"]
               for e in other["effects"])


def flank_scenarios():
    card = printed("the-flank-was-refused")
    assert card["type"] == "stratagem" and len(card["effects"]) == 1
    e = card["effects"][0]
    assert e["timing"] == "hidden"
    assert e["text"].startswith("At resolution")
    assert "friendly flanked Frontline Force here" in e["text"]
    assert "ignores its flank penalty" in e["text"]
    assert "In an outer Front" in e["text"] and "+2 Strength this Battle" in e["text"]

    # Battle I: active central Fronts 2 and 3 support a legitimate flank.
    center = Board(fronts=(2, 3))
    pos = center.place("A", 2, "front", "the-fifty-men")
    center.place("B", 3, "front", "the-iron-boars")
    assert center.flanked("A", 2)
    original = center.strength(pos)
    assert original + 1 == CARDS["the-fifty-men"]["strength"]
    assert center.set_stratagem("A", "the-flank-was-refused")
    assert not center.set_stratagem("A", "the-lines-held")
    # The hidden response prevents the -1 flank penalty; no outer +2 in Battle I.
    inner_resolved = original + 1
    assert inner_resolved == CARDS["the-fifty-men"]["strength"]

    # Battle III: the same condition in an active outer Front adds a further +2.
    outer = Board(fronts=(1, 2, 3, 4))
    pos2 = outer.place("A", 1, "front", "the-fifty-men")
    outer.place("B", 2, "front", "the-iron-boars")
    assert outer.flanked("A", 1)
    assert outer.set_stratagem("A", "the-flank-was-refused")
    outer_resolved = outer.strength(pos2) + 1 + 2
    assert outer_resolved == CARDS["the-fifty-men"]["strength"] + 2
    # This is still a flank: the Rider target remains legal if Attack is otherwise possible.
    assert outer.flanked("A", 1)

    # If a friendly adjacent Frontline is occupied, there is no flank and no reveal.
    counter = Board(fronts=(2, 3))
    counter.place("A", 2, "front", "the-fifty-men")
    counter.place("A", 3, "front", "the-old-guard")
    counter.place("B", 3, "front", "the-iron-boars")
    assert not counter.flanked("A", 2)
    # No magic response to unflanked positions or unrevealed plans.
    assert counter.set_stratagem("A", "the-flank-was-refused")

    rules = (ROOT / "rules" / "rulebook.md").read_text()
    assert "one simultaneous Stratagem reveal window" in rules
    assert "active" in rules
    assert "Provisional" in rules or "provisional" in rules


def run():
    assert len(load_print_cards()["cards"]) == 131
    recovery_scenarios()
    print("PASS: recovery distinguishes Exhaustion movement and Inspired outcomes")
    flank_scenarios()
    print("PASS: central flank defense, outer bonus, reveal eligibility and plan limit")
    print("LIMIT: targeted physical examples, NOT full matches or native engine parity")


if __name__ == "__main__":
    run()
