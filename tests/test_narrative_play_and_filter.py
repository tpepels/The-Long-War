"""Printed draw-before-discard, face-up Narrative PLAY, Rider and Archer effects."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from longwar.game.actions import (
    BeginTurn, Discard, EffectChoice, PlayBond, PlayNarrative, PlayOrder,
)
from longwar.game.engine import GameEngine
from longwar.game.model import Front, Position, Rank

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def game():
    engine = GameEngine.from_file(str(ROOT / "cards" / "cards.json"))
    deck = json.loads((ROOT / "decks" / "mobility-open-bonds.json").read_text())["cards"]
    return engine, deck


def at(front, rank):
    return Position(Front(front), rank)


def own_turn(game, card):
    engine, deck = game
    state = engine.new_game(deck, deck, seed=127, first_player=0)
    engine.apply(state, BeginTurn())
    while state.pending_draw_discard_for is not None:
        engine.apply(state, next(a for a in engine.legal_actions(state)
                                 if isinstance(a, Discard)))
    state.players[0].hand[:] = [card]
    state.players[0].command = 20
    return engine, state


def pending_targets(engine, state):
    return [a for a in engine.legal_actions(state) if isinstance(a, EffectChoice)]


def test_bond_kept_pace_draws_then_player_chooses_discard(game):
    engine, state = own_turn(game, "kept-pace-with")
    state.slot(0, at(1, Rank.FRONT)).force = "the-grey-riders"
    # The qualifying Rider belongs to this Front, not the new Bond's slot.
    deck_before = len(state.players[0].deck)
    action = PlayBond("kept-pace-with", at(1, Rank.REAR))
    assert action in engine.legal_actions(state)
    engine.apply(state, action)
    options = pending_targets(engine, state)
    assert options
    assert len(state.players[0].deck) == deck_before - 1
    assert len(state.players[0].hand) == 1  # draw completed before discard
    engine.apply(state, next(a for a in options if a.card_id is not None))
    assert len(state.players[0].hand) == 0


def test_kept_pace_has_no_draw_without_rider_or_scout_here(game):
    engine, state = own_turn(game, "kept-pace-with")
    state.slot(0, at(1, Rank.FRONT)).force = "the-fifty-men"
    deck_before = len(state.players[0].deck)
    engine.apply(state, PlayBond("kept-pace-with", at(1, Rank.REAR)))
    assert not pending_targets(engine, state)
    assert len(state.players[0].deck) == deck_before


def test_send_a_runner_order_draws_two_before_discard(game):
    engine, state = own_turn(game, "send-a-runner")
    state.slot(0, at(1, Rank.REAR)).force = "the-lantern-scouts"
    deck_before = len(state.players[0].deck)
    options = [a for a in engine.legal_actions(state)
               if isinstance(a, PlayOrder) and a.card_id == "send-a-runner"]
    assert options
    engine.apply(state, options[0])
    assert len(state.players[0].deck) == deck_before - 2
    assert len(state.players[0].hand) == 2
    choices = pending_targets(engine, state)
    assert choices
    engine.apply(state, next(a for a in choices if a.card_id is not None))
    assert len(state.players[0].hand) == 1


def test_crows_narrative_play_can_exhaust_enemy_in_archer_front(game):
    engine, state = own_turn(game, "the-crows-came-down")
    enemy = at(1, Rank.REAR)
    state.slot(0, at(1, Rank.MIDDLE)).force = "the-crow-archers"
    state.slot(1, enemy).force = "the-fifty-men"
    action = PlayNarrative("the-crows-came-down")
    assert action in engine.legal_actions(state)
    engine.apply(state, action)
    choices = [a for a in pending_targets(engine, state)
               if a.destination is not None and a.destination.position == enemy]
    assert choices
    engine.apply(state, choices[0])
    assert state.slot(1, enemy).exhausted
    assert state.narratives[0][0].card_id == "the-crows-came-down"


def test_long_march_play_grants_rider_strength_this_battle(game):
    engine, state = own_turn(game, "the-long-march")
    rider = at(1, Rank.FRONT)
    other = at(1, Rank.MIDDLE)
    state.slot(0, rider).force = "the-grey-riders"
    state.slot(0, other).force = "the-fifty-men"
    before = engine.position_strength(state, 0, rider)
    other_before = engine.position_strength(state, 0, other)
    action = PlayNarrative("the-long-march")
    assert action in engine.legal_actions(state)
    engine.apply(state, action)
    choices = pending_targets(engine, state)
    chosen = [a for a in choices if a.source is not None
              and a.source.position == rider
              and a.destination is None]
    assert chosen, choices
    engine.apply(state, chosen[0])
    assert engine.position_strength(state, 0, rider) == before + 1
    assert engine.position_strength(state, 0, other) == other_before
