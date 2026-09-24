from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from longwar.agents.ismcts_agent import ISMCTSAgent
from longwar.belief import BeliefSampler, DeckHypothesis, HypothesisDeckPrior
from longwar.cards import load_card_file
from longwar.game import GameEngine
from longwar.rules import GameRules

fast_search = pytest.importorskip("longwar._fast_search")
FastEngine = fast_search.FastEngine
NativeHeuristicEvaluator = fast_search.NativeHeuristicEvaluator
ismcts_search = fast_search.ismcts_search

ROOT = Path(__file__).resolve().parents[1]
CARD_FILE = ROOT / "cards" / "cards.json"
DECK_FILE = ROOT / "decks" / "reference.json"


def setup():
    data = load_card_file(CARD_FILE)
    deck = json.loads(DECK_FILE.read_text(encoding="utf-8"))["cards"]
    engine = GameEngine(data, rules=GameRules.standard())
    priors = (
        HypothesisDeckPrior(
            engine,
            [DeckHypothesis(tuple(deck), label="a")],
        ),
        HypothesisDeckPrior(
            engine,
            [DeckHypothesis(tuple(deck), label="b")],
        ),
    )
    return engine, deck, priors


def test_cython_ismcts_returns_legal_action() -> None:
    engine, deck, priors = setup()
    state = engine.new_game(deck, deck, seed=8101, first_player=0)
    legal = engine.legal_actions(state)

    agent = ISMCTSAgent(
        engine,
        8102,
        priors=priors,
        belief_samples=4,
        iterations=200,
        rollout_depth=6,
        tree_depth_limit=24,
    )
    action = agent.choose(engine, state)

    assert action in legal
    assert agent.last_decision["policy_source"] == "ismcts"
    assert agent.last_decision["search_backend_detail"] == "packed-ismcts"
    assert agent.last_decision["ismcts_iterations"] == 200
    assert agent.last_decision["ismcts_root_total_visits"] == 200
    assert (
        0 < agent.last_decision["ismcts_selected_action_visits"] <= 200
    )
    assert agent.last_decision["ismcts_tree_nodes"] > 0
    assert (
        agent.last_decision["ismcts_rollouts_stopped_terminal"]
        + agent.last_decision["ismcts_rollouts_stopped_battle_boundary"]
        + agent.last_decision["ismcts_rollouts_stopped_depth"]
        == 200
    )
    assert agent.last_decision["ismcts_rollout_actions"] >= 0


def test_root_belief_samples_share_information_set() -> None:
    engine, deck, priors = setup()
    state = engine.new_game(deck, deck, seed=8110, first_player=0)
    belief = BeliefSampler(engine, priors=priors)
    fast = FastEngine(engine)

    sampled_a = belief.sample(state, 0, random.Random(8111))
    sampled_b = belief.sample(state, 0, random.Random(8112))
    packed_a = fast.from_game_state(sampled_a)
    packed_b = fast.from_game_state(sampled_b)

    # Opponent hidden cards/deck order may differ, but root player cannot
    # distinguish those determinizations.
    assert fast.information_key(packed_a, 0) == fast.information_key(
        packed_b,
        0,
    )


def test_information_key_distinguishes_public_resource_state() -> None:
    engine, deck, _priors = setup()
    fast = FastEngine(engine)
    base = engine.new_game(deck, deck, seed=8120, first_player=0)

    def key(state):
        return fast.information_key(fast.from_game_state(state), 0)

    baseline = key(base)

    changed = base.clone()
    changed.players[0].command -= 1
    assert key(changed) != baseline

    changed = base.clone()
    changed.operations_this_battle[0] += 1
    assert key(changed) != baseline

    changed = base.clone()
    changed.players[0].free_cycle = True
    assert key(changed) != baseline

    changed = base.clone()
    changed.cleanup_pending = True
    changed.cleanup_next_starter = 0
    assert key(changed) != baseline


def test_ismcts_rng_accepts_full_uint64_seed_range() -> None:
    engine, deck, _priors = setup()
    state = engine.new_game(deck, deck, seed=8130, first_player=0)
    fast = FastEngine(engine)
    evaluator = NativeHeuristicEvaluator(fast)
    packed = fast.from_game_state(state)

    result = ismcts_search(
        fast,
        evaluator,
        [packed],
        0,
        iterations=8,
        rollout_depth=2,
        tree_depth_limit=8,
        seed=0xFFFFFFFFFFFFFFFF,
    )

    assert result["iterations"] == 8
    assert result["root_total_visits"] == 8
    assert 0 < result["selected_action_visits"] <= 8


def test_native_information_hash_matches_information_identity() -> None:
    engine, deck, priors = setup()
    state = engine.new_game(deck, deck, seed=8140, first_player=0)
    belief = BeliefSampler(engine, priors=priors)
    fast = FastEngine(engine)

    sample_a = fast.from_game_state(
        belief.sample(state, 0, random.Random(8141))
    )
    sample_b = fast.from_game_state(
        belief.sample(state, 0, random.Random(8142))
    )
    assert fast.information_hash(sample_a, 0) == fast.information_hash(
        sample_b,
        0,
    )

    changed = state.clone()
    changed.players[0].command -= 1
    changed_fast = fast.from_game_state(changed)
    assert fast.information_hash(changed_fast, 0) != fast.information_hash(
        sample_a,
        0,
    )


@pytest.mark.parametrize("policy", ("greedy", "cheap", "random"))
def test_ismcts_rollout_policies_return_legal_action(policy: str) -> None:
    engine, deck, priors = setup()
    state = engine.new_game(deck, deck, seed=8150, first_player=0)
    legal = engine.legal_actions(state)
    agent = ISMCTSAgent(
        engine,
        8151,
        priors=priors,
        belief_samples=2,
        iterations=40,
        rollout_depth=2,
        rollout_policy=policy,
    )
    assert agent.choose(engine, state) in legal
    assert agent.last_decision["ismcts_rollout_policy"] == policy


def test_ismcts_wall_clock_budget_reports_actual_work() -> None:
    engine, deck, priors = setup()
    state = engine.new_game(deck, deck, seed=8160, first_player=0)
    agent = ISMCTSAgent(
        engine,
        8161,
        priors=priors,
        belief_samples=2,
        iterations=40,
        time_budget_seconds=0.01,
        rollout_depth=2,
        tree_depth_limit=16,
        exploration=0.3,
    )

    action = agent.choose(engine, state)
    info = agent.last_decision

    assert action in engine.legal_actions(state)
    assert info["search_time_budget_seconds"] == pytest.approx(0.01)
    assert info["search_timed_out"] is True
    assert int(info["ismcts_iterations"]) >= 256
    assert int(info["search_nodes"]) == int(info["ismcts_iterations"])
    assert float(info["decision_seconds"]) > 0.0
