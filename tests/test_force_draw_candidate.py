from __future__ import annotations

import json
from pathlib import Path

from longwar.cards import load_card_file
from longwar.game import (
    Cycle,
    Draw,
    Front,
    GameEngine,
    Pass,
    PlayName,
    PlaySubject,
    Position,
    Rank,
    SetStratagem,
)
from longwar.rules import GameRules

ROOT = Path(__file__).resolve().parents[1]
CENTER_FRONT = Position(Front.CENTER, Rank.FRONT)


def candidate(*, automatic: bool = False, paid: bool = False):
    data = load_card_file(ROOT / "cards" / "experiments" / "force-draw-cards.json")
    deck = json.loads(
        (
            ROOT
            / "decks"
            / "experiments"
            / "force-rich-34-reference.json"
        ).read_text(encoding="utf-8")
    )["cards"]
    draw_mode = "automatic" if automatic else "paid"
    rules = GameRules.force_candidate(draw_mode)
    if not automatic and not paid:
        rules = rules.with_overrides(paid_draw_enabled=False)
    engine = GameEngine(data, rules=rules)
    state = engine.new_game(deck, deck, seed=26092334, first_player=0)
    return engine, state


def test_force_rich_reference_has_14_forces_and_6_names() -> None:
    data = load_card_file(ROOT / "cards" / "experiments" / "force-draw-cards.json")
    index = {card["id"]: card for card in data["cards"]}
    deck = json.loads(
        (
            ROOT
            / "decks"
            / "experiments"
            / "force-rich-34-reference.json"
        ).read_text(encoding="utf-8")
    )["cards"]

    assert len(deck) == 34
    assert sum(index[card_id]["type"] == "subject" for card_id in deck) == 14
    assert sum(index[card_id]["type"] == "name" for card_id in deck) == 6


def test_automatic_draw_starts_first_turn_with_one_fresh_card() -> None:
    engine, state = candidate(automatic=True)

    assert [len(hand) for hand in state.opening_hands] == [10, 10]
    assert len(state.players[0].hand) == 11
    assert state.cards_drawn_this_battle == [1, 0]


def test_paid_draw_costs_one_command_and_uses_operation() -> None:
    engine, state = candidate(paid=True)
    before_hand = len(state.players[0].hand)

    assert Draw() in engine.legal_actions(state)
    assert engine.command_cost_for_action(state, Draw()) == 1

    engine.apply(state, Draw())

    assert len(state.players[0].hand) == before_hand + 1
    assert state.players[0].command == 19
    assert state.command_spent_this_battle[0] == 1
    assert state.operations_this_battle[0] == 1
    assert state.active_player == 1


def test_cycle_is_absent_from_candidate() -> None:
    engine, state = candidate(paid=True)

    assert not any(isinstance(action, Cycle) for action in engine.legal_actions(state))


def test_pass_waits_until_both_players_operated() -> None:
    engine, state = candidate(paid=True)

    assert Pass() not in engine.legal_actions(state)

    state.operations_this_battle = [1, 1]

    assert Pass() in engine.legal_actions(state)


def test_first_pass_gives_exactly_one_final_operation_and_next_initiative() -> None:
    engine, state = candidate(paid=True)
    state.operations_this_battle = [1, 1]
    state.players[1].hand = ["the-fifty-men"]

    engine.apply(state, Pass())

    assert state.pending_final_operation_for == 1
    assert state.active_player == 1

    engine.apply(state, PlaySubject("the-fifty-men", CENTER_FRONT))

    assert state.battle == 2
    assert state.pending_final_operation_for is None
    assert state.active_player == 0


def test_completion_refunds_one_command_before_name_utility() -> None:
    engine, state = candidate(paid=True)
    state.operations_this_battle = [1, 1]
    slot = state.slot(0, CENTER_FRONT)
    slot.subject = "the-fifty-men"
    slot.link = "followed"
    state.players[0].hand = ["iria"]
    state.players[0].command = 8

    engine.apply(state, PlayName("iria", CENTER_FRONT))

    assert slot.complete
    assert state.players[0].command == 8
    assert state.completion_command_refunded_this_battle[0] == 1


def test_public_stratagem_is_immediately_revealed() -> None:
    engine, state = candidate(paid=True)
    state.players[0].hand = ["the-storm-broke"]

    engine.apply(state, SetStratagem("the-storm-broke"))

    stratagem = state.stratagem(0)
    assert stratagem is not None
    assert stratagem.revealed is True
