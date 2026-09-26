from __future__ import annotations

import json
from pathlib import Path

from longwar.cards import load_card_file
from longwar.game import BoardTarget, Front, GameEngine, PlayName, PlayStory, Position, Rank
from longwar.game.model import GameState, PlayerState
from longwar.mccfr import information_set_id

ROOT = Path(__file__).resolve().parents[1]
FRONT_2 = Position(Front.SECOND, Rank.FRONT)


def setup_return_state():
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "reference.json").read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(data)

    p0_deck = list(deck)
    for card_id in ("the-fifty-men", "followed", "namar"):
        p0_deck.remove(card_id)

    p1_deck = list(deck)
    p1_deck.remove("he-never-came")

    state = GameState(
        players=[
            PlayerState(deck=p0_deck, hand=[], command=engine.starting_command),
            PlayerState(deck=p1_deck, hand=["he-never-came"], command=engine.starting_command),
        ],
        active_player=1,
    )
    slot = state.slot(0, FRONT_2)
    slot.force = "the-fifty-men"
    slot.bond = "followed"
    slot.name = "namar"
    return engine, deck, state


def test_returned_public_name_remains_known_in_hidden_hand() -> None:
    engine, _, state = setup_return_state()

    engine.apply(
        state,
        PlayStory(
            "he-never-came",
            (BoardTarget(0, FRONT_2),),
        ),
    )

    assert "namar" in state.players[0].hand
    assert len(state.players[0].hand) == 2  # returned Name + automatic turn draw
    assert state.known_hidden_cards(1, 0, "hand") == ["namar"]
    assert any(
        event.card_id == "namar"
        and event.kind == "hidden_knowledge"
        and event.delta == 1
        for event in state.observations
    )


def test_known_hidden_card_is_consumed_when_played_publicly() -> None:
    engine, _, state = setup_return_state()
    engine.apply(
        state,
        PlayStory(
            "he-never-came",
            (BoardTarget(0, FRONT_2),),
        ),
    )
    assert state.active_player == 0
    assert state.known_hidden_count(1, 0, "namar") == 1

    engine.apply(state, PlayName("namar", FRONT_2))

    assert state.known_hidden_count(1, 0, "namar") == 0


def test_information_set_distinguishes_remembered_hidden_card() -> None:
    engine, _, state = setup_return_state()
    engine.apply(
        state,
        PlayStory(
            "he-never-came",
            (BoardTarget(0, FRONT_2),),
        ),
    )

    remembered = information_set_id(state, 1)
    forgotten = state.clone()
    # Clearing the presentation log must not erase canonical knowledge.
    forgotten.observations.clear()
    assert information_set_id(forgotten, 1) == remembered
    forgotten.known_hidden_hand[1][0].clear()

    assert information_set_id(forgotten, 1) != remembered
