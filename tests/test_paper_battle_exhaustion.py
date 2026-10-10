"""Battle-end Exhaustion and formation-class semantics from the printed rules.

Tests run against the canonical native engine and public Python facade.
The losing player, not the engine, chooses one Force in each lost Front.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from longwar.game.actions import (
    Attack, BeginTurn, Discard, EffectChoice, EndTurn, Pass,
)
from longwar.game.engine import GameEngine
from longwar.game.model import Front, Position, Rank

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def engine():
    return GameEngine.from_file(str(ROOT / "cards" / "cards.json"))


@pytest.fixture(scope="module")
def deck():
    return json.loads(
        (ROOT / "decks" / "mobility-open-bonds.json").read_text()
    )["cards"]


def position(front, rank):
    return Position(Front(front), rank)


def place(state, player, front, rank, card, *, name=None):
    pos = position(front, rank)
    slot = state.slot(player, pos)
    slot.force = card
    slot.name = name
    return pos


def start_action_segment(engine, state):
    engine.apply(state, BeginTurn())
    while state.pending_draw_discard_for is not None:
        discard = next(
            action for action in engine.legal_actions(state)
            if isinstance(action, Discard)
        )
        engine.apply(state, discard)


def finish_battle(engine, state):
    # No Action is needed; Pass at the pre-draw decision.
    assert Pass() in engine.legal_actions(state)
    engine.apply(state, Pass())
    for _ in range(2):
        assert state.turn_draw_pending
        start_action_segment(engine, state)
        engine.apply(state, EndTurn())


def lost_front_choices(engine, state):
    return [
        action for action in engine.legal_actions(state)
        if isinstance(action, EffectChoice)
        and action.effect == "lost-front-exhaust"
        and action.source is not None
    ]


def losing_board(engine, deck):
    state = engine.new_game(deck, deck, seed=81, first_player=0)
    # Player 0 loses only the second Front, retaining two Force choices.
    front = 1
    a = place(state, 0, front, Rank.FRONT, "the-fifty-men")
    b = place(state, 0, front, Rank.MIDDLE, "the-white-hands-of-elara")
    place(state, 1, front, Rank.FRONT, "a-hundred-shields")
    place(state, 1, front, Rank.MIDDLE, "the-iron-boars")
    assert engine.front_strength(state, 0, Front(front)) < engine.front_strength(state, 1, Front(front))
    return state, a, b


def test_player_selects_one_force_from_lost_front(engine, deck):
    state, a, b = losing_board(engine, deck)
    state.slot(0, a).exhausted = True  # A prior Attack Exhaustion must expire.
    finish_battle(engine, state)

    options = lost_front_choices(engine, state)
    assert len(options) == 2, options
    assert {choice.source.position for choice in options} == {a, b}
    assert state.players[0].command == 19  # Penalty and Collapse precede recovery
    assert state.battle == 1

    engine.apply(state, next(choice for choice in options if choice.source.position == b))
    assert state.battle == 2
    assert state.players[0].command == 20  # Recovery after player choice
    assert not state.slot(0, a).exhausted
    assert state.slot(0, b).exhausted


def test_guarded_chosen_force_prevents_loss_exhaustion_without_retarget(engine, deck):
    state, a, b = losing_board(engine, deck)
    state.slot(0, b).guarded = True
    state.slot(0, a).exhausted = True
    finish_battle(engine, state)
    options = lost_front_choices(engine, state)
    assert len(options) == 2
    engine.apply(state, next(choice for choice in options if choice.source.position == b))
    assert state.battle == 2
    assert not state.slot(0, b).exhausted
    assert not state.slot(0, b).guarded
    assert not state.slot(0, a).exhausted


def test_command_collapse_before_selecting_lost_front_exhaustion(engine, deck):
    state, _, _ = losing_board(engine, deck)
    state.players[0].command = 1
    finish_battle(engine, state)
    assert state.winner == 1
    assert not lost_front_choices(engine, state)
    assert state.players[0].command == 0


def test_old_attack_exhaustion_expires_without_lost_front(engine, deck):
    state = engine.new_game(deck, deck, seed=35, first_player=0)
    origin = place(state, 0, 1, Rank.FRONT, "the-fifty-men")
    state.slot(0, origin).exhausted = True
    finish_battle(engine, state)
    assert state.battle == 2
    assert not state.slot(0, origin).exhausted


def test_exhausted_reduces_formation_strength_one(engine, deck):
    state = engine.new_game(deck, deck, seed=44, first_player=0)
    pos = place(state, 0, 1, Rank.MIDDLE, "the-fifty-men")
    before = engine.position_strength(state, 0, pos)
    state.slot(0, pos).exhausted = True
    assert engine.position_strength(state, 0, pos) == max(0, before - 1)


def test_attached_name_grants_raider_attack(engine, deck):
    state = engine.new_game(deck, deck, seed=56, first_player=0)
    origin = place(state, 0, 1, Rank.REAR, "the-fifty-men", name="brannoc")
    target = place(state, 1, 1, Rank.MIDDLE, "the-white-hands-of-elara")
    start_action_segment(engine, state)
    action = Attack(origin, target, "raider")
    assert action in engine.legal_actions(state)


def test_attached_guard_name_screens_friendly_rear(engine, deck):
    state = engine.new_game(deck, deck, seed=57, first_player=0)
    origin = place(state, 0, 1, Rank.REAR, "the-crow-archers")
    target = place(state, 1, 1, Rank.REAR, "the-fifty-men")
    guard = place(state, 1, 1, Rank.MIDDLE, "the-white-hands-of-elara", name="asha-the-shield-bearer")
    start_action_segment(engine, state)
    action = Attack(origin, target, "archer")
    assert action not in engine.legal_actions(state)
    state.slot(1, guard).shaken = True
    assert action in engine.legal_actions(state)
