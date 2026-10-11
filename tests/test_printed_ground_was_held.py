"""The Ground Was Held locks its reveal branch against pre-reveal Strength."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from longwar.game.actions import BeginTurn, Discard, EffectChoice, EndTurn, Pass
from longwar.game.engine import GameEngine
from longwar.game.model import Front, Position, Rank, StratagemState

ROOT = Path(__file__).resolve().parents[1]
HERE = Front.SECOND


@pytest.fixture(scope="module")
def game():
    e = GameEngine.from_file(str(ROOT / "cards" / "cards.json"))
    deck = json.loads((ROOT / "decks" / "mobility-open-bonds.json").read_text())["cards"]
    return e, deck


def at(rank):
    return Position(HERE, rank)


def close_battle(e, s):
    e.apply(s, Pass())
    for _ in range(2):
        e.apply(s, BeginTurn())
        while s.pending_draw_discard_for is not None:
            e.apply(s, next(a for a in e.legal_actions(s) if isinstance(a, Discard)))
        e.apply(s, EndTurn())


def picks(e, s, kind):
    return [a for a in e.legal_actions(s)
            if isinstance(a, EffectChoice) and a.effect == kind]


def decide(e, s, reveal):
    e.apply(s, next(a for a in picks(e, s, "stratagem-reveal")
                    if a.skip != reveal))


def baseline(game, *, deficit=0, opponent_center=False):
    e, deck = game
    s = e.new_game(deck, deck, seed=218, first_player=0)
    own = s.slot(0, at(Rank.FRONT))
    own.force = "the-fifty-men"
    own.bond = "guarded"
    own.name = "mara"
    enemy = s.slot(1, at(Rank.FRONT))
    enemy.force = "the-late-banner" if opponent_center else "the-fifty-men"
    if opponent_center:
        s.slot(1, at(Rank.MIDDLE)).force = "the-fifty-men"
        s.stratagems[1] = StratagemState(
            "the-center-must-hold", fronts=(HERE,),
        )
    s.stratagems[0] = StratagemState("the-ground-was-held", fronts=(HERE,))
    # Balance provisional Strength independently of the cards' printed
    # numeric values; the test targets tie/deficit eligibility and outcomes.
    ours = e.front_strength(s, 0, HERE)
    theirs = e.front_strength(s, 1, HERE)
    if ours > theirs - deficit:
        enemy.temporary_strength += ours - (theirs - deficit)
    else:
        own.temporary_strength += (theirs - deficit) - ours
    # Ensure player 0 would tie (deficit=0) or lose by exactly one (deficit=1).
    assert e.front_strength(s, 1, HERE) - e.front_strength(s, 0, HERE) == deficit
    close_battle(e, s)
    return e, s


def test_on_pre_reveal_tie_owner_can_win_only_if_revealed(game):
    e, s = baseline(game)
    assert len(picks(e, s, "stratagem-reveal")) == 2
    decide(e, s, reveal=True)
    # Player 0 alone has Named here; the revealed tie-break applies at final
    # comparison and cannot be treated as a free Strength marker.
    assert "the-ground-was-held" in s.players[0].discard
    assert s.slot(0, at(Rank.FRONT)).temporary_strength >= 0
    assert s.battle_resolution is not None
    assert s.battle_resolution["lost_masks"][1] & (1 << int(HERE))


def test_initial_one_point_deficit_grants_two_strength_to_named_force(game):
    e, s = baseline(game, deficit=1)
    before = s.slot(0, at(Rank.FRONT)).temporary_strength
    decide(e, s, reveal=True)
    buff = picks(e, s, "stratagem-buff")
    assert len(buff) == 1 and buff[0].source is not None
    e.apply(s, buff[0])
    assert s.slot(0, at(Rank.FRONT)).temporary_strength == before + 2
    assert s.battle_resolution is not None
    assert s.battle_resolution["lost_masks"][1] & (1 << int(HERE))


def test_initial_tie_break_does_not_win_if_opponent_reveals_extra_strength(game):
    e, s = baseline(game, opponent_center=True)
    decide(e, s, reveal=True)
    assert not s.stratagems[0].revealed
    decide(e, s, reveal=True)
    assert s.stratagems[0].revealed and s.stratagems[1].revealed
    buff = picks(e, s, "stratagem-buff")
    assert buff
    e.apply(s, next(a for a in buff if a.source is not None))
    # The opponent's +1 breaks the tie, invalidating the tie-only result.
    assert s.battle_resolution is not None
    assert s.battle_resolution["lost_masks"][0] & (1 << int(HERE))
    assert not (s.battle_resolution["lost_masks"][1] & (1 << int(HERE)))


def test_no_reveal_when_opponent_has_named_here_too(game):
    e, deck = game
    s = e.new_game(deck, deck, seed=218, first_player=0)
    for player in (0, 1):
        slot = s.slot(player, at(Rank.FRONT))
        slot.force = "the-fifty-men"
        slot.bond = "guarded"
        slot.name = "mara"
    s.stratagems[0] = StratagemState("the-ground-was-held", fronts=(HERE,))
    close_battle(e, s)
    actions = picks(e, s, "stratagem-reveal")
    assert len(actions) == 1 and actions[0].skip
