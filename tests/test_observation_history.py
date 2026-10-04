from __future__ import annotations

from pathlib import Path

from longwar.cards import load_card_file
from longwar.game import EffectChoice, Front, GameEngine, PlayBond, Position, Rank
from longwar.game.model import GameState, PlayerState
from longwar.mccfr import information_set_id

ROOT = Path(__file__).resolve().parents[1]
FRONT_2 = Position(Front.SECOND, Rank.FRONT)


def setup_return_state():
    data = load_card_file(ROOT / "cards" / "cards.json")
    engine = GameEngine(data)

    state = GameState(
        players=[
            PlayerState(
                deck=[],
                hand=[],
                discard=["followed"],
                command=engine.starting_command,
            ),
            PlayerState(deck=[], hand=[], command=engine.starting_command),
        ],
        active_player=0,
        battle=1,
    )
    # Keep a legal public destination for replaying the recovered Bond.
    state.slot(0, FRONT_2).force = "the-fifty-men"

    # Use the canonical recovery effect: the Bond starts in the public discard
    # pile and becomes hidden when returned to hand.
    state.pending_effects = [{
        "kind": 4,  # EFFECT_RECOVER
        "player": 0,
        "card": -1,
        "source": -1,
        "aux": 2,  # CARD_BOND
        "source_mask": 0,
        "dest_mask": 0,
        "flags": 0,
    }]
    return engine, state


def return_public_bond_to_hidden_hand(
    engine: GameEngine,
    state: GameState,
) -> None:
    action = EffectChoice("recover", card_id="followed")
    assert action in engine.legal_actions(state)
    engine.apply(state, action)

    assert "followed" in state.players[0].hand
    assert "followed" not in state.players[0].discard


def test_returned_public_card_remains_known_in_hidden_hand() -> None:
    engine, state = setup_return_state()

    return_public_bond_to_hidden_hand(engine, state)

    assert state.known_hidden_cards(1, 0, "hand") == ["followed"]
    assert any(
        event.card_id == "followed"
        and event.kind == "hidden_knowledge"
        and event.delta == 1
        for event in state.observations
    )


def test_known_hidden_card_is_consumed_when_played_publicly() -> None:
    engine, state = setup_return_state()
    return_public_bond_to_hidden_hand(engine, state)
    assert state.known_hidden_count(1, 0, "followed") == 1

    engine.apply(state, PlayBond("followed", FRONT_2))

    assert state.known_hidden_count(1, 0, "followed") == 0


def test_information_set_distinguishes_remembered_hidden_card() -> None:
    engine, state = setup_return_state()
    return_public_bond_to_hidden_hand(engine, state)

    remembered = information_set_id(state, 1)
    forgotten = state.clone()
    # Clearing the presentation log must not erase canonical knowledge.
    forgotten.observations.clear()
    assert information_set_id(forgotten, 1) == remembered
    forgotten.known_hidden_hand[1][0].clear()

    assert information_set_id(forgotten, 1) != remembered
