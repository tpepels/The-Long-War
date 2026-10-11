"""Printed Tactic suppresses ACTION text and only *Name Strength* when Named."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from longwar.game.actions import BeginTurn, Discard, PlayTactic
from longwar.game.engine import GameEngine
from longwar.game.model import Front, Position, Rank

ROOT = Path(__file__).resolve().parents[1]
SUPPRESS_ACTION_BATTLE = 16
SUPPRESS_NAME_STRENGTH = 128


@pytest.fixture(scope="module")
def game():
    engine = GameEngine.from_file(str(ROOT / "cards" / "cards.json"))
    deck = json.loads((ROOT / "decks" / "mobility-open-bonds.json").read_text())["cards"]
    return engine, deck


def at(rank=Rank.MIDDLE, front=Front.SECOND):
    return Position(front, rank)


def start(game, *, named=True):
    engine, deck = game
    state = engine.new_game(deck, deck, seed=330, first_player=0)
    target = state.slot(1, at())
    target.force = "the-fifty-men"
    if named:
        target.bond = "stood-fast-with"
        target.name = "namar"  # exactly +1 printed Name Strength
    state.slot(1, at(Rank.FRONT)).force = "the-red-shields"
    state.players[0].hand[:] = ["they-let-them-through"]
    state.players[0].command = 20
    engine.apply(state, BeginTurn())
    while state.pending_draw_discard_for is not None:
        engine.apply(state, next(a for a in engine.legal_actions(state)
                                 if isinstance(a, Discard)))
    return engine, state


def use_tactic(engine, state):
    options = [a for a in engine.legal_actions(state)
               if isinstance(a, PlayTactic)
               and a.card_id == "they-let-them-through"
               and a.target is not None
               and a.target.player == 1
               and a.target.position == at()]
    assert options
    engine.apply(state, options[0])


def test_named_opponent_loses_name_strength_but_keeps_attached_name(game):
    engine, state = start(game)
    before = engine.position_strength(state, 1, at())
    neighbor = engine.position_strength(state, 1, at(Rank.FRONT))
    assert state.slot(1, at()).named

    use_tactic(engine, state)
    slot = state.slot(1, at())
    assert slot.named
    assert slot.name == "namar"
    assert slot.suppression_mask & SUPPRESS_ACTION_BATTLE
    assert slot.suppression_mask & SUPPRESS_NAME_STRENGTH
    assert engine.position_strength(state, 1, at()) == before - 1
    assert engine.position_strength(state, 1, at(Rank.FRONT)) == neighbor


def test_unnamed_opponent_loses_action_abilities_not_future_name_strength(game):
    engine, state = start(game, named=False)
    before = engine.position_strength(state, 1, at())
    use_tactic(engine, state)
    slot = state.slot(1, at())
    assert slot.suppression_mask & SUPPRESS_ACTION_BATTLE
    assert not slot.suppression_mask & SUPPRESS_NAME_STRENGTH
    assert engine.position_strength(state, 1, at()) == before
    # "If Named" is evaluated when the Tactic resolves, not retroactively.
    control = state.clone()
    control.slot(1, at()).bond = "stood-fast-with"
    control.slot(1, at()).name = "namar"
    expected = engine.position_strength(control, 1, at())
    slot.bond = "stood-fast-with"
    slot.name = "namar"
    assert engine.position_strength(state, 1, at()) == expected


def test_other_player_does_not_get_suppressed(game):
    engine, state = start(game)
    state.slot(0, at()).force = "the-fifty-men"
    use_tactic(engine, state)
    assert state.slot(0, at()).suppression_mask == 0
