from __future__ import annotations

from pathlib import Path

from longwar.cards import load_card_file
from longwar.game import Front, GameEngine, Pass, PlayName, Position, Rank
from longwar.game.model import GameState, PlayerState, StratagemState
from longwar.mccfr import information_set_id

ROOT = Path(__file__).resolve().parents[1]
FRONT_2 = Position(Front.SECOND, Rank.FRONT)


def setup_return_state():
    data = load_card_file(ROOT / "cards" / "cards.json")
    engine = GameEngine(data)

    state = GameState(
        players=[
            PlayerState(deck=[], hand=[], command=engine.starting_command),
            PlayerState(deck=[], hand=[], command=engine.starting_command),
        ],
        active_player=0,
        operations_this_battle=[1, 1],
    )

    # No Step Back turns the lost Front's Retreat into a drive-off. Stayed
    # Behind For then leaves the Bond in place and returns the public Name to
    # its owner's hand, which must become remembered hidden information.
    own = state.slot(0, FRONT_2)
    own.force = "the-fifty-men"
    own.bond = "stayed-behind-for"
    own.name = "namar"
    state.stratagems[0] = StratagemState(
        "no-step-back",
        fronts=(Front.SECOND,),
    )

    enemy = state.slot(1, FRONT_2)
    enemy.force = "a-hundred-shields"
    enemy.bond = "stood-fast-with"
    enemy.name = "asha-the-shield-bearer"

    return engine, state


def return_public_name_to_hidden_hand(engine: GameEngine, state: GameState) -> None:
    engine.apply(state, Pass())
    engine.apply(state, Pass())
    assert state.active_player == 0
    assert state.battle == 2
    assert state.slot(0, FRONT_2).force is None
    assert state.slot(0, FRONT_2).bond == "stayed-behind-for"
    assert state.slot(0, FRONT_2).name is None


def test_returned_public_name_remains_known_in_hidden_hand() -> None:
    engine, state = setup_return_state()

    return_public_name_to_hidden_hand(engine, state)

    assert "namar" in state.players[0].hand
    assert state.known_hidden_cards(1, 0, "hand") == ["namar"]
    assert any(
        event.card_id == "namar"
        and event.kind == "hidden_knowledge"
        and event.delta == 1
        for event in state.observations
    )


def test_known_hidden_card_is_consumed_when_played_publicly() -> None:
    engine, state = setup_return_state()
    return_public_name_to_hidden_hand(engine, state)
    assert state.known_hidden_count(1, 0, "namar") == 1

    engine.apply(state, PlayName("namar", FRONT_2))

    assert state.known_hidden_count(1, 0, "namar") == 0


def test_information_set_distinguishes_remembered_hidden_card() -> None:
    engine, state = setup_return_state()
    return_public_name_to_hidden_hand(engine, state)

    remembered = information_set_id(state, 1)
    forgotten = state.clone()
    # Clearing the presentation log must not erase canonical knowledge.
    forgotten.observations.clear()
    assert information_set_id(forgotten, 1) == remembered
    forgotten.known_hidden_hand[1][0].clear()

    assert information_set_id(forgotten, 1) != remembered
