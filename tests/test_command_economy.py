from __future__ import annotations

import json
from pathlib import Path

import pytest

from longwar.cards import load_card_file
from longwar.game import (
    Front,
    GameEngine,
    Maneuver,
    Pass,
    PlayForce,
    Position,
    Rank,
)
from longwar.game.engine import IllegalAction
from longwar.rules import GameRules


ROOT = Path(__file__).resolve().parents[1]


def standard_game(*, opening_bonus: bool = False):
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "reference.json").read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(data, rules=GameRules.standard())
    state = engine.new_game(
        deck,
        deck,
        seed=26092701,
        first_player=0,
        opening_bonus=opening_bonus,
    )
    return engine, state


def test_standard_command_profile_matches_canonical_rules() -> None:
    engine, state = standard_game()
    rules = engine.rules

    assert rules.starting_command == 20
    assert rules.command_cap == 20
    assert rules.command_recovery_schedule == (10, 7, 5, 4, 3, 2, 1)
    assert rules.command_collapse_threshold == 5
    assert rules.maneuver_command_cost == 1
    assert rules.completion_command_refund == 0
    assert [player.command for player in state.players] == [20, 20]


def test_unaffordable_card_play_is_not_legal_and_does_not_mutate_state() -> None:
    engine, state = standard_game()
    target = Position(Front.FIRST, Rank.FRONT)
    state.players[0].hand = ["the-fifty-men"]
    state.players[0].command = 1
    action = PlayForce("the-fifty-men", target)
    before = state.clone()

    assert action not in engine.legal_actions(state)
    with pytest.raises(IllegalAction):
        engine.apply(state, action)

    assert state == before


def test_unaffordable_maneuver_is_not_legal() -> None:
    engine, state = standard_game()
    source = Position(Front.FIRST, Rank.FRONT)
    destination = Position(Front.SECOND, Rank.FRONT)
    slot = state.slot(0, source)
    slot.force = "the-fifty-men"
    slot.bond = "followed"
    slot.name = "namar"
    state.players[0].command = 0

    assert Maneuver(source, destination) not in engine.legal_actions(state)


def test_command_never_goes_below_zero() -> None:
    engine, state = standard_game()
    state.players[0].command = 0
    state.players[0].hand = ["the-fifty-men"]

    assert engine.legal_actions(state) == [Pass()]
    engine.apply(state, Pass())
    assert state.players[0].command == 0


def test_printed_card_cost_is_paid_by_operation() -> None:
    engine, state = standard_game()
    target = Position(Front.FIRST, Rank.FRONT)
    state.players[0].hand = ["the-fifty-men"]
    state.players[0].command = 7
    action = PlayForce("the-fifty-men", target)

    assert engine.command_cost_for_action(state, action) == 2
    engine.apply(state, action)

    assert state.players[0].command == 5
    assert state.command_spent_this_battle[0] == 2
    assert state.operations_this_battle[0] == 1


def test_all_current_cards_have_small_printed_command_costs() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    costs = [card["command_cost"] for card in data["cards"]]
    assert all(cost in {1, 2, 3} for cost in costs)
    assert set(costs) == {1, 2, 3}


def test_candidate_recovery_tail_applies_from_battle_eight_onward() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "reference.json").read_text(encoding="utf-8")
    )["cards"]
    rules = GameRules.standard().with_overrides(
        command_recovery_schedule=(10, 8, 6, 5, 4, 3, 2),
        command_recovery_tail=1,
    )
    engine = GameEngine(data, rules=rules)
    state = engine.new_game(
        deck,
        deck,
        seed=26092801,
        first_player=0,
        opening_bonus=False,
    )
    state.battle = 8
    state.players[0].command = 10
    state.players[1].command = 10
    state.operations_this_battle[:] = [1, 1]

    engine.apply(state, Pass())
    engine.apply(state, Pass())

    assert state.battle == 9
    assert [player.command for player in state.players] == [11, 11]


def test_equal_low_command_remains_an_explicit_canonical_ambiguity() -> None:
    engine, state = standard_game()
    state.battle = 8
    state.players[0].command = 0
    state.players[1].command = 0
    state.operations_this_battle[:] = [1, 1]
    state.players[0].hand.clear()
    state.players[1].hand.clear()

    engine.apply(state, Pass())
    engine.apply(state, Pass())

    # Current rulebook: lower Command loses, equal Command continues.
    # This deliberately documents the unresolved 0-0 loop instead of
    # inventing a winner in engine code.
    assert state.phase.value == "battle"
    assert state.winner is None
    assert state.battle == 9
    assert [player.command for player in state.players] == [0, 0]
