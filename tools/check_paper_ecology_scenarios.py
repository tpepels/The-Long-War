"""Small, independent paper-rules scenario checks for the physical ecology pass.

Not a full engine, balance test, or win-rate simulation. The model covers exactly
the board/attack/opening-order rules exercised by these hand-authored scenarios;
all other card effects are checked against their actual printed wording.
Run: python tools/check_paper_ecology_scenarios.py
"""
from __future__ import annotations

from dataclasses import dataclass
from print_cards import load_print_cards

CARDS = {card["id"]: card for card in load_print_cards()["cards"]}
ROWS = ("front", "middle", "rear")
SIDES = ("A", "B")


@dataclass
class Piece:
    cid: str
    name: str | None = None
    exhausted: bool = False
    shaken: bool = False
    depleted: bool = False
    guarded: bool = False
    used_attack: bool = False


class Board:
    """Independent minimal state model; no engine/native card semantics used."""

    def __init__(self, fronts=(2, 3)):
        self.fronts = set(fronts)
        self.slots: dict[tuple[str, int, str], Piece] = {}
        self.command = {"A": 20, "B": 20}
        self.commits: dict[tuple[str, int], int] = {}
        self.set_plan = {"A": None, "B": None}

    def place(self, side, front, row, cid, **options):
        pos = (side, front, row)
        card = CARDS[cid]
        assert side in SIDES and front in self.fronts and row in ROWS
        assert card["type"] == "force" and pos not in self.slots
        assert row in card.get("allowed_rows", list(ROWS)), (cid, row)
        self.slots[pos] = Piece(cid, **options)
        return pos

    def classes(self, piece):
        classes = set(CARDS[piece.cid].get("classes", []))
        if piece.name:
            classes.update(CARDS[piece.name].get("classes", []))
        return classes

    def can_move(self, source, dest, *, maneuver=False):
        if source not in self.slots or dest in self.slots:
            return False
        side, front, row = source
        other, front2, row2 = dest
        if other != side or front2 not in self.fronts or row2 not in ROWS:
            return False
        if abs(front - front2) + abs(ROWS.index(row) - ROWS.index(row2)) != 1:
            return False
        piece = self.slots[source]
        if row2 not in CARDS[piece.cid].get("allowed_rows", list(ROWS)):
            return False
        if maneuver and piece.exhausted:
            texts = " ".join(e["text"] for e in CARDS[piece.cid].get("effects", []))
            if "may Maneuver while Exhausted" not in texts:
                return False
        return True

    def move(self, source, dest, *, maneuver=False):
        if not self.can_move(source, dest, maneuver=maneuver):
            return False
        self.slots[dest] = self.slots.pop(source)
        return True

    def flanked(self, side, front):
        if (side, front, "front") not in self.slots:
            return False
        other = "B" if side == "A" else "A"
        for neighbor in (front - 1, front + 1):
            if neighbor in self.fronts:
                if ((other, neighbor, "front") in self.slots
                        and (side, neighbor, "front") not in self.slots):
                    return True
        return False

    def strength(self, pos):
        piece = self.slots[pos]
        value = CARDS[piece.cid]["strength"]
        value -= 1 if piece.exhausted else 0
        value -= 2 if piece.shaken else 0
        value -= 1 if piece.depleted else 0
        value -= 1 if pos[2] == "front" and self.flanked(pos[0], pos[1]) else 0
        return max(0, value)

    def front_total(self, side, front):
        result = sum(self.strength((side, front, rank))
                     for rank in ROWS if (side, front, rank) in self.slots)
        if result:
            result += self.commits.get((side, front), 0)
        return result

    def can_attack(self, source, target):
        if source not in self.slots or target not in self.slots:
            return False
        side, f, row = source
        other, tf, tr = target
        if other == side:
            return False
        piece = self.slots[source]
        if piece.depleted or piece.used_attack:
            return False
        kinds = self.classes(piece)
        if "archer" in kinds and f == tf and tr == "rear":
            guard_pos = (other, tf, "middle")
            guard = self.slots.get(guard_pos)
            screened = (guard and "guard" in self.classes(guard)
                        and not guard.shaken and not guard.depleted)
            if not screened:
                return True
        if "skirmisher" in kinds and f == tf and tr == "middle":
            return True
        if "raider" in kinds and f == tf and row == "front" and tr in ("middle", "rear"):
            defender = (other, tf, "front")
            if defender not in self.slots or self.strength(source) > self.strength(defender):
                return True
        if ("rider" in kinds and row in ("front", "middle") and tr == "front"
                and abs(f - tf) == 1 and tf in self.fronts
                and self.flanked(other, tf)):
            return True
        return False

    def strike(self, source, target, *, prevalidated=False):
        if not prevalidated and not self.can_attack(source, target):
            return False
        kind = self.classes(self.slots[source])
        victim = self.slots[target]
        if victim.guarded:
            victim.guarded = False
        elif "raider" in kind and source[2] == "front":
            victim.depleted = True
        else:
            victim.shaken = True
        self.slots[source].used_attack = True
        return True

    def set_stratagem(self, side, cid):
        assert CARDS[cid]["type"] == "stratagem"
        if self.set_plan[side] is not None:
            return False
        self.set_plan[side] = cid
        return True

    def resolve_opening(self, a, b):
        """Just Commit/Hold/Maneuver/Strike; no generalized card-effect engine.

        Maneuvers are complete before Strikes regardless of printed order number.
        Opposing Strikes at a numbered step are prevalidated together so a
        newly applied Depleted marker cannot retroactively cancel the other.
        """
        assert len(a) == len(b) == 2
        orders = {"A": a, "B": b}
        for side in SIDES:
            for order in orders[side]:
                if order[0] == "commit":
                    front = order[1]
                    assert front in self.fronts and self.command[side] >= 1
                    assert any((side, front, row) in self.slots for row in ROWS)
                    self.command[side] -= 1
                    self.commits[(side, front)] = self.commits.get((side, front), 0) + 2
                else:
                    assert order[0] in ("hold", "maneuver", "strike")
        for number in (0, 1):
            for side in SIDES:
                order = orders[side][number]
                if order[0] == "maneuver":
                    src, dst = order[1]
                    self.move(src, dst, maneuver=True)
        for number in (0, 1):
            eligible = []
            for side in SIDES:
                order = orders[side][number]
                if order[0] == "strike":
                    src, dst = order[1]
                    if self.can_attack(src, dst):
                        eligible.append((src, dst))
            for src, dst in eligible:
                self.strike(src, dst, prevalidated=True)


def scenario_commit_vs_hold():
    base = Board()
    base.place("A", 2, "front", "the-late-banner")
    base.place("B", 2, "front", "the-old-guard")
    assert base.front_total("A", 2) == base.front_total("B", 2) == 3
    base.resolve_opening([("commit", 2), ("hold",)], [("hold",), ("hold",)])
    assert base.front_total("A", 2) == 5
    assert base.front_total("B", 2) == 3
    assert base.command["A"] == 19


def scenario_maneuvers_before_strikes():
    board = Board()
    archer = board.place("A", 2, "rear", "the-crow-archers")
    victim = board.place("B", 2, "rear", "the-fifty-men")
    old_guard = board.place("B", 2, "middle", "the-old-guard")
    assert not board.can_attack(archer, victim), "Guard screens rear initially"
    board.resolve_opening(
        [("strike", (archer, victim)), ("hold",)],
        [("hold",), ("maneuver", (old_guard, ("B", 2, "front")))])
    assert board.slots[victim].shaken, "Maneuver #2 exposes Rear before Strike #1"
    assert board.slots[archer].used_attack


def scenario_rider_flank_and_legal_move():
    board = Board()
    grey = board.place("A", 2, "middle", "the-grey-riders", exhausted=True)
    victim = board.place("B", 3, "front", "the-fifty-men")
    assert not board.can_attack(grey, victim), "Target is not yet flanked"
    forward = ("A", 2, "front")
    assert board.move(grey, forward, maneuver=True), "Grey has Exhausted-Maneuver exception"
    assert board.flanked("B", 3) and board.can_attack(forward, victim)
    assert board.strike(forward, victim) and board.slots[victim].shaken
    assert board.slots[forward].used_attack

    texts = " ".join(e["text"] for e in CARDS["the-long-march"]["effects"])
    assert "0 Command" in texts and "ordinary Maneuvers" in texts
    assert "Maneuver" in CARDS["the-battle-turned-east"]["effects"][0]["text"] or (
        "moves into or out" in CARDS["the-battle-turned-east"]["effects"][0]["text"])
    assert not board.can_attack(forward, victim), "Attack cannot repeat in Battle"


def scenario_frontline_conflict_and_stratagem_cap():
    board = Board()
    board.place("A", 2, "front", "the-red-duelists")
    try:
        board.place("A", 2, "front", "the-iron-boars")
    except AssertionError:
        pass
    else:
        raise AssertionError("Two Frontline-only Forces in one square looked legal")

    assert board.set_stratagem("A", "the-battle-turned-east")
    assert not board.set_stratagem("A", "the-center-must-hold")
    assert not board.set_stratagem("A", "no-step-back")


def scenario_scouter_action_and_defensive_choices():
    kael = CARDS["kael-the-roadless"]["modes"]["name"]["effects"][1]["text"]
    assert "Stratagem" in kael and "if any" in kael and "Move this formation" in kael
    assert "one adjacent legal position" in kael
    assert not any(e.get("limit") == "once_per_battle"
                   for e in CARDS["kael-the-roadless"]["modes"]["name"]["effects"][1:])

    alda = CARDS["alda-keeper-of-the-ford"]["modes"]["name"]["effects"][1]["text"]
    asha = CARDS["asha-the-shield-bearer"]["effects"][1]["text"]
    assert "Once per Battle" in alda and "give its Force Guarded" in alda
    assert "before that Tactic resolves" in alda
    assert "make it target this formation instead" in asha
    assert "make it target this formation instead" not in alda
    # An affliction is prevented by Guarded, not the entire Tactic or layer return.
    victim = Piece("the-fifty-men", guarded=True)
    if victim.guarded:
        victim.guarded = False
    else:
        victim.shaken = True
    assert not victim.shaken and not victim.guarded
    no_step = CARDS["no-step-back"]["effects"][0]["text"]
    assert "ignore its effect" in no_step and "prevent one affliction" in no_step

    taxes = [
        CARDS["the-red-shields"]["effects"][0]["text"],
        CARDS["the-serekh"]["effects"][0]["text"],
        CARDS["supported-by"]["effects"][0]["text"],
        CARDS["maelin"]["effects"][1]["text"],
    ]
    assert "this formation" in taxes[0]
    assert "directly behind" in taxes[1]
    assert "directly behind" in taxes[2] and "Middle" in taxes[2]
    assert "another friendly formation" in taxes[3]


def scenario_deck_package():
    import json
    from print_cards import ROOT
    source = json.loads((ROOT / "cards" / "playtest-decks.json").read_text())
    assert len(source["decks"]) == 6
    banner = next(d for d in source["decks"] if d["id"] == "banner-and-blood")
    copies = {entry["id"]: entry["copies"] for entry in banner["cards"]}
    assert sum(copies.values()) == 48
    assert sum(1 for amount in copies.values() if amount == 1) <= 18
    assert copies["the-grey-riders"] == copies["the-vardai"] == 2
    assert copies["the-long-march"] == copies["the-battle-turned-east"] == 2
    assert copies["the-center-must-hold"] == 1
    assert copies["every-banner-turned-toward-them"] == 1


def run():
    tests = [
        ("Commit vs Hold changes a tied Front", scenario_commit_vs_hold),
        ("all Maneuvers before Strikes even with reversed numbers", scenario_maneuvers_before_strikes),
        ("Rider flanking + Exhausted Maneuver + spent Attack", scenario_rider_flank_and_legal_move),
        ("Frontline competition and single hidden plan", scenario_frontline_conflict_and_stratagem_cap),
        ("Kael scouting and different protection decisions", scenario_scouter_action_and_defensive_choices),
        ("Rider demonstration package remains playable as 48-card deck", scenario_deck_package),
    ]
    for label, check in tests:
        check()
        print("PASS: " + label)
    print("Six PAPER SCENARIOS passed; legality examples only, NOT full gameplay or balance proof")


if __name__ == "__main__":
    run()
