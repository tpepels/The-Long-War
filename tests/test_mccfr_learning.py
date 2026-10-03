from __future__ import annotations

import json
from pathlib import Path

import pytest

from longwar.cards import load_card_file
from longwar.game import Front, GameEngine, Position, Rank
from longwar.game.model import StratagemState
from longwar.mccfr import MCCFRTrainer, action_key, information_set_id

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.algorithm


def setup():
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "mobility-open-bonds.json").read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(data)
    state = engine.new_game(deck, deck, seed=19, first_player=0)
    return engine, deck, state


def test_fixed_state_training_is_reproducible() -> None:
    engine, deck, state = setup()
    state.battle = 3
    state.players[1].passed = True
    state.pass_order = [1]
    state.closing_turns_remaining = 2
    state.active_player = 0
    state.players[0].hand = ["the-fifty-men"]
    state.players[1].hand = []
    state.slot(0, Position(Front.FIRST, Rank.FRONT)).force = "the-fifty-men"
    state.slot(0, Position(Front.SECOND, Rank.FRONT)).force = "the-fifty-men"

    trainers = [
        MCCFRTrainer(engine, deck, deck, seed=55, max_depth=1),
        MCCFRTrainer(engine, deck, deck, seed=55, max_depth=1),
    ]
    for trainer in trainers:
        trainer.train_from_state(state, iterations=30)

    assert trainers[0].policy_payload() == trainers[1].policy_payload()


def test_face_down_opponent_stratagem_identity_is_not_in_information_set() -> None:
    engine, _deck, state = setup()
    state.stratagems[1] = StratagemState(
        "the-ground-was-held",
        revealed=False,
    )
    first = information_set_id(state, 0)

    changed_hidden = state.clone()
    changed_hidden.stratagems[1].card_id = "the-lines-held"
    assert information_set_id(changed_hidden, 0) == first

    # The owner knows which card they set.
    assert information_set_id(changed_hidden, 1) != information_set_id(state, 1)

    # Once revealed, the opponent can distinguish the identity too.
    revealed = changed_hidden.clone()
    revealed.stratagems[1].revealed = True
    assert information_set_id(revealed, 0) != first


def test_direct_longwar_traversal_matches_generic_core() -> None:
    engine, deck, state = setup()
    direct = MCCFRTrainer(
        engine,
        deck,
        deck,
        seed=812,
        max_depth=2,
        direct_traversal=True,
    )
    generic = MCCFRTrainer(
        engine,
        deck,
        deck,
        seed=812,
        max_depth=2,
        direct_traversal=False,
    )

    direct_summary = direct.train_from_state(state, iterations=12)
    generic_summary = generic.train_from_state(state, iterations=12)

    assert direct_summary == generic_summary
    assert direct.policy_payload()["infosets"] == generic.policy_payload()["infosets"]
