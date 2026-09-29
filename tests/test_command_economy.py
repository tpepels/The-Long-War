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
from longwar.testing import GameScenario


ROOT = Path(__file__).resolve().parents[1]


def standard_game(*, opening_bonus: bool = False):
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "mobility-open-bonds.json").read_text(encoding="utf-8")
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
    assert rules.command_recovery_floor == 1
    assert rules.command_collapse_threshold == 5
    assert rules.maneuver_command_cost == 1
    assert [player.command for player in state.players] == [20, 20]


def test_unaffordable_card_play_is_not_legal_and_does_not_mutate_state() -> None:
    engine, state = standard_game()
    target = Position(Front.FIRST, Rank.FRONT)
    GameScenario(state).hand(0, "the-fifty-men").command(0, 1)
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
    GameScenario(state).formation(
        0,
        source,
        force="the-fifty-men",
        bond="followed",
        name="namar",
    ).command(0, 0)

    assert Maneuver(source, destination) not in engine.legal_actions(state)


def test_command_never_goes_below_zero() -> None:
    engine, state = standard_game()
    GameScenario(state).command(0, 0).hand(0, "the-fifty-men")

    assert engine.legal_actions(state) == [Pass()]
    engine.apply(state, Pass())
    assert state.players[0].command == 0


def test_printed_card_cost_is_paid_by_operation() -> None:
    engine, state = standard_game()
    target = Position(Front.FIRST, Rank.FRONT)
    GameScenario(state).hand(0, "the-fifty-men").command(0, 7)
    action = PlayForce("the-fifty-men", target)

    assert engine.command_cost_for_action(state, action) == 2
    engine.apply(state, action)

    assert state.players[0].command == 5
    assert state.command_spent_this_battle[0] == 2
    assert state.operations_this_battle[0] == 1


def test_all_current_cards_have_positive_native_safe_command_costs() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    costs = [card["command_cost"] for card in data["cards"]]
    assert costs
    assert all(type(cost) is int and 1 <= cost < 128 for cost in costs)


def test_candidate_recovery_tail_applies_from_battle_eight_onward() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "mobility-open-bonds.json").read_text(encoding="utf-8")
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
    GameScenario(state).battle(8).commands(10, 10).clear_hands().operations(1, 1)

    engine.apply(state, Pass())
    engine.apply(state, Pass())

    assert state.battle == 9
    assert [player.command for player in state.players] == [11, 11]


def test_equal_zero_command_continues_then_recovers_to_floor_one() -> None:
    engine, state = standard_game()
    GameScenario(state).battle(8).commands(0, 0).operations(
        1,
        1,
    ).clear_hands()

    engine.apply(state, Pass())
    engine.apply(state, Pass())

    # Collapse is checked before recovery. Equal low Command continues, then
    # the canonical recovery floor guarantees that 0-0 is not absorbing.
    assert state.phase.value == "battle"
    assert state.winner is None
    assert state.battle == 9
    assert [player.command for player in state.players] == [1, 1]
    snapshot = state.last_battle_snapshot
    assert snapshot is not None
    assert snapshot["command_before_recovery"] == [0, 0]
    assert snapshot["recovery_actual"] == [1, 1]
    assert snapshot["command_remaining"] == [1, 1]


def test_unequal_low_command_collapses_before_recovery() -> None:
    engine, state = standard_game()
    GameScenario(state).battle(1).commands(4, 5).operations(
        1,
        1,
    ).clear_hands()

    engine.apply(state, Pass())
    engine.apply(state, Pass())

    # Battle-I recovery would otherwise rescue both players. It must not be
    # applied because 4-5 already decides Command Collapse.
    assert state.phase.value == "complete"
    assert state.winner == 1
    assert state.battle == 1
    assert [player.command for player in state.players] == [4, 5]
    snapshot = state.last_battle_snapshot
    assert snapshot is not None
    assert snapshot["command_before_recovery"] == [4, 5]
    assert snapshot["recovery_actual"] == [0, 0]
    assert snapshot["command_remaining"] == [4, 5]


def test_canonical_recovery_floor_is_one_after_front_losses() -> None:
    engine, state = standard_game()
    # Battle VIII+ has base recovery 0. Equal low Command survives Collapse,
    # and each player must still recover exactly 1 despite losing a Front.
    GameScenario(state).battle(8).commands(4, 4).battle_start_commands(
        4,
        4,
    ).operations(1, 1).clear_hands().formation(
        1,
        Position(Front.FIRST, Rank.FRONT),
        force="the-fifty-men",
    ).formation(
        0,
        Position(Front.SECOND, Rank.FRONT),
        force="the-fifty-men",
    )

    engine.apply(state, Pass())
    engine.apply(state, Pass())

    assert state.phase.value == "battle"
    assert state.winner is None
    assert state.battle == 9
    assert [player.command for player in state.players] == [5, 5]
    snapshot = state.last_battle_snapshot
    assert snapshot is not None
    assert snapshot["fronts_lost"] == [1, 1]
    assert snapshot["recovery_loss"] == [1, 1]
    assert snapshot["command_before_recovery"] == [4, 4]
    assert snapshot["recovery_actual"] == [1, 1]
    assert snapshot["command_remaining"] == [5, 5]



def test_negative_recovery_floor_is_invalid() -> None:
    with pytest.raises(ValueError):
        GameRules.standard().with_overrides(command_recovery_floor=-1)

