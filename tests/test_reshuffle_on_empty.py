from __future__ import annotations

import json
from pathlib import Path

from longwar.cards import load_card_file
from longwar.game import GameEngine, Pass
from longwar.rules import GameRules


ROOT = Path(__file__).resolve().parents[1]


def setup_state(seed: int = 7401):
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "reference.json").read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(data, rules=GameRules.standard())
    state = engine.new_game(
        deck,
        deck,
        seed=seed,
        first_player=0,
        opening_bonus=False,
    )
    return engine, state


def start_final_turn(engine: GameEngine, state) -> None:
    state.active_player = 0
    state.operations_this_battle[:] = [1, 1]
    engine.apply(state, Pass())
    assert state.active_player == 1


def test_draw_uses_existing_draw_pile_without_touching_discard() -> None:
    engine, state = setup_state()
    player = state.players[1]
    player.hand = player.hand[:9]
    player.deck = ["namar"]
    player.discard = ["followed", "swore-to"]

    start_final_turn(engine, state)

    assert "namar" in player.hand
    assert player.deck == []
    assert player.discard == ["followed", "swore-to"]
    assert state.deck_reshuffles[1] == 0


def test_required_draw_reshuffles_discard_when_draw_pile_is_empty() -> None:
    engine, state = setup_state()
    player = state.players[1]
    player.hand = player.hand[:9]
    player.deck = []
    player.discard = ["followed", "swore-to", "namar"]

    start_final_turn(engine, state)

    assert len(player.hand) == 10
    assert len(player.deck) == 2
    assert player.discard == []
    assert state.deck_reshuffles[1] == 1


def test_empty_pile_reshuffle_is_deterministic_for_same_shuffle_seed() -> None:
    engine, first = setup_state(seed=7501)
    _engine, second = setup_state(seed=7502)

    for state in (first, second):
        state.shuffle_seed = 991122
        player = state.players[1]
        player.hand = player.hand[:9]
        player.deck = []
        player.discard = [
            "followed",
            "swore-to",
            "namar",
            "teyra",
            "the-fifty-men",
        ]
        start_final_turn(engine, state)

    assert first.players[1].hand[-1] == second.players[1].hand[-1]
    assert first.players[1].deck == second.players[1].deck
    assert first.shuffle_seed == second.shuffle_seed


def test_battle_end_does_not_recycle_discard_without_a_draw() -> None:
    engine, state = setup_state()
    state.players[0].hand = state.players[0].hand[:10]
    state.players[0].deck = []
    state.players[0].discard = ["followed", "swore-to", "namar"]

    # Make the final opponent turn drawable without touching player 0.
    state.players[1].hand = state.players[1].hand[:9]
    state.operations_this_battle[:] = [1, 1]
    state.active_player = 0
    engine.apply(state, Pass())
    engine.apply(state, Pass())

    assert state.battle == 2
    assert state.players[0].discard == ["followed", "swore-to", "namar"]
    assert state.deck_reshuffles[0] == 0
    assert state.pending_draw_discard_for == 0
