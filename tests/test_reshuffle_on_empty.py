from __future__ import annotations

import json
from pathlib import Path

from longwar.cards import load_card_file
from longwar.game import Cycle, GameEngine, Pass

ROOT = Path(__file__).resolve().parents[1]


def deck() -> list[str]:
    return json.loads(
        (ROOT / "decks" / "reference.json").read_text(
            encoding="utf-8"
        )
    )["cards"]


def engine(*, reshuffle_on_empty: bool) -> GameEngine:
    return GameEngine(
        load_card_file(ROOT / "cards" / "cards.json"),
        opening_hand_size=13,
        draw_action_enabled=False,
        deck_size=30,
        recycle_between_battles=False,
        command_enabled=True,
        reshuffle_on_empty=reshuffle_on_empty,
    )


def state_for(test_engine: GameEngine):
    return test_engine.new_game(
        deck(),
        deck(),
        seed=7401,
        first_player=0,
        opening_bonus=False,
    )


def test_refill_reshuffles_discard_only_after_draw_pile_empties() -> None:
    test_engine = engine(reshuffle_on_empty=True)
    state = state_for(test_engine)
    player = state.players[0]
    player.hand = player.hand[:10]
    player.deck = ["namar"]
    player.discard = ["followed", "swore-to", "teyra"]

    test_engine.apply(state, Pass())
    test_engine.apply(state, Pass())

    assert len(player.hand) == 13
    assert player.discard == []
    assert len(player.deck) == 1
    assert state.deck_reshuffles[0] == 1


def test_reshuffle_on_empty_is_deterministic() -> None:
    test_engine = engine(reshuffle_on_empty=True)
    states = [state_for(test_engine) for _ in range(2)]

    for state in states:
        state.shuffle_seed = 991122
        state.players[0].hand = []
        state.players[0].deck = []
        state.players[0].discard = [
            "followed",
            "swore-to",
            "namar",
            "teyra",
            "the-fifty-men",
        ]
        test_engine.apply(state, Pass())
        test_engine.apply(state, Pass())

    assert states[0].players[0].hand == states[1].players[0].hand
    assert states[0].players[0].deck == states[1].players[0].deck
    assert states[0].shuffle_seed == states[1].shuffle_seed
    assert states[0].deck_reshuffles == states[1].deck_reshuffles == [1, 0]


def test_cycle_can_trigger_discard_reshuffle_when_draw_pile_is_empty() -> None:
    test_engine = engine(reshuffle_on_empty=True)
    state = state_for(test_engine)
    player = state.players[0]
    player.hand = ["namar"]
    player.deck = []
    player.discard = ["followed", "swore-to"]
    player.command = 5

    cycle = Cycle("namar")
    assert cycle in test_engine.legal_actions(state)

    test_engine.apply(state, cycle)

    assert player.command == 4
    assert len(player.hand) == 1
    assert len(player.deck) == 2
    assert player.discard == []
    assert state.deck_reshuffles[0] == 1


def test_cycle_is_not_offered_when_only_the_cycled_card_could_be_redrawn() -> None:
    test_engine = engine(reshuffle_on_empty=True)
    state = state_for(test_engine)
    player = state.players[0]
    player.hand = ["namar"]
    player.deck = []
    player.discard = []

    assert Cycle("namar") not in test_engine.legal_actions(state)


def test_flag_off_preserves_hard_exhaustion_behavior() -> None:
    test_engine = engine(reshuffle_on_empty=False)
    state = state_for(test_engine)
    player = state.players[0]
    player.hand = player.hand[:10]
    player.deck = ["namar"]
    player.discard = ["followed", "swore-to", "teyra"]

    test_engine.apply(state, Pass())
    test_engine.apply(state, Pass())

    assert len(player.hand) == 11
    assert player.discard == ["followed", "swore-to", "teyra"]
    assert state.deck_reshuffles[0] == 0
