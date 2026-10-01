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
    PlayBond,
    PlayForce,
    PlayName,
    Position,
    Rank,
)
from longwar.game.engine import IllegalAction
from longwar.rules import GameRules
from longwar.heuristics import command_preserving_actions
from longwar.testing import GameScenario


ROOT = Path(__file__).resolve().parents[1]


def standard_game(
    *,
    opening_bonus: bool = False,
    rules: GameRules | None = None,
):
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "mobility-open-bonds.json").read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(data, rules=rules or GameRules.standard())
    state = engine.new_game(
        deck,
        deck,
        seed=26092701,
        first_player=0,
        opening_bonus=opening_bonus,
    )
    return engine, state


def test_standard_command_profile_propagates_into_engine_and_state() -> None:
    engine, state = standard_game()
    rules = GameRules.standard()

    assert engine.rules == rules
    assert engine.starting_command == rules.starting_command
    assert engine.command_cap == rules.command_cap
    assert engine.command_recovery_start == rules.command_recovery_start
    assert engine.command_recovery_decrement == rules.command_recovery_decrement
    assert engine.command_recovery_floor == rules.command_recovery_floor
    assert engine.command_collapse_threshold == rules.command_collapse_threshold
    assert engine.maneuver_command_cost == rules.maneuver_command_cost
    assert [player.command for player in state.players] == [
        rules.starting_command,
        rules.starting_command,
    ]


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
    rules = GameRules.standard().with_overrides(maneuver_command_cost=1)
    engine, state = standard_game(rules=rules)
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



def test_catchup_zero_cost_cannot_stack_into_negative_command_cost() -> None:
    engine, state = standard_game()
    front = Position(Front.FIRST, Rank.FRONT)
    rear = Position(Front.FIRST, Rank.REAR)
    GameScenario(state).formation(
        0,
        rear,
        force="the-fifty-men",
        bond="followed",
        name="iven",
    ).formation(
        0,
        front,
        force="the-fifty-men",
    ).commands(1, 5).hand(0, "rallied-behind")

    action = PlayBond("rallied-behind", front)

    # Rallied Behind becomes free while behind. Iven can also discount the
    # first card in this Front, but discounts may never push a cost below 0.
    assert engine.command_cost_for_action(state, action) == 0
    engine.apply(state, action)
    assert state.players[0].command == 1
    assert state.command_spent_this_battle[0] == 0

def test_arithmetic_recovery_formula_can_be_overridden() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    rules = GameRules.standard().with_overrides(
        command_recovery_start=10,
        command_recovery_decrement=2,
    )
    engine = GameEngine(data, rules=rules)

    assert [
        engine.command_recovery_for_battle(battle)
        for battle in range(1, 9)
    ] == [10, 8, 6, 4, 2, 0, 0, 0]


def test_equal_threshold_command_is_a_draw_without_recovery() -> None:
    rules = GameRules.standard().with_overrides(
        command_collapse_threshold=0,
        command_recovery_start=0,
        command_recovery_decrement=0,
        command_recovery_floor=1,
    )
    engine, state = standard_game(rules=rules)
    GameScenario(state).battle(1).commands(0, 0).operations(
        1,
        1,
    ).clear_hands()

    engine.apply(state, Pass())
    engine.apply(state, Pass())

    assert state.phase.value == "complete"
    assert state.winner is None
    assert state.battle == 1
    assert [player.command for player in state.players] == [0, 0]
    snapshot = state.last_battle_snapshot
    assert snapshot is not None
    assert snapshot["command_before_recovery"] == [0, 0]
    assert snapshot["recovery_actual"] == [0, 0]
    assert snapshot["command_remaining"] == [0, 0]


def test_threshold_vs_positive_command_collapses_before_recovery() -> None:
    rules = GameRules.standard().with_overrides(
        command_collapse_threshold=0,
        command_recovery_start=12,
        command_recovery_decrement=3,
    )
    engine, state = standard_game(rules=rules)
    GameScenario(state).battle(1).commands(0, 5).operations(
        1,
        1,
    ).clear_hands()

    engine.apply(state, Pass())
    engine.apply(state, Pass())

    # Battle-I recovery would otherwise rescue the exhausted player. It must
    # not be applied because 0-vs-positive already decides Command Collapse.
    assert state.phase.value == "complete"
    assert state.winner == 1
    assert state.battle == 1
    assert [player.command for player in state.players] == [0, 5]
    snapshot = state.last_battle_snapshot
    assert snapshot is not None
    assert snapshot["command_before_recovery"] == [0, 5]
    assert snapshot["recovery_actual"] == [0, 0]
    assert snapshot["command_remaining"] == [0, 5]


def test_front_losses_reduce_command_before_recovery_floor_applies() -> None:
    rules = GameRules.standard().with_overrides(
        command_recovery_start=0,
        command_recovery_decrement=0,
        command_recovery_floor=1,
        command_collapse_threshold=0,
    )
    engine, state = standard_game(rules=rules)
    # Each lost Front removes 1 current Command before Collapse. Base recovery
    # is 0, so surviving players then recover only the configured floor.
    GameScenario(state).battle(1).commands(4, 4).battle_start_commands(
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
    assert state.battle == 2
    assert [player.command for player in state.players] == [4, 4]
    snapshot = state.last_battle_snapshot
    assert snapshot is not None
    assert snapshot["fronts_lost"] == [1, 1]
    assert snapshot["recovery_loss"] == [1, 1]
    assert snapshot["command_before_recovery"] == [3, 3]
    assert snapshot["recovery_actual"] == [1, 1]
    assert snapshot["command_remaining"] == [4, 4]



def test_command_guard_filters_avoidable_final_command_spend() -> None:
    rules = GameRules.standard().with_overrides(
        command_collapse_threshold=0,
        maneuver_command_cost=1,
    )
    engine, state = standard_game(rules=rules)
    source = Position(Front.FIRST, Rank.FRONT)
    destination = Position(Front.SECOND, Rank.FRONT)
    GameScenario(state).formation(
        0,
        source,
        force="the-fifty-men",
        bond="followed",
        name="namar",
    ).commands(1, 5).operations(1, 1).clear_hands()

    maneuver = Maneuver(source, destination)
    legal = engine.legal_actions(state)
    preserving, filtered = command_preserving_actions(engine, state, legal)

    assert Pass() in legal
    assert maneuver in legal
    assert Pass() in preserving
    assert maneuver not in preserving
    assert filtered >= 1


def test_command_guard_keeps_immediate_command_refund_action() -> None:
    rules = GameRules.standard().with_overrides(
        command_collapse_threshold=0,
        maneuver_command_cost=1,
    )
    engine, state = standard_game(rules=rules)
    target = Position(Front.FIRST, Rank.FRONT)
    GameScenario(state).formation(
        0,
        target,
        force="the-fifty-men",
        bond="followed",
    ).commands(1, 5).operations(1, 1).clear_hands().hand(0, "namar")

    play_name = PlayName("namar", target)
    preserving, _filtered = command_preserving_actions(
        engine,
        state,
        engine.legal_actions(state),
    )

    assert play_name in preserving
    child = state.clone()
    engine.apply(child, play_name)
    assert child.players[0].command == 1


def test_pass_is_valued_over_spending_the_final_command() -> None:
    rules = GameRules.standard().with_overrides(
        command_collapse_threshold=0,
        maneuver_command_cost=1,
    )
    engine, state = standard_game(rules=rules)
    source = Position(Front.FIRST, Rank.FRONT)
    destination = Position(Front.SECOND, Rank.FRONT)
    GameScenario(state).formation(
        0,
        source,
        force="the-fifty-men",
        bond="followed",
        name="namar",
    ).commands(1, 5).operations(1, 1)

    pass_score = engine._native_heuristic().score_action(
        engine._native_core().from_game_state(state),
        0,
        engine._native_action(
            engine._native_core().from_game_state(state),
            Pass(),
        ),
    )
    maneuver = Maneuver(source, destination)
    packed = engine._native_core().from_game_state(state)
    maneuver_score = engine._native_heuristic().score_action(
        packed,
        0,
        engine._native_action(packed, maneuver),
    )

    assert Pass() in engine.legal_actions(state)
    assert maneuver in engine.legal_actions(state)
    assert pass_score > maneuver_score


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("command_recovery_start", -1),
        ("command_recovery_decrement", -1),
        ("command_recovery_floor", -1),
    ],
)
def test_negative_recovery_settings_are_invalid(field: str, value: int) -> None:
    with pytest.raises(ValueError):
        GameRules.standard().with_overrides(**{field: value})



def test_command_diagnostics_attribute_completion_gain_to_source_card() -> None:
    engine, state = standard_game()
    target = Position(Front.FIRST, Rank.FRONT)
    GameScenario(state).formation(
        0,
        target,
        force="the-fifty-men",
        bond="followed",
    ).commands(1, 5).hand(0, "namar")

    action = PlayName("namar", target)
    engine.apply(state, action)

    events = engine.last_command_diagnostics()
    assert any(
        event["kind"] == "gain"
        and event["detail"] == "completion_gain"
        and event["source_card"] == "namar"
        and event["amount"] == 1
        for event in events
    )


def test_command_diagnostics_attribute_catchup_discount_to_source_card() -> None:
    engine, state = standard_game()
    target = Position(Front.FIRST, Rank.FRONT)
    GameScenario(state).formation(
        0, target, force="the-fifty-men"
    ).commands(1, 5).hand(0, "rallied-behind")

    action = PlayBond("rallied-behind", target)
    engine.apply(state, action)

    events = engine.last_command_diagnostics()
    assert any(
        event["kind"] == "discount"
        and event["detail"] == "catchup_discount"
        and event["source_card"] == "rallied-behind"
        and event["amount"] >= 1
        for event in events
    )


def test_front_loss_can_cause_collapse_before_recovery() -> None:
    rules = GameRules.standard().with_overrides(
        command_recovery_start=12,
        command_recovery_decrement=3,
        command_recovery_floor=1,
        command_collapse_threshold=0,
    )
    engine, state = standard_game(rules=rules)
    GameScenario(state).battle(1).commands(1, 5).battle_start_commands(
        1,
        5,
    ).operations(1, 1).clear_hands().formation(
        1,
        Position(Front.FIRST, Rank.FRONT),
        force="the-fifty-men",
    )

    engine.apply(state, Pass())
    engine.apply(state, Pass())

    assert state.phase.value == "complete"
    assert state.winner == 1
    snapshot = state.last_battle_snapshot
    assert snapshot is not None
    assert snapshot["fronts_lost"][0] == 1
    assert snapshot["command_before_recovery"] == [0, 5]
    assert snapshot["recovery_actual"] == [0, 0]
