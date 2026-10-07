from __future__ import annotations

import json
from pathlib import Path

import pytest

from longwar.cards import load_card_file
from longwar.game import (
    EndTurn,
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
    battle: int = 3,
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
    state.battle = battle
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


def test_all_current_cards_have_nonnegative_native_safe_command_costs() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    costs = [card["command_cost"] for card in data["cards"]]
    assert costs
    assert all(type(cost) is int and 0 <= cost < 128 for cost in costs)



def test_ordinary_discount_defaults_to_minimum_cost_one() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    iven = next(card for card in data["cards"] if card["id"] == "iven")
    iven["design_rules"].pop("minimum_cost")
    engine = GameEngine(data)

    deck = json.loads(
        (ROOT / "decks" / "mobility-open-bonds.json").read_text(
            encoding="utf-8"
        )
    )["cards"]
    state = engine.new_game(
        deck,
        deck,
        seed=26092702,
        first_player=0,
        opening_bonus=False,
    )
    state.battle = 3
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
    ).commands(1, 5).hand(0, "followed")

    action = PlayBond("followed", front)
    assert engine.command_cost_for_action(state, action) == 1


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
    engine.apply(state, EndTurn())
    engine.apply(state, EndTurn())

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
        Position(Front.SECOND, Rank.FRONT),
        force="the-fifty-men",
    )

    engine.apply(state, Pass())
    engine.apply(state, EndTurn())
    engine.apply(state, EndTurn())

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
    engine.apply(state, EndTurn())
    engine.apply(state, EndTurn())

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
        Position(Front.SECOND, Rank.FRONT),
        force="the-fifty-men",
    ).formation(
        0,
        Position(Front.THIRD, Rank.FRONT),
        force="the-fifty-men",
    )

    engine.apply(state, Pass())
    engine.apply(state, EndTurn())
    engine.apply(state, EndTurn())

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
        Position(Front.SECOND, Rank.FRONT),
        force="the-fifty-men",
    ).formation(
        0,
        Position(Front.THIRD, Rank.FRONT),
        force="the-fifty-men",
    )

    engine.apply(state, Pass())
    engine.apply(state, EndTurn())
    engine.apply(state, EndTurn())

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


def test_rollout_guard_keeps_legal_zero_command_midbattle_actions() -> None:
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
    assert maneuver in rollout_safe
    assert rollout_filtered == 0


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


def test_heuristic_honors_separate_hero_mode_allowances() -> None:
    engine, state = standard_game()
    hero = next(
        card_id
        for card_id, card in engine.cards.items()
        if card.get("hero")
    )
    state.players[0].hand[:] = [hero]

    state.hero_used[0] = 1  # Force used, Name still available.
    packed = engine._native_core().from_game_state(state)
    one_mode_left = engine._native_heuristic().hand_construction_value(packed, 0)

    state.hero_used[0] = 3  # Force and Name both used.
    packed = engine._native_core().from_game_state(state)
    exhausted = engine._native_heuristic().hand_construction_value(packed, 0)

    assert one_mode_left > exhausted


def test_heuristic_counts_force_and_name_hero_uses_separately() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    heroes = [
        card["id"]
        for card in data["cards"]
        if card.get("hero")
    ][:2]
    assert len(heroes) == 2

    force_only = GameRules.standard().with_overrides(
        hero_name_play_limit_per_battle=0,
    )
    both_modes = GameRules.standard()
    engine_one, state_one = standard_game(rules=force_only)
    engine_two, state_two = standard_game(rules=both_modes)
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
    legal = engine.legal_actions(state)
    assert Pass() not in legal
    assert EndTurn() in legal
    assert maneuver in legal

    child = state.clone()
    engine.apply(child, maneuver)
    assert child.phase.value == "battle"
    assert child.players[0].command == 0
    assert child.players[1].command == 5


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"actions_per_turn": 0}, "actions_per_turn"),
        ({"closing_turns_after_pass": 0}, "closing_turns_after_pass"),
        ({"opening_hand_size": 10, "hand_limit": 9}, "hand_limit"),
        ({"opening_hand_size": 2, "mulligan_max_cards": 3}, "mulligan_max_cards"),
    ],
)
def test_invalid_turn_and_hand_rule_configurations_are_rejected(
    changes: dict[str, int],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        GameRules.standard().with_overrides(**changes)


@pytest.mark.parametrize(
    "field",
    [
        "hero_force_play_limit_per_battle",
        "hero_name_play_limit_per_battle",
    ],
)
def test_hero_mode_allowance_cannot_exceed_native_bit_capacity(field: str) -> None:
    with pytest.raises(ValueError):
        GameRules.standard().with_overrides(**{field: 2})


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


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("opening_hand_size", 256),
        ("hand_limit", 256),
        ("turn_draw_count", 256),
        ("actions_per_turn", 256),
        ("closing_turns_after_pass", 256),
        ("command_cap", 32768),
        ("command_recovery_start", 32768),
        ("maneuver_command_cost", 32768),
        ("lost_front_command_penalty", 8192),
    ],
)
def test_rule_overrides_must_fit_native_storage(field: str, value: int) -> None:
    changes = {field: value}
    if field == "opening_hand_size":
        changes["hand_limit"] = value
    if field == "command_cap":
        changes["starting_command"] = 20
    with pytest.raises(ValueError, match=field):
        GameRules.standard().with_overrides(**changes)


def test_recovery_floor_cannot_exceed_command_cap() -> None:
    with pytest.raises(ValueError, match="command_recovery_floor"):
        GameRules.standard().with_overrides(
            command_cap=10,
            starting_command=10,
            command_recovery_floor=11,
        )



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
        Position(Front.SECOND, Rank.FRONT),
        force="the-fifty-men",
    )

    engine.apply(state, Pass())
    engine.apply(state, EndTurn())
    engine.apply(state, EndTurn())

    assert state.phase.value == "complete"
    assert state.winner == 1
    snapshot = state.last_battle_snapshot
    assert snapshot is not None
    assert snapshot["fronts_lost"][0] == 1
    assert snapshot["command_before_collapse"] == [0, 5]
    assert snapshot["recovery_actual"] == [0, 0]
