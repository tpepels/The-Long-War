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
from longwar.game.model import StratagemState
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
    assert engine.lost_front_command_penalty == rules.lost_front_command_penalty
    assert rules.pass_signal_costs_operation is True
    assert rules.pass_closing_rounds == 0
    assert engine.rules.pass_signal_costs_operation is True
    assert engine.rules.pass_closing_rounds == 0
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


def test_equal_threshold_command_first_passer_loses_without_recovery() -> None:
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
    assert state.winner == 1
    assert state.battle == 1
    assert [player.command for player in state.players] == [0, 0]
    snapshot = state.last_battle_snapshot
    assert snapshot is not None
    assert snapshot["command_before_collapse"] == [0, 0]
    assert snapshot["recovery_actual"] == [0, 0]
    assert snapshot["command_remaining"] == [0, 0]


def test_front_loss_command_overrun_is_not_clamped_before_collapse() -> None:
    rules = GameRules.standard().with_overrides(
        lost_front_command_penalty=2,
        command_collapse_threshold=0,
        command_recovery_start=12,
        command_recovery_decrement=3,
    )
    engine, state = standard_game(rules=rules)
    GameScenario(state).battle(1).commands(1, 0).battle_start_commands(
        1,
        0,
    ).operations(1, 1).clear_hands().formation(
        1,
        Position(Front.FIRST, Rank.FRONT),
        force="the-fifty-men",
    )

    engine.apply(state, Pass())
    engine.apply(state, Pass())

    assert state.phase.value == "complete"
    assert state.winner == 1
    assert [player.command for player in state.players] == [-1, 0]
    snapshot = state.last_battle_snapshot
    assert snapshot is not None
    assert snapshot["fronts_lost"] == [1, 0]
    assert snapshot["front_loss_command_penalty"] == [2, 0]
    assert snapshot["command_before_collapse"] == [-1, 0]
    assert snapshot["recovery_actual"] == [0, 0]
    assert snapshot["command_remaining"] == [-1, 0]


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
    assert snapshot["command_before_collapse"] == [0, 5]
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
    assert snapshot["front_loss_command_penalty"] == [1, 1]
    assert snapshot["command_before_collapse"] == [3, 3]
    assert snapshot["recovery_actual"] == [1, 1]
    assert snapshot["command_remaining"] == [4, 4]



def test_lost_front_command_penalty_is_configurable() -> None:
    rules = GameRules.standard().with_overrides(
        lost_front_command_penalty=2,
        command_recovery_start=0,
        command_recovery_decrement=0,
        command_recovery_floor=1,
        command_collapse_threshold=0,
    )
    engine, state = standard_game(rules=rules)
    GameScenario(state).battle(1).commands(5, 5).battle_start_commands(
        5,
        5,
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

    snapshot = state.last_battle_snapshot
    assert snapshot is not None
    assert snapshot["fronts_lost"] == [1, 1]
    assert snapshot["front_loss_command_penalty"] == [2, 2]
    assert snapshot["command_before_collapse"] == [3, 3]
    assert snapshot["recovery_actual"] == [1, 1]
    assert [player.command for player in state.players] == [4, 4]


def test_command_guard_keeps_zero_command_midbattle_actions() -> None:
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

    assert maneuver in legal
    assert maneuver in preserving
    assert filtered == 0

    packed = engine._native_core().from_game_state(state)
    native_maneuver = engine._native_action(packed, maneuver)
    native_preserving, native_filtered = (
        engine._native_heuristic().command_preserving_action_codes(packed)
    )
    assert native_maneuver in native_preserving
    assert native_filtered == 0


def test_rollout_guard_preserves_last_command_without_restricting_root() -> None:
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

    packed = engine._native_core().from_game_state(state)
    maneuver = engine._native_action(
        packed,
        Maneuver(source, destination),
    )

    root_safe, root_filtered = (
        engine._native_heuristic().command_preserving_action_codes(packed)
    )
    rollout_safe, rollout_filtered = (
        engine._native_heuristic().rollout_preserving_action_codes(packed)
    )

    assert maneuver in root_safe
    assert root_filtered == 0
    assert maneuver not in rollout_safe
    assert rollout_filtered >= 1


def test_post_signal_evaluation_does_not_discount_immediate_closing_option() -> None:
    rules = GameRules.standard().with_overrides(pass_closing_rounds=3)
    engine, state = standard_game(rules=rules)
    state.players[0].passed = True
    state.pass_order[:] = [0]

    state.pass_closing_turns_remaining = 6
    early = engine._native_heuristic().evaluate(
        engine._native_core().from_game_state(state),
        0,
    )

    state.pass_closing_turns_remaining = 1
    late = engine._native_heuristic().evaluate(
        engine._native_core().from_game_state(state),
        0,
    )

    # The unsignalled opponent may end the Battle immediately by signalling
    # in either state. The automatic deadline must not discount that leverage.
    assert early == pytest.approx(late)


def test_projected_lost_masks_use_tie_control_resolution_rule() -> None:
    engine, state = standard_game()
    first = Position(Front.FIRST, Rank.FRONT)
    rear = Position(Front.FIRST, Rank.REAR)
    GameScenario(state).formation(
        0, first, force="the-fifty-men", bond="followed", name="namar"
    ).formation(
        1, rear, force="the-fifty-men", bond="followed", name="namar"
    )
    state.stratagems[0] = StratagemState("the-ground-was-held")

    packed = engine._native_core().from_game_state(state)
    lost0, lost1 = engine._native_heuristic().projected_lost_masks(packed)

    assert not (lost0 & (1 << int(Front.FIRST)))
    assert lost1 & (1 << int(Front.FIRST))


def test_projected_lost_masks_use_combined_front_resolution_rule() -> None:
    engine, state = standard_game()
    first = Position(Front.FIRST, Rank.FRONT)
    second = Position(Front.SECOND, Rank.FRONT)
    GameScenario(state).formation(
        0, first, force="the-fifty-men"
    ).formation(
        1, second, force="the-fifty-men"
    )
    state.slot(0, first).temporary_strength = 2
    state.stratagems[0] = StratagemState(
        "the-center-must-hold",
        fronts=(Front.FIRST, Front.SECOND),
    )

    packed = engine._native_core().from_game_state(state)
    lost0, lost1 = engine._native_heuristic().projected_lost_masks(packed)
    pair = (1 << int(Front.FIRST)) | (1 << int(Front.SECOND))

    assert lost0 & pair == 0
    assert lost1 & pair == pair


def test_projected_lost_masks_use_frontline_only_resolution_strength() -> None:
    engine, state = standard_game()
    front = Position(Front.FIRST, Rank.FRONT)
    rear = Position(Front.FIRST, Rank.REAR)
    GameScenario(state).formation(
        0, front, force="the-red-duelists"
    ).formation(
        0, rear, force="seven-black-ships"
    ).formation(
        1, front, force="the-fifty-men"
    ).formation(
        1, rear, force="seven-black-ships"
    )

    packed = engine._native_core().from_game_state(state)
    lost0, lost1 = engine._native_heuristic().projected_lost_masks(packed)

    assert lost0 & (1 << int(Front.FIRST))
    assert not (lost1 & (1 << int(Front.FIRST)))


def test_immediate_completion_value_requires_affordable_name() -> None:
    engine, state = standard_game()
    target = Position(Front.FIRST, Rank.FRONT)
    GameScenario(state).clear_hands().hand(0, "oren").formation(
        0,
        target,
        force="the-fifty-men",
    ).command(0, 1)

    packed = engine._native_core().from_game_state(state)
    assert engine._native_heuristic().immediate_completion_value(
        packed,
        0,
    ) == pytest.approx(0.0)

    state.players[0].command = 2
    packed = engine._native_core().from_game_state(state)
    assert engine._native_heuristic().immediate_completion_value(
        packed,
        0,
    ) > 0.0


def test_projected_front_loss_penalty_uses_configured_rule() -> None:
    rules = GameRules.standard().with_overrides(lost_front_command_penalty=2)
    engine, state = standard_game(rules=rules)
    packed = engine._native_core().from_game_state(state)
    mask = (1 << int(Front.FIRST)) | (1 << int(Front.SECOND))

    assert engine._native_heuristic().projected_front_loss_command_penalty(
        packed,
        0,
        mask,
    ) == 4


def test_heuristic_honors_multiple_hero_allowance() -> None:
    rules = GameRules.standard().with_overrides(hero_play_limit_per_battle=2)
    engine, state = standard_game(rules=rules)
    hero = next(
        card_id
        for card_id, card in engine.cards.items()
        if card.get("hero")
    )
    state.players[0].hand[:] = [hero]
    state.hero_used[0] = 1
    packed = engine._native_core().from_game_state(state)
    available = engine._native_heuristic().hand_construction_value(packed, 0)

    state.hero_used[0] = 2
    packed = engine._native_core().from_game_state(state)
    exhausted = engine._native_heuristic().hand_construction_value(packed, 0)

    assert available > exhausted


def test_heuristic_counts_multiple_remaining_hero_uses() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    heroes = [
        card["id"]
        for card in data["cards"]
        if card.get("hero")
    ][:2]
    assert len(heroes) == 2

    rules_one = GameRules.standard().with_overrides(
        hero_play_limit_per_battle=1
    )
    rules_two = GameRules.standard().with_overrides(
        hero_play_limit_per_battle=2
    )
    engine_one, state_one = standard_game(rules=rules_one)
    engine_two, state_two = standard_game(rules=rules_two)
    state_one.players[0].hand[:] = heroes
    state_two.players[0].hand[:] = heroes

    value_one = engine_one._native_heuristic().hand_construction_value(
        engine_one._native_core().from_game_state(state_one),
        0,
    )
    value_two = engine_two._native_heuristic().hand_construction_value(
        engine_two._native_core().from_game_state(state_two),
        0,
    )

    assert value_two > value_one


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


def test_spending_final_command_midbattle_remains_nonterminal() -> None:
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

    maneuver = Maneuver(source, destination)
    assert Pass() in engine.legal_actions(state)
    assert maneuver in engine.legal_actions(state)

    child = state.clone()
    engine.apply(child, maneuver)
    assert child.phase.value == "battle"
    assert child.players[0].command == 0
    assert child.players[1].command == 5


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
    assert snapshot["command_before_collapse"] == [0, 5]
    assert snapshot["recovery_actual"] == [0, 0]
