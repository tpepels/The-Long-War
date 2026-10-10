"""Printed one-rank Move directions and Bond Strength selection."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from longwar.game.actions import BeginTurn, Discard, EffectChoice, PlayBond, PlayForce
from longwar.game.engine import GameEngine
from longwar.game.model import Front, Position, Rank

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def game():
    engine = GameEngine.from_file(str(ROOT / "cards" / "cards.json"))
    deck = json.loads((ROOT / "decks" / "mobility-open-bonds.json").read_text())["cards"]
    return engine, deck


def pos(rank):
    return Position(Front.SECOND, rank)


def prepare(game, card):
    engine, deck = game
    state = engine.new_game(deck, deck, seed=73, first_player=0)
    engine.apply(state, BeginTurn())
    while state.pending_draw_discard_for is not None:
        engine.apply(state, next(a for a in engine.legal_actions(state) if isinstance(a, Discard)))
    state.players[0].hand[:] = [card]
    state.players[0].command = 20
    return engine, state


def selected_effects(engine, state, destination):
    return [a for a in engine.legal_actions(state)
            if isinstance(a, EffectChoice)
            and a.destination is not None
            and a.destination.position == destination]


def test_damar_moves_a_different_formation_one_row_toward_frontline(game):
    engine, state = prepare(game, "the-damar")
    middle = pos(Rank.MIDDLE)
    front = pos(Rank.FRONT)
    state.slot(0, middle).force = "the-fifty-men"
    action = PlayForce("the-damar", pos(Rank.REAR))
    assert action in engine.legal_actions(state)
    engine.apply(state, action)
    picks = selected_effects(engine, state, middle)
    assert picks
    engine.apply(state, picks[0])
    assert state.slot(0, front).force == "the-fifty-men"
    assert state.slot(0, middle).force is None
    assert state.slot(0, pos(Rank.REAR)).force == "the-damar"


def test_damar_can_decline_optional_move(game):
    engine, state = prepare(game, "the-damar")
    middle = pos(Rank.MIDDLE)
    state.slot(0, middle).force = "the-fifty-men"
    engine.apply(state, PlayForce("the-damar", pos(Rank.REAR)))
    skip = [a for a in engine.legal_actions(state)
            if isinstance(a, EffectChoice) and a.skip]
    assert skip
    engine.apply(state, skip[0])
    assert state.slot(0, middle).force == "the-fifty-men"
    assert state.slot(0, pos(Rank.FRONT)).force is None


def test_ash_bowmen_move_only_opposing_frontline_toward_rear(game):
    engine, state = prepare(game, "the-ash-bowmen")
    frontline = pos(Rank.FRONT)
    middle = pos(Rank.MIDDLE)
    state.slot(1, frontline).force = "the-fifty-men"
    engine.apply(state, PlayForce("the-ash-bowmen", pos(Rank.REAR)))
    picks = selected_effects(engine, state, frontline)
    assert picks
    engine.apply(state, picks[0])
    assert state.slot(1, frontline).force is None
    assert state.slot(1, middle).force == "the-fifty-men"


def test_marched_with_bond_grants_one_strength_to_chosen_formation(game):
    engine, state = prepare(game, "marched-with")
    frontline = pos(Rank.FRONT)
    state.slot(0, frontline).force = "the-fifty-men"
    before = engine.position_strength(state, 0, frontline)
    engine.apply(state, PlayBond("marched-with", pos(Rank.REAR)))
    picks = selected_effects(engine, state, frontline)
    assert picks
    engine.apply(state, picks[0])
    assert engine.position_strength(state, 0, frontline) == before + 1
