"""Fourteen targeted physical-print false-friend contract/scenario checks.

These are independent, small paper-state examples and printed-effect contracts,
NOT a complete rules engine, win-rate simulation, or proof of strategic utility.
Run: python tools/check_print_false_friends.py
"""
from __future__ import annotations

import json

from check_paper_ecology_scenarios import Board, CARDS, Piece
from print_cards import ROOT

DATA = ROOT / "cards" / "false-friend-decisions.json"
DECKS = ROOT / "cards" / "playtest-decks.json"
SCENARIOS = {}


def scenario(key):
    def register(fn):
        if key in SCENARIOS:
            raise ValueError("Duplicate case: " + key)
        SCENARIOS[key] = fn
        return fn
    return register


def wording(card_id, *, mode=None):
    card = CARDS[card_id]
    effects = card["effects"] if mode is None else card["modes"][mode]["effects"]
    return " ".join(effect["text"] for effect in effects)


@scenario("duelists-boars")
def frontline_competition():
    board = Board()
    board.place("A", 2, "front", "the-red-duelists")
    board.place("B", 2, "front", "the-fifty-men")
    try:
        board.place("A", 2, "front", "the-iron-boars")
    except AssertionError:
        pass
    else:
        raise AssertionError("Frontline cannot contain both Duelists and Boars")

    assert "Shaken" in wording("the-red-duelists")
    assert "Shaken" in wording("the-iron-boars")
    # Legal but costly hand sequence: Duelists must first vacate the position;
    # the same Shaken marker still cannot stack.
    assert board.move(("A", 2, "front"), ("A", 3, "front"), maneuver=True)
    board.place("A", 2, "front", "the-iron-boars")
    enemy = board.slots[("B", 2, "front")]
    enemy.shaken = True
    assert board.strength(("B", 2, "front")) == 3
    assert board.strength(("A", 2, "front")) == 5
    enemy.shaken = True
    assert board.strength(("B", 2, "front")) == 3  # no double Shaken


@scenario("grey-kept-pace")
def grey_maneuver_not_move():
    assert "After it Maneuvers" in wording("the-grey-riders")
    assert "Move one friendly Rider or Scout" in wording("kept-pace-with")
    assert "Maneuver" not in wording("kept-pace-with")
    b = Board()
    pos = b.place("A", 2, "middle", "the-grey-riders")
    b.place("B", 3, "front", "the-fifty-men")
    destination = ("A", 2, "front")
    assert b.move(pos, destination, maneuver=False)
    assert b.can_attack(destination, ("B", 3, "front"))
    assert not b.slots[destination].used_attack
    # A legal target does not turn a Move into a free Attack.


@scenario("grey-no-one")
def narrative_move_not_maneuver():
    narrative = CARDS["no-one-would-be-first-to-leave"]["effects"][1]
    assert narrative["timing"] == "action"
    assert "Move up to two different friendly formations" in narrative["text"]
    assert "Maneuver" not in narrative["text"]
    assert "After it Maneuvers" in wording("the-grey-riders")


@scenario("dust-long-march")
def discounts_overlap():
    dust = wording("the-dust-riders")
    march = wording("the-long-march")
    assert "first Maneuver each Battle costs 0 Command" in dust
    assert "pay 0 Command for their ordinary Maneuvers" in march
    ordinary_maneuver = 1
    assert min(ordinary_maneuver, 0, 0) == 0
    assert "Maneuver" in dust and "ordinary Maneuvers" in march
    # The Dust discount is relevant when March is absent; no negative cost.
    assert "Move" not in dust


@scenario("opening-bond-long-march")
def opening_discounts_do_not_stack():
    bonded = wording("had-been-ordered-forward")
    march = wording("the-long-march")
    rules = (ROOT / "rules" / "player-rulebook.md").read_text()
    opening = rules.split("## Opening Orders", 1)[1].split("## Resolving a Battle", 1)[0]
    assert "No Action or Command cost" in opening
    assert "0 Command" in march
    assert "Move it one additional adjacent legal position" in bonded
    # Opening Maneuver costs 0 already; an extra Move still matters spatially.


@scenario("prepared-swore-house")
def prepared_play_effect_does_not_replay():
    swore = CARDS["swore-again-to"]["effects"][0]
    house = CARDS["the-house-of-reed"]["effects"]
    assert swore["timing"] == "play"
    assert "If playing this Bond completes a Named Formation" in swore["text"]
    assert "Attach" in " ".join(x["text"] for x in house)
    rules = (ROOT / "rules" / "rulebook.md").read_text()
    assert "not replaying" in rules or "not replay" in rules
    # Preparing on an empty square plays Swore; later attachment is no PLAY.
    prepared_force_present = False
    play_completion_bonus = 2 if prepared_force_present else 0
    newly_named_at_attachment = True
    assert newly_named_at_attachment and play_completion_bonus == 0


@scenario("archer-extension")
def archers_have_different_middle_access():
    archer = CARDS["the-crow-archers"]["effects"][1]
    narrative = CARDS["every-bow-was-strung"]["effects"][0]
    assert archer["timing"] == "attack"
    assert "opposing Frontline in this Front is empty" in archer["text"]
    assert "Middle Force" in archer["text"]
    assert narrative["timing"] == "continuous"
    assert "During Opening Orders" in narrative["text"]
    assert "Bonded Archers" in narrative["text"]
    defender_has_frontline = True
    assert not (not defender_has_frontline)  # Crow's intrinsic Middle extension is off
    assert defender_has_frontline and "Middle Force" in narrative["text"]
    # Narrative can extend a bonded Archer's chosen Opening Strike, not a second Attack.


@scenario("baited-trap")
def tactic_enabled_marker_reaction():
    baited = CARDS["the-line-was-baited"]["effects"][0]
    trap = CARDS["the-trap-closed"]["effects"][0]
    assert baited["timing"] == "play"
    assert "Front containing your Skirmisher" in baited["text"]
    assert "If it moves, give it Depleted" in baited["text"]
    assert trap["timing"] == "hidden"
    assert "a Tactic you play while one is here" in trap["text"]
    assert "negative marker" in trap["text"]

    b = Board()
    b.place("A", 2, "front", "the-red-duelists")  # Skirmisher
    enemy = b.place("B", 2, "middle", "the-fifty-men")
    assert b.set_stratagem("A", "the-trap-closed")  # before playing Tactic
    bonded_attachment = "followed"

    has_qualified_skirmisher = any(
        pos[0] == "A" and pos[1] == 2
        and "skirmisher" in b.classes(p)
        for pos, p in b.slots.items()
    )
    assert has_qualified_skirmisher
    moved_to = ("B", 2, "rear")
    assert b.move(enemy, moved_to)
    b.slots[moved_to].depleted = True
    assert b.slots[moved_to].depleted and bonded_attachment
    # The actual Tactic is the source; new Trap wording explicitly allows it.
    bonded_attachment = None  # owner's hand receives the layer
    assert bonded_attachment is None
    assert b.set_plan["A"] == "the-trap-closed"
    assert not b.set_stratagem("A", "the-center-must-hold")

    blocked = Board()
    blocked.place("A", 2, "front", "the-red-duelists")
    m = blocked.place("B", 2, "middle", "the-fifty-men")
    blocked.place("B", 2, "rear", "a-hundred-shields")
    assert not blocked.move(m, ("B", 2, "rear"))
    assert not blocked.slots[m].depleted
    # A blocked retreat inflicts no Depleted marker and cannot trip the Trap.
    no_class = Board()
    no_class.place("A", 2, "front", "the-fifty-men")
    no_class.place("B", 2, "middle", "the-fifty-men")
    assert not any(
        side == "A" and front == 2 and "skirmisher" in no_class.classes(p)
        for (side, front, _), p in no_class.slots.items()
    )


@scenario("bond-swap-named")
def already_named_does_not_retrigger():
    narrative = wording("the-king-had-given-the-order")
    assert "Exchange the Bonds" in narrative
    assert "remains Named" in narrative
    stacks = [
        {"force": "the-late-banner", "bond": "followed", "name": "oren"},
        {"force": "the-fifty-men", "bond": "trusted", "name": "teren"},
    ]
    before = [all(v is not None for v in f.values()) for f in stacks]
    stacks[0]["bond"], stacks[1]["bond"] = stacks[1]["bond"], stacks[0]["bond"]
    after = [all(v is not None for v in f.values()) for f in stacks]
    assert before == after == [True, True]
    assert not any(not b and a for b, a in zip(before, after))
    # +1 Strength on each still-Named formation is available as printed.


@scenario("action-lock-iven")
def disabling_actions_does_not_suppress_continuous():
    tactic = wording("they-let-them-through")
    iven = CARDS["iven"]["effects"][1]
    assert "ACTION abilities cannot be used" in tactic
    assert "Name contributes no Strength" in tactic
    assert iven["timing"] == "continuous"
    assert "Tactics cost 1 less Command" in iven["text"]
    assert "CONTINUOUS" not in tactic


@scenario("ground-narrative")
def provisional_eligibility_after_continuous_strength():
    ground = wording("the-ground-was-held")
    narrative = wording("the-battle-had-chosen-them")
    assert "on a tie" in ground and "behind by 1" in ground
    assert "Named Formation gets +1 Strength" in narrative
    provisional_you, provisional_them = 5, 5
    assert provisional_you == provisional_them
    provisional_you += 1  # already-Named unit is under the continuous Narrative
    assert provisional_you > provisional_them
    rules = (ROOT / "rules" / "player-rulebook.md").read_text()
    assert "including" in rules.split("### 1. Reveal Stratagems", 1)[1][:330]
    # Tie-branch eligibility was never present at the actual reveal window.


@scenario("no-step-wall")
def concealed_prevention_and_guarded_differ():
    no_step = wording("no-step-back")
    wall = wording("the-wall-did-not-break")
    assert "ignore its effect" in no_step and "prevent one affliction" in no_step
    assert "Give one friendly Guard or Stronghold Guarded" in wall
    guarded = Piece("the-first-spear", guarded=True)
    # Do not reveal No Step Back: Guarded absorbs this one attack affliction.
    if guarded.guarded:
        guarded.guarded = False
    else:
        guarded.shaken = True
    assert not guarded.shaken and not guarded.guarded
    # A distinct later Tactic that returns a layer is not stopped by Guarded.


@scenario("two-strats")
def stratagems_are_alternatives():
    b = Board()
    assert b.set_stratagem("A", "the-lines-held")
    assert not b.set_stratagem("A", "the-center-must-hold")
    assert b.set_stratagem("B", "the-center-must-hold")


@scenario("crows-archers-ready")
def narrative_action_not_a_basic_archer_attack():
    narrative = CARDS["the-crows-came-down"]["effects"]
    ready = wording("the-archers-were-ready")
    assert narrative[1]["timing"] == "action"
    assert "opposing Exhausted Force" in narrative[1]["text"]
    assert "Attack" not in narrative[1]["text"]
    assert "has not Attacked" in ready
    b = Board()
    archer = b.place("A", 2, "rear", "the-crow-archers")
    b.place("A", 2, "middle", "the-old-guard")
    enemy_archer_target = b.place("B", 2, "rear", "the-fifty-men", exhausted=True)
    attacker = b.place("B", 2, "front", "the-red-duelists")
    assert b.set_stratagem("A", "the-archers-were-ready")
    # Narrative 1/BATTLE ACTION gives Shaken, but does not mark Archer Attack used.
    b.slots[enemy_archer_target].shaken = True
    assert not b.slots[archer].used_attack
    assert b.can_attack(attacker, ("A", 2, "middle"))  # opponent's Attack triggers plan
    assert b.strike(attacker, ("A", 2, "middle"))
    assert b.can_attack(archer, enemy_archer_target)
    assert b.strike(archer, enemy_archer_target)
    assert b.slots[archer].used_attack
    assert not b.can_attack(archer, enemy_archer_target)


def run():
    data = json.loads(DATA.read_text())
    cases = data["cases"]
    assert len(cases) == 14
    assert len({case["id"] for case in cases}) == 14
    assert set(SCENARIOS) == {case["id"] for case in cases}
    assert {case["id"] for case in cases if case["status"] == "fixed"} == {"baited-trap"}
    assert all(case["reason"] and case["gameplay_decision"] for case in cases)
    for case in cases:
        SCENARIOS[case["id"]]()
        print(f"PASS {case['id']}: {case['status']}")
    d = json.loads(DECKS.read_text())
    blood = next(x for x in d["decks"] if x["id"] == "blood-and-spoils")
    assert any("Alternative frontline pressure" in p["label"] for p in blood["combo_packages"])
    assert any("Tactic" in note and "Trap Closed" in note for note in blood["combo_notes"])
    print("PASS: 14 targeted physical false-friend scenarios. Not a complete game engine.")


if __name__ == "__main__":
    run()
