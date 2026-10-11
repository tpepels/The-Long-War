"""Printed The Muster Was False: prepared targets or Scout/Seer-enabled Bond."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from longwar.game.actions import BeginTurn, Discard, PlayTactic
from longwar.game.engine import GameEngine
from longwar.game.model import Front, Position, Rank

ROOT = Path(__file__).resolve().parents[1]
HERE = Front.SECOND
ELSEWHERE = Front.THIRD


@pytest.fixture(scope="module")
def game():
    engine = GameEngine.from_file(str(ROOT / "cards" / "cards.json"))
    deck = json.loads((ROOT / "decks" / "mobility-open-bonds.json").read_text())["cards"]
    return engine, deck


def pos(front=HERE, rank=Rank.MIDDLE):
    return Position(front, rank)


def setup(game):
    engine, deck = game
    state = engine.new_game(deck, deck, seed=911, first_player=0)
    state.players[0].command = 20
    engine.apply(state, BeginTurn())
    while state.pending_draw_discard_for is not None:
        engine.apply(state, next(
            a for a in engine.legal_actions(state) if isinstance(a, Discard)
        ))
    state.players[0].hand[:] = ["the-muster-was-false"]
    state.players[1].hand[:] = []
    return engine, state


def tactics(engine, state):
    return [
        a for a in engine.legal_actions(state)
        if isinstance(a, PlayTactic) and a.card_id == "the-muster-was-false"
    ]


def take(engine, state, at, component):
    matching = [
        a for a in tactics(engine, state)
        if a.target is not None
        and a.target.position == at
        and a.option == component
    ]
    assert len(matching) == 1, tactics(engine, state)
    engine.apply(state, matching[0])


def test_prepared_bond_is_returned_without_any_scout_or_seer(game):
    engine, state = setup(game)
    target = state.slot(1, pos())
    target.bond = "carried-the-oath-of"
    take(engine, state, pos(), "bond")
    assert target.bond is None
    assert "carried-the-oath-of" in state.players[1].hand
    assert state.operations_this_battle[0] == 1


def test_prepared_name_is_returned_without_scout_or_seer(game):
    engine, state = setup(game)
    target = state.slot(1, pos())
    target.name = "oren"
    take(engine, state, pos(), "name")
    assert target.name is None
    assert "oren" in state.players[1].hand


def test_scout_in_same_front_allows_attached_enemy_bond_only(game):
    engine, state = setup(game)
    state.slot(0, pos()).force = "the-lantern-scouts"
    target = state.slot(1, pos())
    target.force = "the-crow-archers"
    target.bond = "carried-the-oath-of"
    target.name = "oren"
    matching = [a for a in tactics(engine, state)
                if a.target is not None and a.target.position == pos()]
    assert len(matching) == 1 and matching[0].option == "bond"
    engine.apply(state, matching[0])
    assert target.force == "the-crow-archers"
    assert target.bond is None and target.name == "oren"
    assert "carried-the-oath-of" in state.players[1].hand


def test_scout_in_different_front_does_not_enable_attached_bond(game):
    engine, state = setup(game)
    state.slot(0, pos(ELSEWHERE)).force = "the-lantern-scouts"
    target = state.slot(1, pos())
    target.force = "the-crow-archers"
    target.bond = "carried-the-oath-of"
    assert not tactics(engine, state)


def test_no_scout_or_seer_does_not_enable_attached_bond(game):
    engine, state = setup(game)
    target = state.slot(1, pos())
    target.force = "the-crow-archers"
    target.bond = "carried-the-oath-of"
    assert not tactics(engine, state)


def test_seer_in_named_formation_enables_attached_bond(game):
    engine, state = setup(game)
    friendly = state.slot(0, pos())
    friendly.force = "the-crow-archers"
    friendly.bond = "carried-the-oath-of"
    friendly.name = "iria"
    enemy = state.slot(1, pos())
    enemy.force = "the-crow-archers"
    enemy.bond = "carried-the-oath-of"
    take(engine, state, pos(), "bond")
    assert enemy.bond is None
    assert friendly.name == "iria"
