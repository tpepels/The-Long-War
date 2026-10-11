"""Printed simultaneous resolution Stratagems use one shared eligibility snapshot.

Both players privately commit reveal or decline. No Strength changes until
both decisions are made. These tests use the real native engine and facade.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from longwar.game.actions import BeginTurn, Discard, EffectChoice, EndTurn, Pass
from longwar.game.engine import GameEngine
from longwar.game.model import Front, Position, Rank, StratagemState

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def game():
    engine = GameEngine.from_file(str(ROOT / "cards" / "cards.json"))
    deck = json.loads((ROOT / "decks" / "mobility-open-bonds.json").read_text())["cards"]
    return engine, deck


def at(rank, front=Front.FIRST):
    return Position(front, rank)


def end_battle(engine, state):
    assert Pass() in engine.legal_actions(state)
    engine.apply(state, Pass())
    for _ in range(2):
        engine.apply(state, BeginTurn())
        while state.pending_draw_discard_for is not None:
            engine.apply(state, next(a for a in engine.legal_actions(state)
                                     if isinstance(a, Discard)))
        engine.apply(state, EndTurn())


def setup(game):
    engine, deck = game
    state = engine.new_game(deck, deck, seed=106, first_player=0)
    state.battle = 2  # left outer Front is active in Battle II
    state.slot(0, at(Rank.FRONT)).force = "the-late-banner"  # Captain
    state.slot(0, at(Rank.MIDDLE)).force = "the-fifty-men"
    state.slot(0, at(Rank.REAR)).force = "the-fifty-men"
    state.slot(1, at(Rank.FRONT)).force = "the-red-shields"  # Guard
    state.stratagems[0] = StratagemState(
        "the-center-must-hold", fronts=(Front.FIRST,),
    )
    state.stratagems[1] = StratagemState(
        "the-flank-was-refused", fronts=(Front.FIRST,),
    )
    end_battle(engine, state)
    return engine, state


def choices(engine, state, effect):
    return [a for a in engine.legal_actions(state)
            if isinstance(a, EffectChoice) and a.effect == effect]


def choose(engine, state, effect, *, reveal):
    opts = choices(engine, state, effect)
    assert opts, (effect, engine.legal_actions(state))
    action = next(a for a in opts if a.skip != reveal)
    engine.apply(state, action)


def information_key(engine, state, player):
    native = engine._native_core_instance
    return native.information_key(native.from_game_state(state), player)


def test_private_reveal_commitment_is_not_visible_to_other_player(game):
    engine, state = setup(game)
    assert state.active_player == 0
    assert len(choices(engine, state, "stratagem-reveal")) == 2
    reveal_state = state.clone()
    decline_state = state.clone()
    choose(engine, reveal_state, "stratagem-reveal", reveal=True)
    choose(engine, decline_state, "stratagem-reveal", reveal=False)

    assert not reveal_state.stratagems[0].revealed
    assert not decline_state.stratagems[0].revealed
    assert reveal_state.active_player == decline_state.active_player == 1
    assert information_key(engine, reveal_state, 1) == information_key(engine, decline_state, 1)
    assert information_key(engine, reveal_state, 0) != information_key(engine, decline_state, 0)


def test_both_commit_before_either_reveals_and_choose_independent_targets(game):
    engine, state = setup(game)
    middle, rear, guard = at(Rank.MIDDLE), at(Rank.REAR), at(Rank.FRONT)
    initial0 = [state.slot(0, middle).temporary_strength,
                state.slot(0, rear).temporary_strength]
    initial1 = state.slot(1, guard).temporary_strength
    choose(engine, state, "stratagem-reveal", reveal=True)
    assert not state.stratagems[0].revealed
    assert not state.stratagems[1].revealed
    assert [state.slot(0, middle).temporary_strength,
            state.slot(0, rear).temporary_strength] == initial0

    choose(engine, state, "stratagem-reveal", reveal=True)
    assert state.stratagems[0].revealed and state.stratagems[1].revealed

    buff0 = choices(engine, state, "stratagem-buff")
    pair = next(a for a in buff0 if a.source is not None
                and a.destination is not None)
    engine.apply(state, pair)
    assert state.slot(0, middle).temporary_strength == initial0[0] + 1
    assert state.slot(0, rear).temporary_strength == initial0[1] + 1
    assert state.slot(1, guard).temporary_strength == initial1

    buff1 = choices(engine, state, "stratagem-buff")
    assert len(buff1) == 1
    engine.apply(state, buff1[0])
    # The combined Front result can still require a player to choose
    # which defeated Force receives next-Battle Exhaustion before recovery.
    while True:
        exhaust = choices(engine, state, "lost-front-exhaust")
        if not exhaust:
            break
        engine.apply(state, exhaust[0])
    assert state.battle >= 3 or state.winner is not None
    assert state.stratagems[0] is None and state.stratagems[1] is None


def test_declining_one_reveal_does_not_block_the_other(game):
    engine, state = setup(game)
    choose(engine, state, "stratagem-reveal", reveal=False)
    choose(engine, state, "stratagem-reveal", reveal=True)
    assert not state.stratagems[0].revealed
    assert state.stratagems[1].revealed
    assert len(choices(engine, state, "stratagem-buff")) == 1


def test_outer_only_reveal_ineligible_in_middle_front(game):
    engine, deck = game
    state = engine.new_game(deck, deck, seed=14, first_player=0)
    state.slot(0, at(Rank.FRONT, Front.SECOND)).force = "the-red-shields"
    state.stratagems[0] = StratagemState(
        "the-flank-was-refused", fronts=(Front.SECOND,),
    )
    end_battle(engine, state)
    # Present a forced private decline for ineligible hidden cards rather
    # than disclosing their eligibility through missing pending-player turns.
    options = choices(engine, state, "stratagem-reveal")
    assert len(options) == 1 and options[0].skip
    engine.apply(state, options[0])
    assert state.stratagems[0] is None
