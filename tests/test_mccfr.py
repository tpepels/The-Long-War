from __future__ import annotations

import json
from pathlib import Path

import pytest

from longwar.agents.mccfr_agent import MCCFRAgent
from longwar.cards import load_card_file
from longwar.game import Front, GameEngine, Pass, Position, Rank
from longwar.game.model import StoryState
from longwar.mccfr import CFRNode, MCCFRTrainer, action_key, information_set_id

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.algorithm


def setup():
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "mobility-open-bonds.json").read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(data)
    state = engine.new_game(deck, deck, seed=77, first_player=0)
    return engine, deck, state


def test_mccfr_leaf_values_command_exhaustion_before_recovery() -> None:
    engine, deck, state = setup()
    trainer = MCCFRTrainer(engine, deck, deck, seed=8, max_depth=1)

    exhausted = state.clone()
    exhausted.players[0].command = 0
    exhausted.players[1].command = 1

    equal_zero = state.clone()
    equal_zero.players[0].command = 0
    equal_zero.players[1].command = 0

    assert trainer._leaf_value(exhausted, 0) < trainer._leaf_value(equal_zero, 0)


def test_information_set_hides_opponent_hand_identities() -> None:
    _, _, state = setup()
    state.players[1].hand = ["namar", "iria", "oren", "mara"]
    first = information_set_id(state, 0)

    state.players[1].hand = [
        "the-fifty-men",
        "seven-black-ships",
        "followed",
        "swore-again-to",
    ]
    second = information_set_id(state, 0)
    assert first == second


def test_information_set_hides_deck_order_but_not_own_composition() -> None:
    _, _, state = setup()
    first = information_set_id(state, 0)
    state.players[0].deck.reverse()
    assert information_set_id(state, 0) == first

    original = state.players[0].deck[0]
    replacement = next(
        card_id
        for card_id in state.players[0].deck[1:]
        if card_id != original
    )
    state.players[0].deck[0] = replacement
    assert information_set_id(state, 0) != first


def test_information_set_includes_public_story_identities() -> None:
    _, _, state = setup()
    state.stories[1] = [StoryState("public-story-a")]
    first = information_set_id(state, 0)

    state.stories[1] = [StoryState("public-story-b")]
    assert information_set_id(state, 0) != first


def test_regret_matching_prefers_positive_regret() -> None:
    node = CFRNode(
        regret_sum={"a": 3.0, "b": -2.0},
        strategy_sum={"a": 0.0, "b": 0.0},
    )
    strategy = node.strategy(["a", "b"])
    assert strategy["a"] == 1.0
    assert strategy["b"] == 0.0


def test_mccfr_policy_cannot_spend_last_command_when_pass_is_safe() -> None:
    engine, deck, _state = setup()
    state = engine.new_game(
        deck,
        deck,
        seed=77,
        first_player=0,
        opening_bonus=False,
    )
    state.players[0].command = 1
    state.players[1].command = 5
    state.operations_this_battle[:] = [1, 1]
    player = state.players[0]
    for zone in (player.hand, player.deck):
        if "the-grey-riders" in zone:
            zone.remove("the-grey-riders")
            break
    else:
        raise AssertionError("expected The Grey Riders in player 0 hidden zones")
    if "marched-with" not in player.hand:
        player.deck.remove("marched-with")
        if len(player.hand) >= engine.hand_limit:
            player.deck.append(player.hand.pop())
        player.hand.append("marched-with")
    slot = state.slot(0, Position(Front.FIRST, Rank.FRONT))
    slot.force = "the-grey-riders"

    legal = engine.legal_actions(state)
    unsafe = next(
        action
        for action in legal
        if getattr(action, "card_id", None) == "marched-with"
    )
    info_id = information_set_id(state, 0)
    policy = {
        "schema_version": 1,
        "infosets": {
            info_id: {
                "average_strategy": {
                    action_key(unsafe): 1.0,
                    "pass": 0.0,
                },
            },
        },
    }

    agent = MCCFRAgent(seed=10, policy=policy, deterministic=True)
    action = agent.choose(engine, state)

    assert isinstance(action, Pass)
    assert agent.last_decision["command_guard_applied"] is True


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
