"""Native positional PLAY swaps match the two reviewed printed Force effects."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from longwar.game.actions import BeginTurn, Discard, EffectChoice, PlayForce
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


def start(game, card):
    engine, deck = game
    state = engine.new_game(deck, deck, seed=432, first_player=0)
    engine.apply(state, BeginTurn())
    while state.pending_draw_discard_for is not None:
        engine.apply(state, next(a for a in engine.legal_actions(state) if isinstance(a, Discard)))
    state.players[0].hand[:] = [card]
    state.players[0].command = 20
    return engine, state


def choices(engine, state):
    return [a for a in engine.legal_actions(state) if isinstance(a, EffectChoice)]


def test_ilyri_swaps_full_formation_and_guards_displaced_force(game):
    engine, state = start(game, "the-ilyri")
    front, middle = pos(Rank.FRONT), pos(Rank.MIDDLE)
    original = state.slot(0, front)
    original.force = "the-fifty-men"
    original.bond = "stood-fast-with"
    original.exhausted = True

    engine.apply(state, PlayForce("the-ilyri", middle))
    action = next(a for a in choices(engine, state)
                  if a.destination is not None and a.destination.position == front)
    engine.apply(state, action)

    assert state.slot(0, front).force == "the-ilyri"
    displaced = state.slot(0, middle)
    assert displaced.force == "the-fifty-men"
    assert displaced.bond == "stood-fast-with"
    assert displaced.exhausted
    assert displaced.guarded
    assert not state.slot(0, front).guarded


def test_ilyri_can_decline_optional_swap(game):
    engine, state = start(game, "the-ilyri")
    front, middle = pos(Rank.FRONT), pos(Rank.MIDDLE)
    state.slot(0, front).force = "the-fifty-men"
    engine.apply(state, PlayForce("the-ilyri", middle))
    skip = next(a for a in choices(engine, state) if a.skip)
    engine.apply(state, skip)
    assert state.slot(0, front).force == "the-fifty-men"
    assert state.slot(0, middle).force == "the-ilyri"
    assert not state.slot(0, front).guarded


def test_kings_spears_relieves_eligible_frontline_without_granting_guarded(game):
    engine, state = start(game, "the-kings-spears")
    front, middle = pos(Rank.FRONT), pos(Rank.MIDDLE)
    state.slot(0, front).force = "the-fifty-men"
    engine.apply(state, PlayForce("the-kings-spears", middle))
    action = next(a for a in choices(engine, state)
                  if a.destination is not None and a.destination.position == front)
    engine.apply(state, action)
    assert state.slot(0, front).force == "the-kings-spears"
    assert state.slot(0, middle).force == "the-fifty-men"
    assert not state.slot(0, middle).guarded


def test_kings_spears_cannot_swap_front_only_force_into_middle(game):
    engine, state = start(game, "the-kings-spears")
    front, middle = pos(Rank.FRONT), pos(Rank.MIDDLE)
    state.slot(0, front).force = "the-first-spear"  # printed Frontline-only
    engine.apply(state, PlayForce("the-kings-spears", middle))
    assert not [a for a in choices(engine, state) if not a.skip]
    assert state.slot(0, front).force == "the-first-spear"
    assert state.slot(0, middle).force == "the-kings-spears"


def test_kings_spears_requires_empty_middle_before_play(game):
    engine, state = start(game, "the-kings-spears")
    front, middle = pos(Rank.FRONT), pos(Rank.MIDDLE)
    state.slot(0, front).force = "the-fifty-men"
    state.slot(0, middle).bond = "stood-fast-with"  # prepared Bond, not empty
    action = PlayForce("the-kings-spears", middle)
    assert action in engine.legal_actions(state)
    engine.apply(state, action)
    assert not [a for a in choices(engine, state) if not a.skip]
    assert state.slot(0, front).force == "the-fifty-men"
    assert state.slot(0, middle).force == "the-kings-spears"
