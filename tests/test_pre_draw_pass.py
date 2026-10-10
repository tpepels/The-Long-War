"""Authoritative paper-rule timing: voluntary Pass before drawing.

This exercises the real Python facade and packed Cython engine rather than
mocking a turn or manually changing the result of the closing sequence.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from longwar.game.actions import BeginTurn, Discard, EndTurn, Pass, action_from_key, action_key
from longwar.game.engine import GameEngine, IllegalAction

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def engine_and_deck():
    engine = GameEngine.from_file(str(ROOT / "cards" / "cards.json"))
    deck = json.loads(
        (ROOT / "decks" / "mobility-open-bonds.json").read_text(encoding="utf8")
    )["cards"]
    return engine, deck


def test_pre_draw_begin_turn_has_roundtrip_action_identity():
    assert action_key(BeginTurn()) == "begin-turn"
    assert action_from_key("begin-turn") == BeginTurn()


def test_voluntary_pass_before_draw_keeps_hand_and_deck(engine_and_deck):
    engine, deck = engine_and_deck
    state = engine.new_game(deck, deck, seed=611, first_player=0)
    assert state.turn_draw_pending
    assert set(engine.legal_actions(state)) == {BeginTurn(), Pass()}
    before_hand = list(state.players[0].hand)
    before_deck = list(state.players[0].deck)
    before_draw_count = state.cards_drawn_this_battle[0]
    engine.apply(state, Pass())
    assert state.players[0].hand == before_hand
    assert state.players[0].deck == before_deck
    assert state.cards_drawn_this_battle[0] == before_draw_count
    assert state.pass_order == [0]
    assert state.closing_turns_remaining == 2
    assert state.active_player == 1
    assert state.turn_draw_pending
    assert engine.legal_actions(state) == [BeginTurn()]


def test_begin_turn_draws_once_and_does_not_consume_an_action(engine_and_deck):
    engine, deck = engine_and_deck
    state = engine.new_game(deck, deck, seed=117, first_player=0)
    before = state.clone()
    engine.apply(state, BeginTurn())
    assert not state.turn_draw_pending
    assert state.cards_drawn_this_battle[0] == before.cards_drawn_this_battle[0] + 1
    assert state.actions_this_turn == 0
    assert state.turn_number == before.turn_number
    assert not engine.transition_completed_turn(before, state, BeginTurn())
    assert not engine.action_consumes_operation(before, 0, BeginTurn())
    with pytest.raises(IllegalAction):
        engine.apply(state, Pass())
    # With a full opening hand the mandatory discard precedes any Action.
    assert all(isinstance(x, Discard) for x in engine.legal_actions(state))
    engine.apply(state, engine.legal_actions(state)[0])
    assert EndTurn() in engine.legal_actions(state)
    assert Pass() not in engine.legal_actions(state)


def test_closing_turns_draw_then_resolve_without_second_pass(engine_and_deck):
    engine, deck = engine_and_deck
    state = engine.new_game(deck, deck, seed=918, first_player=0)
    engine.apply(state, Pass())
    for expected_player, remaining in ((1, 2), (0, 1)):
        assert state.active_player == expected_player
        assert state.closing_turns_remaining == remaining
        assert engine.legal_actions(state) == [BeginTurn()]
        engine.apply(state, BeginTurn())
        if state.pending_draw_discard_for is not None:
            engine.apply(state, engine.legal_actions(state)[0])
        assert EndTurn() in engine.legal_actions(state)
        engine.apply(state, EndTurn())
    assert state.battle >= 2 or state.winner is not None
    if state.winner is None:
        assert state.active_player == 1
        assert state.turn_draw_pending
        assert not state.pass_order
