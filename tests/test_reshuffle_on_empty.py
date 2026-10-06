from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from longwar.cards import load_card_file
from longwar.game import EndTurn, GameEngine, Pass
from longwar.rules import GameRules


ROOT = Path(__file__).resolve().parents[1]


def setup_state(seed: int = 7401):
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "mobility-open-bonds.json").read_text(encoding="utf-8")
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
    # Force the one true Battle Pass. Player 1 then begins the first closing
    # turn and performs the draw under test.
    state.active_player = 0
    state.players[0].hand.clear()
    state.players[0].deck.clear()
    state.players[0].discard.clear()
    state.operations_this_battle[:] = [1, 1]
    assert engine.legal_actions(state) == [Pass()]
    engine.apply(state, Pass())
    assert state.active_player == 1


def test_draw_uses_existing_draw_pile_without_touching_discard() -> None:
    engine, state = setup_state()
    player = state.players[1]
    player.hand = player.hand[:9]
    player.deck = ["namar"]
    player.discard = ["followed", "swore-again-to"]

    start_final_turn(engine, state)

    assert "namar" in player.hand
    assert player.deck == []
    assert player.discard == ["followed", "swore-again-to"]
    assert state.deck_reshuffles[1] == 0


def test_required_draw_reshuffles_discard_when_draw_pile_is_empty() -> None:
    engine, state = setup_state()
    player = state.players[1]
    player.hand = player.hand[:9]
    player.deck = []
    player.discard = ["followed", "swore-again-to", "namar"]

    start_final_turn(engine, state)

    assert len(player.hand) == 10
    assert len(player.deck) == 2
    assert player.discard == []
    assert state.deck_reshuffles[1] == 1


def test_empty_pile_reshuffle_is_deterministic_for_same_shuffle_seed() -> None:
    engine, first = setup_state(seed=7501)
    _engine, second = setup_state(seed=7502)

    drawn = []
    for state in (first, second):
        state.shuffle_seed = 991122
        player = state.players[1]
        player.hand = player.hand[:9]
        before = Counter(player.hand)
        player.deck = []
        player.discard = [
            "followed",
            "swore-again-to",
            "namar",
            "mara",
            "the-fifty-men",
        ]
        start_final_turn(engine, state)
        added = Counter(player.hand) - before
        assert sum(added.values()) == 1
        drawn.append(next(iter(added)))

    assert drawn[0] == drawn[1]
    assert first.players[1].deck == second.players[1].deck
    assert first.shuffle_seed == second.shuffle_seed


def test_next_battle_turn_draw_reshuffles_before_overflow_cleanup() -> None:
    engine, state = setup_state()

    # Player 1 is unable to act and becomes the passer. Player 0 is the
    # non-passer: its first closing-turn draw uses the one existing deck card
    # to reach 10 cards. Battle-end refill needs no card, but the next Battle's
    # normal turn draw still happens. With an empty deck, that draw reshuffles
    # the discard pile before hand-limit cleanup.
    state.active_player = 1
    state.players[1].hand.clear()
    state.players[1].deck.clear()
    state.players[1].discard.clear()
    state.players[0].hand = state.players[0].hand[:9]
    state.players[0].deck = ["the-fifty-men"]
    state.players[0].discard = ["followed", "swore-again-to", "namar"]
    state.operations_this_battle[:] = [1, 1]

    assert engine.legal_actions(state) == [Pass()]
    engine.apply(state, Pass())
    assert state.active_player == 0
    engine.apply(state, EndTurn())
    assert state.active_player == 1
    engine.apply(state, EndTurn())

    assert state.battle == 2
    assert state.active_player == 0
    assert state.deck_reshuffles[0] == 1
    assert state.players[0].discard == []
    assert len(state.players[0].hand) == engine.hand_limit + 1
    assert len(state.players[0].deck) == 2
    assert state.pending_draw_discard_for == 0
