from __future__ import annotations

import json
from pathlib import Path

import pytest

from longwar.agents import HeuristicAgent
from longwar.agents.random_agent import RandomAgent
from longwar.cards import load_card_file
from longwar.game import Discard, Front, GameEngine, Pass, Position, Rank


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


def test_discard_scoring_does_not_peek_at_own_unknown_deck_order() -> None:
    engine, state = engine_and_state()
    agent = HeuristicAgent(seed=6, exploration=0.0)
    state.pending_draw_discard_for = 0
    state.active_player = 0

    action = Discard(state.players[0].hand[0])
    first = agent._score_action(engine, state, 0, action)

    reordered = state.clone()
    reordered.players[0].deck.reverse()
    second = agent._score_action(engine, reordered, 0, action)

    assert first == pytest.approx(second)


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


def test_first_pass_is_penalized_while_opponent_has_normal_reply_turn() -> None:
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

def test_complete_named_formation_is_distinguished_from_force_plus_name() -> None:
    engine, state = engine_and_state()
    agent = HeuristicAgent(seed=11, exploration=0.0)

    for player in state.players:
        player.hand = []
        player.deck = []
        player.discard = []
    state.players[0].command = 10
    state.players[1].command = 10

    target = Position(Front.FIRST, Rank.FRONT)

    incomplete = state.clone()
    incomplete_slot = incomplete.slot(0, target)
    incomplete_slot.force = "those-who-came-back"
    incomplete_slot.name = "namar"
    # Equalize current Strength with the complete comparison state so the
    # difference is the Named Formation rule, not raw Strength.
    incomplete_slot.temporary_strength = 2

    complete = state.clone()
    complete_slot = complete.slot(0, target)
    complete_slot.force = "those-who-came-back"
    complete_slot.bond = "held-fast"
    complete_slot.name = "namar"

    assert (
        engine.position_strength(incomplete, 0, target)
        == engine.position_strength(complete, 0, target)
    )
    assert agent.evaluate(engine, complete, 0) > agent.evaluate(
        engine,
        incomplete,
        0,
    )


def test_heuristic_penalizes_rear_named_formation_that_would_be_driven_off() -> None:
    engine, state = engine_and_state()
    agent = HeuristicAgent(seed=12, exploration=0.0)

    for player in state.players:
        player.hand = []
        player.deck = []
        player.discard = []
    state.players[0].command = 10
    state.players[1].command = 10

    front_position = Position(Front.FIRST, Rank.FRONT)
    rear_position = Position(Front.FIRST, Rank.REAR)

    def named_at(test_state, position):
        slot = test_state.slot(0, position)
        slot.force = "those-who-came-back"
        slot.bond = "held-fast"
        slot.name = "namar"

    frontline = state.clone()
    named_at(frontline, front_position)
    enemy = frontline.slot(1, front_position)
    enemy.force = "the-fifty-men"
    enemy.temporary_strength = 20

    rear = state.clone()
    named_at(rear, rear_position)
    enemy = rear.slot(1, front_position)
    enemy.force = "the-fifty-men"
    enemy.temporary_strength = 20

    assert (
        engine.front_strength(frontline, 0, Front.FIRST)
        == engine.front_strength(rear, 0, Front.FIRST)
    )
    assert agent.evaluate(engine, frontline, 0) > agent.evaluate(
        engine,
        rear,
        0,
    )


def test_heuristic_accounts_for_projected_command_collapse_after_recovery() -> None:
    engine, state = engine_and_state()
    agent = HeuristicAgent(seed=13, exploration=0.0)

    for player in state.players:
        player.hand = []
        player.deck = []
        player.discard = []
    state.battle = 7
    state.players[0].command = 4
    state.players[1].command = 6

    safe = state.clone()
    collapse_risk = state.clone()
    enemy = collapse_risk.slot(
        1,
        Position(Front.FIRST, Rank.FRONT),
    )
    enemy.force = "the-fifty-men"

    safe_value = agent.evaluate(engine, safe, 0)
    collapse_value = agent.evaluate(engine, collapse_risk, 0)

    # Battle VII recovers 1 Command. With no lost Front, player 0 projects to
    # 5 and avoids Collapse. Losing one Front projects to 4 vs 7 and loses if
    # the Battle ended in the current position.
    assert safe_value - collapse_value > 20.0


def test_heuristic_prefers_strength_that_changes_a_front_over_overcommitment() -> None:
    engine, state = engine_and_state()
    agent = HeuristicAgent(seed=14, exploration=0.0)

    for player in state.players:
        player.hand = []
        player.deck = []
        player.discard = []
    state.players[0].command = 10
    state.players[1].command = 10

    contested = state.clone()
    contested.slot(
        0,
        Position(Front.FIRST, Rank.FRONT),
    ).force = "those-who-came-back"
    contested.slot(
        1,
        Position(Front.FIRST, Rank.FRONT),
    ).force = "those-who-came-back"
    contested_gain = contested.clone()
    contested_gain.slot(
        0,
        Position(Front.FIRST, Rank.FRONT),
    ).temporary_strength += 2

    safe = state.clone()
    safe_slot = safe.slot(
        0,
        Position(Front.FIRST, Rank.FRONT),
    )
    safe_slot.force = "those-who-came-back"
    safe_slot.temporary_strength = 3  # margin 6
    safe_gain = safe.clone()
    safe_gain.slot(
        0,
        Position(Front.FIRST, Rank.FRONT),
    ).temporary_strength += 2

    contested_delta = (
        agent.evaluate(engine, contested_gain, 0)
        - agent.evaluate(engine, contested, 0)
    )
    safe_delta = (
        agent.evaluate(engine, safe_gain, 0)
        - agent.evaluate(engine, safe, 0)
    )

    assert contested_delta > safe_delta

