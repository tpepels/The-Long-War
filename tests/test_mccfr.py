from __future__ import annotations

import json
from pathlib import Path

import pytest

from longwar.agents.mccfr_agent import MCCFRAgent
from longwar.cards import load_card_file
from longwar.game import GameEngine
from longwar.mccfr import CFRNode, MCCFRTrainer, information_set_id

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.algorithm


def setup():
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "reference.json").read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(data)
    state = engine.new_game(deck, deck, seed=77, first_player=0)
    return engine, deck, state


def test_information_set_hides_opponent_hand_identities() -> None:
    _, _, state = setup()
    state.players[1].hand = ["namar", "iria", "oren", "teyra"]
    first = information_set_id(state, 0)

    state.players[1].hand = [
        "the-fifty-men",
        "seven-black-ships",
        "followed",
        "swore-to",
    ]
    second = information_set_id(state, 0)
    assert first == second


def test_information_set_hides_deck_order_but_not_own_composition() -> None:
    _, _, state = setup()
    first = information_set_id(state, 0)
    state.players[0].deck.reverse()
    assert information_set_id(state, 0) == first

    state.players[0].deck[0] = "namar"
    assert information_set_id(state, 0) != first


def test_regret_matching_prefers_positive_regret() -> None:
    node = CFRNode(
        regret_sum={"a": 3.0, "b": -2.0},
        strategy_sum={"a": 0.0, "b": 0.0},
    )
    strategy = node.strategy(["a", "b"])
    assert strategy["a"] == 1.0
    assert strategy["b"] == 0.0


def test_mccfr_training_produces_policy_and_legal_agent_action() -> None:
    engine, deck, state = setup()
    trainer = MCCFRTrainer(engine, deck, deck, seed=9, max_depth=2)
    summary = trainer.train(2)
    policy = trainer.policy_payload()

    assert summary.information_sets > 0
    assert policy["algorithm"] == "depth_limited_external_sampling_mccfr"
    assert policy["infosets"]

    agent = MCCFRAgent(seed=11, policy=policy, deterministic=True)
    action = agent.choose(engine, state)
    assert action in engine.legal_actions(state)
