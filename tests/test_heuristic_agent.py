from __future__ import annotations

import json
from pathlib import Path

import pytest

from longwar.agents import HeuristicAgent
from longwar.agents.random_agent import RandomAgent
from longwar.cards import load_card_file
from longwar.game import Front, GameEngine, Pass, Position, Rank


ROOT = Path(__file__).resolve().parents[1]


def engine_and_state():
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "reference.json").read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(data)
    state = engine.new_game(
        deck,
        deck,
        seed=91,
        first_player=0,
        opening_bonus=False,
    )
    return engine, state


def test_heuristic_default_has_no_random_exploration() -> None:
    agent = HeuristicAgent(seed=5)
    assert agent.exploration == 0.0

    with pytest.raises(ValueError, match="exploration"):
        HeuristicAgent(seed=5, exploration=1.1)


def test_opening_mulligan_is_deterministic_and_limited_to_two_cards() -> None:
    engine, _state = engine_and_state()
    hand = [
        "namar",
        "iria",
        "the-fifty-men",
        "seven-black-ships",
        "followed",
        "the-storm-broke",
        "the-house-at-orra",
        "the-children-of-the-salt-road",
        "the-road-was-cut",
        "the-three-brothers-of-avar",
    ]
    agent = HeuristicAgent(seed=5, exploration=0.0)

    first = agent.choose_mulligan(engine, hand)
    second = agent.choose_mulligan(engine, hand)

    assert first == second
    assert len(first) <= 2
    assert len(set(first)) == len(first)


def test_prepared_bond_and_name_are_not_treated_as_illegal_actions() -> None:
    engine, state = engine_and_state()
    state.players[0].hand = ["followed", "namar"]
    legal = engine.legal_actions(state)

    assert any(getattr(action, "card_id", None) == "followed" for action in legal)
    assert any(getattr(action, "card_id", None) == "namar" for action in legal)


def test_heuristic_always_returns_legal_action() -> None:
    engine, state = engine_and_state()
    action = HeuristicAgent(seed=5, exploration=0.0).choose(engine, state)
    assert action in engine.legal_actions(state)


def test_random_agent_does_not_pass_before_pass_is_legal() -> None:
    engine, state = engine_and_state()
    legal = engine.legal_actions(state)
    assert not any(isinstance(action, Pass) for action in legal)

    action = RandomAgent(seed=5, pass_probability=1.0).choose(engine, state)

    assert action in legal
    assert not isinstance(action, Pass)


def test_heuristic_does_not_use_opponent_hidden_hand_identities() -> None:
    engine, state = engine_and_state()
    state.players[0].hand = [
        "the-fifty-men",
        "followed",
        "namar",
        "the-story-is-false",
    ]
    state.players[1].hand = [
        "oren",
        "iria",
        "teyra",
        "he-never-came",
    ]

    first = HeuristicAgent(seed=7, exploration=0.0).choose(engine, state)

    state.players[1].hand = [
        "the-fifty-men",
        "seven-black-ships",
        "followed",
        "swore-to",
    ]
    second = HeuristicAgent(seed=7, exploration=0.0).choose(engine, state)

    assert first == second


def test_heuristic_values_all_four_fronts_independently() -> None:
    engine, state = engine_and_state()
    agent = HeuristicAgent(seed=3, exploration=0.0)

    ahead = state.clone()
    behind = state.clone()
    ahead.players[0].hand = []
    ahead.players[1].hand = []
    behind.players[0].hand = []
    behind.players[1].hand = []

    for front in Front:
        ahead.slot(0, Position(front, Rank.FRONT)).force = "the-fifty-men"
        behind.slot(1, Position(front, Rank.FRONT)).force = "the-fifty-men"

    assert agent.evaluate(engine, ahead, 0) > agent.evaluate(engine, behind, 0)


def test_passing_state_is_penalized_while_opponent_has_final_turn() -> None:
    engine, state = engine_and_state()
    state.players[0].hand = ["oren", "iria"]
    state.players[1].hand = ["namar", "teyra", "followed", "swore-to"]

    live_value = HeuristicAgent(seed=2, exploration=0.0).evaluate(engine, state, 0)

    passed = state.clone()
    passed.players[0].passed = True
    passed.pass_order = [0]
    passed_value = HeuristicAgent(seed=2, exploration=0.0).evaluate(
        engine,
        passed,
        0,
    )

    assert passed_value < live_value


def test_heuristic_values_unused_hero_as_flexible_force_or_name_resource() -> None:
    engine, state = engine_and_state()
    state.players[0].hand = ["daran-the-red-shield"]
    state.players[1].hand = []
    slot = state.slot(0, Position(Front.SECOND, Rank.FRONT))
    slot.force = "the-fifty-men"
    slot.bond = "followed"

    available = HeuristicAgent(seed=2, exploration=0.0).evaluate(engine, state, 0)

    spent = state.clone()
    spent.hero_used[0] = True
    unavailable = HeuristicAgent(seed=2, exploration=0.0).evaluate(
        engine,
        spent,
        0,
    )

    assert available > unavailable
