"""Printed No Road Was Too Long: immediate, rank-for-rank Front exchange."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from longwar.game.actions import (
    ActivateAbility, BeginTurn, Discard, EffectChoice, PlayNarrative,
)
from longwar.game.engine import GameEngine
from longwar.game.model import Front, Position, Rank

ROOT = Path(__file__).resolve().parents[1]
A, B = Front.SECOND, Front.THIRD


@pytest.fixture(scope="module")
def game():
    engine = GameEngine.from_file(str(ROOT / "cards" / "cards.json"))
    deck = json.loads((ROOT / "decks" / "mobility-open-bonds.json").read_text())["cards"]
    return engine, deck


def setup(game):
    engine, deck = game
    state = engine.new_game(deck, deck, seed=307, first_player=0)
    state.players[0].command = 20
    engine.apply(state, BeginTurn())
    while state.pending_draw_discard_for is not None:
        engine.apply(state, next(
            action for action in engine.legal_actions(state)
            if isinstance(action, Discard)
        ))
    state.players[0].hand[:] = ["no-road-was-too-long"]
    return engine, state


def pos(front, rank=Rank.MIDDLE):
    return Position(front, rank)


def play(engine, state):
    matches = [
        a for a in engine.legal_actions(state)
        if isinstance(a, PlayNarrative) and a.card_id == "no-road-was-too-long"
    ]
    assert matches
    engine.apply(state, matches[0])


def choices(engine, state, kind="v2-target"):
    return [
        a for a in engine.legal_actions(state)
        if isinstance(a, EffectChoice) and a.effect == kind
    ]


def exchange(engine, state, left=A, right=B):
    action = next(
        a for a in choices(engine, state)
        if a.source is not None and a.destination is not None
        and a.source.position == pos(left, Rank.FRONT)
        and a.destination.position == pos(right, Rank.FRONT)
    )
    engine.apply(state, action)


def test_play_exchanges_whole_stacks_and_awards_one_named_bonus(game):
    engine, state = setup(game)
    named = state.slot(0, pos(A))
    named.force = "the-lantern-scouts"
    named.bond = "carried-the-oath-of"
    named.name = "oren"
    named.temporary_strength = 1
    named.exhausted = True
    named.guarded = True
    other = state.slot(0, pos(B))
    other.force = "the-crow-archers"
    other.shaken = True
    play(engine, state)
    assert choices(engine, state)
    assert not [
        a for a in engine.legal_actions(state)
        if isinstance(a, ActivateAbility) and a.card_id == "no-road-was-too-long"
    ]
    exchange(engine, state)
    new_named = state.slot(0, pos(B))
    new_other = state.slot(0, pos(A))
    assert (new_named.force, new_named.bond, new_named.name) == (
        "the-lantern-scouts", "carried-the-oath-of", "oren"
    )
    assert new_named.exhausted and new_named.guarded
    assert new_named.temporary_strength == 1
    assert new_other.force == "the-crow-archers" and new_other.shaken
    bonus = choices(engine, state, "swapped-named-strength")
    assert len(bonus) == 1
    assert bonus[0].source.position == pos(B)
    engine.apply(state, bonus[0])
    assert state.slot(0, pos(B)).temporary_strength == 3
    assert state.operations_this_battle[0] == 1


def test_two_moved_named_formations_require_exactly_one_bonus(game):
    engine, state = setup(game)
    for front, force in ((A, "the-crow-archers"), (B, "the-iron-boars")):
        unit = state.slot(0, pos(front))
        unit.force = force
        unit.bond = "carried-the-oath-of"
        unit.name = "oren"
    play(engine, state)
    exchange(engine, state)
    bonus = choices(engine, state, "swapped-named-strength")
    assert len(bonus) == 2
    assert not any(action.skip for action in bonus)
    target = next(a for a in bonus if a.source.position == pos(A))
    engine.apply(state, target)
    assert state.slot(0, pos(A)).temporary_strength == 2
    assert state.slot(0, pos(B)).temporary_strength == 0


def test_prepared_components_follow_ranks_without_named_bonus(game):
    engine, state = setup(game)
    state.slot(0, pos(A, Rank.REAR)).bond = "carried-the-oath-of"
    state.slot(0, pos(B, Rank.FRONT)).force = "the-first-spear"
    play(engine, state)
    exchange(engine, state)
    assert state.slot(0, pos(B, Rank.REAR)).bond == "carried-the-oath-of"
    assert state.slot(0, pos(A, Rank.FRONT)).force == "the-first-spear"
    assert not choices(engine, state, "swapped-named-strength")
    assert state.operations_this_battle[0] == 1


def test_no_inactive_front_exchange_can_be_selected(game):
    engine, state = setup(game)
    state.slot(0, pos(A)).force = "the-crow-archers"
    play(engine, state)
    exchanges = choices(engine, state)
    assert len(exchanges) == 1
    assert exchanges[0].source.position == pos(A, Rank.FRONT)
    assert exchanges[0].destination.position == pos(B, Rank.FRONT)


def test_no_exchange_prompt_when_all_active_fronts_empty(game):
    engine, state = setup(game)
    play(engine, state)
    assert not choices(engine, state)
    assert state.operations_this_battle[0] == 1
