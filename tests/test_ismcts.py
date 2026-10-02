from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from longwar.agents.ismcts_agent import (
    DEFAULT_ISMCTS_POST_BATTLE_ROLLOUT_DEPTH,
    ISMCTSAgent,
)
from longwar.belief import BeliefSampler, DeckHypothesis, HypothesisDeckPrior
from longwar.cards import load_card_file
from longwar.game import Front, GameEngine, Pass, Position, Rank
from longwar.rules import GameRules

fast_search = pytest.importorskip("longwar._fast_search")
FastEngine = fast_search.FastEngine
NativeHeuristicEvaluator = fast_search.NativeHeuristicEvaluator
ismcts_search = fast_search.ismcts_search

ROOT = Path(__file__).resolve().parents[1]
CARD_FILE = ROOT / "cards" / "cards.json"
DECK_FILE = ROOT / "decks" / "mobility-open-bonds.json"


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
    state = engine.new_game(deck, deck, seed=8101, first_player=0, opening_bonus=False)
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
    assert agent.evaluator.sampled_opponent_resources is True
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
    assert agent.last_decision["ismcts_tree_storage"] == "native-hash-node-edge-slab"
    assert agent.last_decision["ismcts_tree_edge_slabs"] > 0
    assert (
        agent.last_decision["ismcts_rollouts_stopped_terminal"]
        + agent.last_decision["ismcts_rollouts_stopped_battle_boundary"]
        + agent.last_decision["ismcts_rollouts_stopped_depth"]
        == 200
    )
    assert agent.last_decision["ismcts_rollout_actions"] >= 0
    assert agent.last_decision["ismcts_anti_decisive_rollout_probes"] >= 0
    assert agent.last_decision["ismcts_anti_decisive_rollout_filtered"] >= 0


def test_root_belief_samples_share_information_set() -> None:
    engine, deck, priors = setup()
    state = engine.new_game(deck, deck, seed=8110, first_player=0, opening_bonus=False)
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
    base = engine.new_game(deck, deck, seed=8120, first_player=0, opening_bonus=False)

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
    changed.hero_used[0] = True
    assert key(changed) != baseline

    changed = base.clone()
    changed.turn_number += 1
    assert key(changed) != baseline

    changed = base.clone()
    changed.pending_draw_discard_for = 0
    assert key(changed) != baseline

    changed = base.clone()
    changed.pass_order = [0]
    changed.players[0].passed = True
    changed.pass_closing_turns_remaining = 3
    assert key(changed) != baseline

    countdown_other = changed.clone()
    countdown_other.pass_closing_turns_remaining = 2
    assert key(countdown_other) != key(changed)


def test_ismcts_rng_accepts_full_uint64_seed_range() -> None:
    engine, deck, _priors = setup()
    state = engine.new_game(deck, deck, seed=8130, first_player=0, opening_bonus=False)
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
    state = engine.new_game(deck, deck, seed=8140, first_player=0, opening_bonus=False)
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


@pytest.mark.parametrize("policy", ("greedy", "cheap", "random", "decisive"))
def test_ismcts_rollout_policies_return_legal_action(policy: str) -> None:
    engine, deck, priors = setup()
    state = engine.new_game(deck, deck, seed=8150, first_player=0, opening_bonus=False)
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


def test_canonical_ismcts_has_next_battle_rollout_horizon() -> None:
    engine, _deck, _priors = setup()
    agent = ISMCTSAgent(engine, 8154, iterations=10, belief_samples=1)
    assert agent.post_battle_rollout_depth == DEFAULT_ISMCTS_POST_BATTLE_ROLLOUT_DEPTH
    assert agent.post_battle_rollout_depth > 0


def test_ismcts_root_guard_allows_legal_midbattle_zero_command_play() -> None:
    engine, deck, priors = setup()
    state = engine.new_game(
        deck,
        deck,
        seed=8155,
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

    packed = engine._native_core().from_game_state(state)
    preserving, filtered = engine._native_heuristic().command_preserving_action_codes(
        packed
    )
    assert preserving
    # Collapse is checked at Battle end, not immediately on reaching zero.
    # The root guard only removes actions that actually resolve the war as a
    # loss on this transition.
    assert filtered == 0

    agent = ISMCTSAgent(
        engine,
        8156,
        priors=priors,
        belief_samples=2,
        iterations=20,
        rollout_depth=2,
    )
    action = agent.choose(engine, state)
    assert action in engine.legal_actions(state)
    assert agent.last_decision["command_guard_applied"] is False


def test_ismcts_wall_clock_budget_reports_actual_work() -> None:
    engine, deck, priors = setup()
    state = engine.new_game(deck, deck, seed=8160, first_player=0, opening_bonus=False)
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


def test_ismcts_release_search_memory_drops_native_tree() -> None:
    engine, deck, priors = setup()
    state = engine.new_game(deck, deck, seed=8170, first_player=0, opening_bonus=False)
    agent = ISMCTSAgent(
        engine,
        8171,
        priors=priors,
        belief_samples=2,
        iterations=40,
        rollout_depth=2,
        reuse_tree=True,
    )

    agent.choose(engine, state)
    assert agent._tree is not None
    assert agent._tree.size() > 0
    assert agent.last_decision

    agent.release_search_memory()

    assert agent._tree is None
    assert agent.last_decision == {}


def test_decisive_rollout_finds_immediate_second_signal_win() -> None:
    data = load_card_file(CARD_FILE)
    deck = json.loads(DECK_FILE.read_text(encoding="utf-8"))["cards"]
    engine = GameEngine(data, rules=GameRules.standard())
    state = engine.new_game(
        deck,
        deck,
        seed=8170,
        first_player=1,
        opening_bonus=False,
    )
    state.operations_this_battle[:] = [1, 1]
    state.players[0].passed = True
    state.pass_order[:] = [0]
    state.active_player = 1
    state.players[0].command = 1
    state.players[1].command = 5

    # Player 1 leads one Front. Move a current-deck Force onto the board so
    # the determinization remains a valid card-conserving state. Avoid Forces
    # with Battle-end contribution choices: this test is about the Pass probe.
    force_id = next(
        card_id
        for card_id in deck
        if engine.cards[card_id].get("type") == "force"
        and int(engine.cards[card_id].get("strength", 0) or 0) > 0
        and "front_resolution"
        not in (engine.cards[card_id].get("design_rules") or {})
    )
    owner = state.players[1]
    for zone in (owner.hand, owner.deck):
        if force_id in zone:
            zone.remove(force_id)
            break
    else:
        raise AssertionError(f"expected {force_id} in player 1 zones")
    state.slot(1, Position(Front.FIRST, Rank.FRONT)).force = force_id

    legal = engine.legal_actions(state)
    assert Pass() in legal

    agent = ISMCTSAgent(
        engine,
        8171,
        belief_samples=2,
        iterations=200,
        rollout_depth=8,
        rollout_policy="decisive",
        reuse_tree=False,
    )
    action = agent.choose(engine, state)

    assert action == Pass()
