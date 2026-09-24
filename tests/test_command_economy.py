from __future__ import annotations

import json
from pathlib import Path

import pytest

from longwar.cards import load_card_file
from longwar.game import (
    BoardTarget,
    Cycle,
    Draw,
    Front,
    GameEngine,
    Pass,
    PlayName,
    PlayPlot,
    PlaySubject,
    Position,
    Rank,
    SetStratagem,
)
from longwar.game.engine import IllegalAction
from longwar.game.model import SchemeState
from longwar.rules import GameRules

ROOT = Path(__file__).resolve().parents[1]
LEFT_FRONT = Position(Front.LEFT, Rank.FRONT)
CENTER_FRONT = Position(Front.CENTER, Rank.FRONT)
RIGHT_FRONT = Position(Front.RIGHT, Rank.FRONT)


def standard_game(*, first_player: int = 0, opening_bonus: bool = False):
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "reference.json").read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(data)
    state = engine.new_game(
        deck,
        deck,
        seed=26092701,
        first_player=first_player,
        opening_bonus=opening_bonus,
    )
    return engine, state


def test_standard_profile_matches_selected_automatic_force_candidate() -> None:
    assert GameRules.standard() == GameRules.force_candidate("automatic")


def test_standard_profile_is_later_force_baseline() -> None:
    engine, state = standard_game()

    assert engine.rules == GameRules.standard()
    assert not hasattr(engine, "deck_size")
    assert [len(player.hand) for player in state.players] == [10, 10]
    assert [len(player.deck) for player in state.players] == [24, 24]
    assert [player.command for player in state.players] == [20, 20]

    assert engine.recycle_between_battles is False
    assert engine.reshuffle_on_empty is True
    assert engine.draw_action_enabled is False
    assert engine.automatic_draw is True
    assert engine.cycle_enabled is False
    assert engine.pass_final_operation is True
    assert engine.pass_requires_both_acted is True
    assert engine.first_passer_starts_next_battle is True
    assert engine.completion_command_refund == 1
    assert engine.public_stratagems is True

    actions = engine.legal_actions(state)
    assert not any(isinstance(action, Draw) for action in actions)
    assert not any(isinstance(action, Cycle) for action in actions)
    assert not any(isinstance(action, Pass) for action in actions)


def test_opening_player_draws_automatically_at_start_of_first_turn() -> None:
    _, state = standard_game(first_player=0, opening_bonus=True)

    assert [len(player.hand) for player in state.players] == [11, 10]
    assert [len(player.deck) for player in state.players] == [23, 24]
    assert state.cards_drawn_this_battle == [1, 0]


def test_unaffordable_play_is_rejected_without_mutating_state() -> None:
    engine, state = standard_game()
    state.players[0].hand = ["the-fifty-men"]
    state.players[0].command = 1
    action = PlaySubject("the-fifty-men", CENTER_FRONT)
    before = state.clone()

    assert action not in engine.legal_actions(state)
    with pytest.raises(IllegalAction):
        engine.apply(state, action)

    assert state == before


def test_zero_command_leaves_pass_as_safety_action() -> None:
    engine, state = standard_game()
    state.players[0].command = 0

    assert engine.legal_actions(state) == [Pass()]


def test_pass_requires_both_players_to_act_then_grants_one_final_operation() -> None:
    engine, state = standard_game()
    assert Pass() not in engine.legal_actions(state)

    state.operations_this_battle[:] = [1, 1]
    before_final_hand = len(state.players[1].hand)
    engine.apply(state, Pass())

    assert state.players[0].passed is True
    assert state.pending_final_operation_for == 1
    assert state.active_player == 1
    assert len(state.players[1].hand) == before_final_hand + 1

    engine.apply(state, Pass())

    assert state.battle == 2
    assert state.pending_final_operation_for is None
    assert state.active_player == 0
    assert state.chooser is None


def test_all_cards_have_small_printed_command_costs() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    costs = [card["command_cost"] for card in data["cards"]]
    assert all(cost in {1, 2, 3} for cost in costs)
    assert set(costs) == {1, 2, 3}


def test_namar_completion_gets_global_and_card_specific_command_refunds() -> None:
    engine, state = standard_game()
    slot = state.slot(0, CENTER_FRONT)
    slot.subject = "the-fifty-men"
    slot.link = "followed"
    state.players[0].hand = ["namar"]
    state.players[0].command = 8

    engine.apply(state, PlayName("namar", CENTER_FRONT))

    assert slot.complete
    assert state.players[0].command == 9
    assert state.command_spent_this_battle[0] == 1
    assert state.completion_command_refunded_this_battle[0] == 1
    assert state.command_refunded_this_battle[0] == 2


def test_oren_completion_draws_a_card_and_gets_global_refund() -> None:
    engine, state = standard_game()
    slot = state.slot(0, CENTER_FRONT)
    slot.subject = "the-fifty-men"
    slot.link = "followed"
    state.players[0].hand = ["oren"]
    state.players[0].deck = ["swore-to"]
    state.players[0].command = 8

    engine.apply(state, PlayName("oren", CENTER_FRONT))

    assert state.players[0].command == 7
    assert "swore-to" in state.players[0].hand
    assert state.players[0].free_cycle is False


def test_teyra_completion_reveals_enemy_veiled_story() -> None:
    engine, state = standard_game()
    state.schemes[1][int(Front.CENTER)] = SchemeState("the-lamps-went-dark")
    slot = state.slot(0, CENTER_FRONT)
    slot.subject = "the-fifty-men"
    slot.link = "followed"
    state.players[0].hand = ["teyra"]

    engine.apply(state, PlayName("teyra", CENTER_FRONT))

    scheme = state.scheme(1, Front.CENTER)
    assert scheme is not None and scheme.revealed


def test_vara_completion_recovers_most_recent_discarded_bond() -> None:
    engine, state = standard_game()
    slot = state.slot(0, CENTER_FRONT)
    slot.subject = "the-fifty-men"
    slot.link = "swore-to"
    state.players[0].discard = ["followed", "he-never-came"]
    state.players[0].hand = ["vara"]

    engine.apply(state, PlayName("vara", CENTER_FRONT))

    assert "followed" in state.players[0].hand
    assert "followed" not in state.players[0].discard


def test_complete_maela_protects_subject_from_immediate_story() -> None:
    engine, state = standard_game(first_player=1)
    slot = state.slot(0, CENTER_FRONT)
    slot.subject = "the-fifty-men"
    slot.link = "followed"
    slot.name = "maela"
    state.players[1].hand = ["he-never-came"]

    actions = engine.legal_actions(state)

    assert not any(
        isinstance(action, PlayPlot)
        and action.targets == (BoardTarget(0, CENTER_FRONT),)
        for action in actions
    )


def test_complete_elian_discounts_adjacent_front_play_to_minimum_one() -> None:
    engine, state = standard_game()
    source = state.slot(0, LEFT_FRONT)
    source.subject = "the-fifty-men"
    source.link = "followed"
    source.name = "elian"
    state.players[0].hand = ["the-fifty-men"]

    action = PlaySubject("the-fifty-men", CENTER_FRONT)

    assert engine.cards["the-fifty-men"]["command_cost"] == 2
    assert engine.command_cost_for_action(state, action) == 1


def test_command_carries_and_replenishes_to_cap_between_battles() -> None:
    engine, state = standard_game()
    state.players[0].command = 7
    state.players[1].command = 14
    state.operations_this_battle[:] = [1, 1]
    state.slot(0, LEFT_FRONT).subject = "the-fifty-men"
    state.slot(0, CENTER_FRONT).subject = "the-fifty-men"
    state.slot(1, RIGHT_FRONT).subject = "the-fifty-men"

    engine.apply(state, Pass())
    engine.apply(state, Pass())

    assert state.battle == 2
    assert [player.command for player in state.players] == [17, 20]
    assert state.battle_start_command == [17, 20]
    assert state.active_player == 0


def test_stratagem_is_paid_public_operation_in_standard_game() -> None:
    engine, state = standard_game()
    state.players[0].hand = ["the-storm-broke"]
    state.players[0].command = 10
    action = SetStratagem("the-storm-broke")
    cost = engine.command_cost_for_action(state, action)

    engine.apply(state, action)

    stratagem = state.stratagem(0)
    assert state.players[0].command == 10 - cost
    assert stratagem is not None
    assert stratagem.revealed is True
    assert state.active_player == 1


def test_hero_offers_subject_and_name_modes_before_allowance_is_spent() -> None:
    engine, state = standard_game()
    state.players[0].hand = ["daran-the-red-shield"]
    actions = engine.legal_actions(state)

    assert any(
        isinstance(action, PlaySubject)
        and action.card_id == "daran-the-red-shield"
        for action in actions
    )
    assert any(
        isinstance(action, PlayName)
        and action.card_id == "daran-the-red-shield"
        for action in actions
    )


def test_playing_hero_as_name_uses_name_strength_and_locks_other_heroes() -> None:
    engine, state = standard_game()
    state.slot(0, CENTER_FRONT).subject = "the-fifty-men"
    state.players[0].hand = [
        "daran-the-red-shield",
        "lysa-of-the-salt-road",
    ]

    action = PlayName("daran-the-red-shield", CENTER_FRONT)
    assert action in engine.legal_actions(state)
    engine.apply(state, action)

    assert state.hero_used == [True, False]
    assert state.slot(0, CENTER_FRONT).name == "daran-the-red-shield"
    assert engine.position_strength(state, 0, CENTER_FRONT) == 8

    state.active_player = 0
    actions = engine.legal_actions(state)
    assert not any(
        getattr(candidate, "card_id", None) == "lysa-of-the-salt-road"
        and isinstance(candidate, (PlaySubject, PlayName))
        for candidate in actions
    )


def test_playing_hero_as_subject_locks_other_heroes_until_next_battle() -> None:
    engine, state = standard_game()
    state.players[0].hand = [
        "daran-the-red-shield",
        "theron-the-oathkeeper",
    ]

    action = next(
        candidate
        for candidate in engine.legal_actions(state)
        if isinstance(candidate, PlaySubject)
        and candidate.card_id == "daran-the-red-shield"
    )
    engine.apply(state, action)

    assert state.hero_used[0] is True
    state.active_player = 0
    assert not any(
        getattr(candidate, "card_id", None) == "theron-the-oathkeeper"
        and isinstance(candidate, (PlaySubject, PlayName))
        for candidate in engine.legal_actions(state)
    )

    state.operations_this_battle[:] = [1, 1]
    state.slot(0, CENTER_FRONT).subject = "the-fifty-men"
    state.slot(0, RIGHT_FRONT).subject = "the-fifty-men"
    engine.apply(state, Pass())
    engine.apply(state, Pass())

    assert state.battle == 2
    assert state.hero_used == [False, False]
