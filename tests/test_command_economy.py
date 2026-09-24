from __future__ import annotations

import json
from collections import Counter
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


def command_game(*, first_player: int = 0):
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "reference.json").read_text(
            encoding="utf-8"
        )
    )["cards"]
    engine = GameEngine(data)
    state = engine.new_game(
        deck,
        deck,
        seed=26092701,
        first_player=first_player,
        opening_bonus=False,
    )
    return engine, state


def test_standard_profile_uses_command_and_persistent_decks() -> None:
    engine, state = command_game()

    assert engine.rules == GameRules.standard()
    assert [len(player.hand) for player in state.players] == [10, 10]
    assert [len(player.deck) for player in state.players] == [20, 20]
    assert [player.command for player in state.players] == [20, 20]
    assert engine.recycle_between_battles is False
    assert engine.reshuffle_on_empty is True
    assert engine.draw_action_enabled is False
    assert not any(isinstance(action, Draw) for action in engine.legal_actions(state))
    assert any(isinstance(action, Cycle) for action in engine.legal_actions(state))


def test_unaffordable_play_is_rejected_without_mutating_state() -> None:
    engine, state = command_game()
    state.players[0].hand = ["the-fifty-men"]
    state.players[0].command = 1
    action = PlaySubject("the-fifty-men", CENTER_FRONT)
    before = state.clone()

    assert action not in engine.legal_actions(state)
    with pytest.raises(IllegalAction):
        engine.apply(state, action)

    assert state == before


def test_battle_refill_preserves_remaining_deck_order_and_discards() -> None:
    engine, state = command_game()
    player = state.players[0]
    player.hand = ["namar"]
    original_deck = list(player.deck)
    player.discard = ["followed"]

    engine.apply(state, Pass())
    engine.apply(state, Pass())

    assert Counter(player.hand) == Counter(["namar", *original_deck[-9:]])
    assert len(player.hand) == 10
    assert player.deck == original_deck[:-9]
    assert player.discard == ["followed"]
    assert state.deck_reshuffles[0] == 0


def test_all_cards_have_small_printed_command_costs() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    costs = [card["command_cost"] for card in data["cards"]]
    assert all(cost in {1, 2, 3} for cost in costs)
    assert set(costs) == {1, 2, 3}


def test_zero_command_leaves_only_pass() -> None:
    engine, state = command_game()
    state.players[0].command = 0

    assert engine.legal_actions(state) == [Pass()]


def test_cycle_costs_one_command_and_replaces_a_card() -> None:
    engine, state = command_game()
    state.players[0].hand = ["the-story-is-false"]
    state.players[0].deck = ["followed"]
    state.players[0].command = 6

    engine.apply(state, Cycle("the-story-is-false"))

    assert state.players[0].command == 5
    assert state.players[0].hand == ["followed"]
    assert state.players[0].discard[-1] == "the-story-is-false"
    assert state.command_spent_this_battle[0] == 1


def test_namar_completion_refunds_its_one_command_cost() -> None:
    engine, state = command_game()
    state.players[1].passed = True
    slot = state.slot(0, CENTER_FRONT)
    slot.subject = "the-fifty-men"
    slot.link = "followed"
    state.players[0].hand = ["namar"]
    state.players[0].command = 8

    engine.apply(state, PlayName("namar", CENTER_FRONT))

    assert slot.complete
    assert state.players[0].command == 8
    assert state.command_spent_this_battle[0] == 1
    assert state.command_refunded_this_battle[0] == 1


def test_oren_completion_makes_next_cycle_free() -> None:
    engine, state = command_game()
    state.players[1].passed = True
    slot = state.slot(0, CENTER_FRONT)
    slot.subject = "the-fifty-men"
    slot.link = "followed"
    state.players[0].hand = ["oren", "the-story-is-false"]
    state.players[0].deck = ["swore-to"]
    state.players[0].command = 8

    engine.apply(state, PlayName("oren", CENTER_FRONT))

    assert state.players[0].command == 6
    assert state.players[0].free_cycle is True
    cycle = Cycle("the-story-is-false")
    assert engine.command_cost_for_action(state, cycle) == 0

    engine.apply(state, cycle)

    assert state.players[0].command == 6
    assert state.players[0].free_cycle is False
    assert "swore-to" in state.players[0].hand


def test_teyra_completion_reveals_enemy_veiled_story() -> None:
    engine, state = command_game()
    state.players[1].passed = True
    state.schemes[1][int(Front.CENTER)] = SchemeState("the-lamps-went-dark")
    slot = state.slot(0, CENTER_FRONT)
    slot.subject = "the-fifty-men"
    slot.link = "followed"
    state.players[0].hand = ["teyra"]

    engine.apply(state, PlayName("teyra", CENTER_FRONT))

    scheme = state.scheme(1, Front.CENTER)
    assert scheme is not None and scheme.revealed


def test_vara_completion_recovers_most_recent_discarded_bond() -> None:
    engine, state = command_game()
    state.players[1].passed = True
    slot = state.slot(0, CENTER_FRONT)
    slot.subject = "the-fifty-men"
    slot.link = "swore-to"
    state.players[0].discard = ["followed", "he-never-came"]
    state.players[0].hand = ["vara"]

    engine.apply(state, PlayName("vara", CENTER_FRONT))

    assert "followed" in state.players[0].hand
    assert "followed" not in state.players[0].discard


def test_complete_maela_protects_subject_from_immediate_story() -> None:
    engine, state = command_game(first_player=1)
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
    engine, state = command_game()
    source = state.slot(0, LEFT_FRONT)
    source.subject = "the-fifty-men"
    source.link = "followed"
    source.name = "elian"
    state.players[0].hand = ["the-fifty-men"]

    action = PlaySubject("the-fifty-men", CENTER_FRONT)

    assert engine.cards["the-fifty-men"]["command_cost"] == 2
    assert engine.command_cost_for_action(state, action) == 1


def test_command_carries_and_replenishes_to_cap_between_battles() -> None:
    engine, state = command_game()
    state.players[0].command = 7
    state.players[1].command = 14
    state.slot(0, LEFT_FRONT).subject = "the-fifty-men"
    state.slot(0, CENTER_FRONT).subject = "the-fifty-men"
    state.slot(1, RIGHT_FRONT).subject = "the-fifty-men"

    engine.apply(state, Pass())
    engine.apply(state, Pass())

    assert state.battle == 2
    assert [player.command for player in state.players] == [17, 20]
    assert state.battle_start_command == [17, 20]


def test_setting_stratagem_is_paid_operation_in_command_mode() -> None:
    engine, state = command_game()
    state.players[0].hand = ["the-storm-broke"]
    state.players[0].command = 10
    action = SetStratagem("the-storm-broke")
    cost = engine.command_cost_for_action(state, action)

    engine.apply(state, action)

    assert state.players[0].command == 10 - cost
    assert state.active_player == 1
