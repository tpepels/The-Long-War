from __future__ import annotations

import json
from pathlib import Path

from longwar.cards import load_card_file
from longwar.game import Discard, Draw, GameEngine, Pass
from longwar.rules import GameRules

ROOT = Path(__file__).resolve().parents[1]


def variant_game(**changes):
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "reference.json").read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(
        data,
        rules=GameRules.standard().with_overrides(**changes),
    )
    state = engine.new_game(
        deck,
        deck,
        seed=26092334,
        first_player=0,
    )
    return engine, state


def test_paid_draw_is_an_explicit_rule_variant() -> None:
    engine, state = variant_game(
        automatic_draw=False,
        paid_draw_enabled=True,
    )
    before_hand = len(state.players[0].hand)

    assert Draw() in engine.legal_actions(state)
    assert engine.command_cost_for_action(state, Draw()) == 1

    engine.apply(state, Draw())

    assert len(state.players[0].hand) == before_hand + 1
    assert state.players[0].command == 19
    assert state.operations_this_battle[0] == 1
    assert state.active_player == 1


def test_paid_draw_can_keep_the_operation() -> None:
    engine, state = variant_game(
        automatic_draw=False,
        paid_draw_enabled=True,
        paid_draw_consumes_operation=False,
    )

    engine.apply(state, Draw())

    assert state.players[0].command == 19
    assert state.operations_this_battle[0] == 0
    assert state.active_player == 0
    assert Draw() in engine.legal_actions(state)


def test_automatic_draw_can_have_a_hand_cap() -> None:
    _, state = variant_game(automatic_draw_hand_limit=10)

    assert [len(hand) for hand in state.opening_hands] == [10, 10]
    assert len(state.players[0].hand) == 10
    assert state.cards_drawn_this_battle == [0, 0]


def test_battle_end_hand_limit_creates_explicit_cleanup() -> None:
    engine, state = variant_game(battle_end_hand_limit=9)
    state.operations_this_battle[:] = [1, 1]

    engine.apply(state, Pass())
    engine.apply(state, Pass())

    assert state.battle == 2
    assert state.cleanup_pending
    assert all(
        isinstance(action, Discard)
        for action in engine.legal_actions(state)
    )

    while state.cleanup_pending:
        engine.apply(state, engine.legal_actions(state)[0])

    assert len(state.players[0].hand) == 10
    assert len(state.players[1].hand) == 9


def test_stronger_battle_end_hand_limit_is_data_not_a_mode() -> None:
    engine, state = variant_game(battle_end_hand_limit=7)
    state.operations_this_battle[:] = [1, 1]

    engine.apply(state, Pass())
    engine.apply(state, Pass())

    discarded = 0
    while state.cleanup_pending:
        engine.apply(state, engine.legal_actions(state)[0])
        discarded += 1

    assert discarded >= 6
    assert len(state.players[0].hand) == 8
    assert len(state.players[1].hand) == 7
