"""Mara's printed BECOMES NAMED hand inspection and optional legal Move."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from longwar.game.actions import BeginTurn, Discard, EffectChoice, PlayBond
from longwar.game.engine import GameEngine
from longwar.game.model import Front, Position, Rank

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def game():
    engine = GameEngine.from_file(str(ROOT / "cards" / "cards.json"))
    deck = json.loads((ROOT / "decks" / "mobility-open-bonds.json").read_text())["cards"]
    return engine, deck


def pos(front=Front.SECOND, rank=Rank.MIDDLE):
    return Position(front, rank)


def start(game):
    engine, deck = game
    state = engine.new_game(deck, deck, seed=72, first_player=0)
    engine.apply(state, BeginTurn())
    while state.pending_draw_discard_for is not None:
        engine.apply(state, next(a for a in engine.legal_actions(state)
                                 if isinstance(a, Discard)))
    state.players[0].hand[:] = ["stood-fast-with"]
    state.players[1].hand[:] = ["the-fifty-men", "the-old-guard"]
    state.players[0].command = 20
    source = state.slot(0, pos())
    source.force = "the-fifty-men"
    source.name = "mara"  # prepared Name completes when the Bond is played
    return engine, state


def reveal(engine, state):
    action = PlayBond("stood-fast-with", pos())
    assert action in engine.legal_actions(state)
    engine.apply(state, action)


def test_mara_reveals_full_opposing_hand_and_can_move_complete_formation(game):
    engine, state = start(game)
    reveal(engine, state)
    assert state.known_hidden_count(0, 1, "the-fifty-men") == 1
    assert state.known_hidden_count(0, 1, "the-old-guard") == 1
    destination = pos(Front.THIRD, Rank.MIDDLE)
    move = next(a for a in engine.legal_actions(state)
                if isinstance(a, EffectChoice)
                and a.destination is not None and a.destination.position == destination)
    engine.apply(state, move)
    assert state.slot(0, pos()).force is None
    after = state.slot(0, destination)
    assert after.force == "the-fifty-men"
    assert after.bond == "stood-fast-with"
    assert after.name == "mara"


def test_mara_can_decline_optional_move_without_losing_hand_inspection(game):
    engine, state = start(game)
    reveal(engine, state)
    decline = next(a for a in engine.legal_actions(state)
                   if isinstance(a, EffectChoice) and a.skip)
    engine.apply(state, decline)
    assert state.slot(0, pos()).named
    assert state.known_hidden_count(0, 1, "the-fifty-men") == 1


def test_mara_still_inspects_hand_when_every_adjacent_legal_destination_is_full(game):
    engine, state = start(game)
    state.slot(0, pos(rank=Rank.FRONT)).force = "the-fifty-men"
    state.slot(0, pos(rank=Rank.REAR)).force = "the-fifty-men"
    state.slot(0, pos(Front.THIRD, Rank.MIDDLE)).force = "the-fifty-men"
    reveal(engine, state)
    assert state.known_hidden_count(0, 1, "the-old-guard") == 1
    assert not [a for a in engine.legal_actions(state) if isinstance(a, EffectChoice)]
    assert state.slot(0, pos()).named
