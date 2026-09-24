from __future__ import annotations

import json
import math
import random
from pathlib import Path

import pytest

from longwar.agents.ismcts_agent import ISMCTSAgent
from longwar.belief import BeliefSampler, DeckHypothesis, HypothesisDeckPrior
from longwar.cards import load_card_file
from longwar.game import GameEngine, Pass, Phase
from longwar.game.actions import action_key
from longwar.rules import GameRules

fast_search = pytest.importorskip("longwar._fast_search")
FastEngine = fast_search.FastEngine
ISMCTSTree = fast_search.ISMCTSTree
NativeHeuristicEvaluator = fast_search.NativeHeuristicEvaluator
ismcts_search = fast_search.ismcts_search

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.algorithm

MASK64 = (1 << 64) - 1


def _force_fixture(rules: GameRules):
    data = load_card_file(
        ROOT / "cards" / "experiments" / "force-draw-cards.json"
    )
    deck = json.loads(
        (
            ROOT
            / "decks"
            / "experiments"
            / "force-rich-34-reference.json"
        ).read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(data, rules=rules)
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


def _standard_fixture():
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "reference.json").read_text(encoding="utf-8")
    )["cards"]
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


def _pass_only_standard_state(
    *,
    victories: tuple[int, int] = (0, 0),
):
    engine, deck, _priors = _standard_fixture()
    state = engine.new_game(deck, deck, seed=9275, first_player=0)
    for index, player in enumerate(state.players):
        player.hand.clear()
        player.deck.clear()
        player.discard.clear()
        player.victories = victories[index]
    assert engine.legal_actions(state) == [Pass()]
    return engine, state


def _hash_information_key(key: bytes) -> tuple[int, int]:
    """Pure-Python oracle for the native canonical information hash."""
    a = 0xCBF29CE484222325
    b = 0x84222325CBF29CE4
    for value in key:
        a ^= value
        a = (a * 0x100000001B3) & MASK64
        b ^= value
        b = (b * 0xC2B2AE3D27D4EB4F) & MASK64
        b ^= b >> 29
    return a, b


def _search(
    fast,
    evaluator,
    packed_states,
    root_player: int,
    *,
    iterations: int,
    seed: int,
    rollout_depth: int = 2,
    tree_depth_limit: int = 24,
    exploration: float = 2 ** 0.5,
    progressive_widening: float = 0.0,
    rollout_policy: int = 1,
):
    return ismcts_search(
        fast,
        evaluator,
        packed_states,
        root_player,
        iterations=iterations,
        rollout_depth=rollout_depth,
        tree_depth_limit=tree_depth_limit,
        exploration=exploration,
        progressive_widening=progressive_widening,
        rollout_epsilon=0.12,
        rollout_policy=rollout_policy,
        seed=seed,
    )


def test_native_hash_is_exact_hash_of_canonical_information_encoding() -> None:
    engine, deck, _priors = _force_fixture(
        GameRules.force_candidate("automatic")
    )
    fast = FastEngine(engine)
    rng = random.Random(9201)
    state = engine.new_game(deck, deck, seed=9202, first_player=0)
    packed = fast.from_game_state(state)

    checked = 0
    for _ in range(50):
        for player in (0, 1):
            key = fast.information_key(packed, player)
            assert fast.information_hash(packed, player) == (
                _hash_information_key(key)
            )
            checked += 1

        if state.phase.value == "complete":
            break
        action = rng.choice(engine.legal_actions(state))
        target = action_key(action)
        native_action = next(
            candidate
            for candidate in fast.legal_actions(packed)
            if fast.action_key(candidate) == target
        )
        engine.apply(state, action, validate=False)
        fast.apply(packed, native_action)

    assert checked >= 20


def test_hidden_determinizations_share_root_information_identity() -> None:
    engine, deck, priors = _force_fixture(
        GameRules.force_candidate("automatic")
    )
    state = engine.new_game(deck, deck, seed=9210, first_player=0)
    belief = BeliefSampler(engine, priors=priors)
    fast = FastEngine(engine)
    rng = random.Random(9211)

    packed = [
        fast.from_game_state(belief.sample(state, 0, rng))
        for _ in range(12)
    ]
    keys = {fast.information_key(sample, 0) for sample in packed}
    hashes = {fast.information_hash(sample, 0) for sample in packed}

    assert len(keys) == 1
    assert len(hashes) == 1


def test_ismcts_is_bit_reproducible_for_fixed_beliefs_and_seed() -> None:
    engine, deck, priors = _force_fixture(
        GameRules.force_candidate("automatic")
    )
    state = engine.new_game(deck, deck, seed=9220, first_player=0)
    belief = BeliefSampler(engine, priors=priors)
    fast = FastEngine(engine)
    evaluator = NativeHeuristicEvaluator(fast)
    rng = random.Random(9221)
    packed = [
        fast.from_game_state(belief.sample(state, 0, rng))
        for _ in range(6)
    ]

    first = _search(
        fast,
        evaluator,
        packed,
        0,
        iterations=300,
        seed=0x123456789ABCDEF0,
    )
    second = _search(
        fast,
        evaluator,
        packed,
        0,
        iterations=300,
        seed=0x123456789ABCDEF0,
    )

    assert first["action"] == second["action"]
    assert first["root_stats"] == second["root_stats"]
    assert first["tree_nodes"] == second["tree_nodes"]
    assert first["max_tree_depth"] == second["max_tree_depth"]


def test_root_visit_and_availability_accounting_is_conserved() -> None:
    engine, deck, _priors = _force_fixture(
        GameRules.force_candidate("automatic")
    )
    state = engine.new_game(deck, deck, seed=9230, first_player=0)
    fast = FastEngine(engine)
    evaluator = NativeHeuristicEvaluator(fast)
    packed = fast.from_game_state(state)
    iterations = 400

    result = _search(
        fast,
        evaluator,
        [packed],
        0,
        iterations=iterations,
        seed=9231,
        rollout_depth=1,
    )

    stats = result["root_stats"]
    assert result["root_total_visits"] == iterations
    assert sum(int(row["visits"]) for row in stats) == iterations
    assert all(int(row["availability"]) == iterations for row in stats)
    assert all(
        0 <= int(row["visits"]) <= int(row["availability"])
        for row in stats
    )

    native_actions = {
        fast.action_key(row["action"])
        for row in stats
    }
    public_actions = {
        action_key(action)
        for action in engine.legal_actions(state)
    }
    assert native_actions == public_actions


def test_first_expansion_visits_every_root_action_once() -> None:
    engine, deck, _priors = _force_fixture(
        GameRules.force_candidate("automatic")
    )
    state = engine.new_game(deck, deck, seed=9240, first_player=0)
    fast = FastEngine(engine)
    evaluator = NativeHeuristicEvaluator(fast)
    packed = fast.from_game_state(state)
    legal_count = len(fast.legal_actions(packed))

    result = _search(
        fast,
        evaluator,
        [packed],
        0,
        iterations=legal_count,
        seed=9241,
        rollout_depth=0,
        tree_depth_limit=1,
        exploration=0.0,
        rollout_policy=2,
    )

    assert result["root_total_visits"] == legal_count
    assert all(int(row["visits"]) == 1 for row in result["root_stats"])


def test_persistent_tree_reroots_to_previously_explored_information_set() -> None:
    engine, state = _pass_only_standard_state()
    fast = FastEngine(engine)
    evaluator = NativeHeuristicEvaluator(fast)
    tree = ISMCTSTree(128)
    packed = fast.from_game_state(state)

    first = ismcts_search(
        fast,
        evaluator,
        [packed],
        0,
        tree=tree,
        iterations=16,
        rollout_depth=0,
        tree_depth_limit=4,
        exploration=0.5,
        seed=9284,
    )
    assert first["root_reused"] is False
    assert first["root_total_visits_before"] == 0
    assert first["root_new_visits"] == 16
    assert first["tree_nodes_before"] == 0
    assert tree.size() == first["tree_nodes"]

    engine.apply(state, Pass())
    assert state.phase is Phase.BATTLE
    assert state.active_player == 1
    next_packed = fast.from_game_state(state)

    second = ismcts_search(
        fast,
        evaluator,
        [next_packed],
        1,
        tree=tree,
        iterations=12,
        rollout_depth=0,
        tree_depth_limit=4,
        exploration=0.5,
        seed=9285,
    )

    assert second["root_reused"] is True
    assert second["root_total_visits_before"] > 0
    assert second["root_new_visits"] == 12
    assert second["root_total_visits"] == (
        second["root_total_visits_before"] + 12
    )
    assert second["tree_nodes_before"] == first["tree_nodes"]
    assert second["tree_nodes"] >= second["tree_nodes_before"]
    assert sum(int(row["new_visits"]) for row in second["root_stats"]) == 12


def test_progressive_widening_limits_initial_root_breadth() -> None:
    engine, deck, _priors = _force_fixture(
        GameRules.force_candidate("automatic")
    )
    state = engine.new_game(deck, deck, seed=9245, first_player=0)
    fast = FastEngine(engine)
    evaluator = NativeHeuristicEvaluator(fast)
    packed = fast.from_game_state(state)
    assert len(fast.legal_actions(packed)) >= 4

    result = _search(
        fast,
        evaluator,
        [packed],
        0,
        iterations=16,
        seed=9246,
        rollout_depth=0,
        tree_depth_limit=1,
        exploration=0.0,
        progressive_widening=1.0,
        rollout_policy=2,
    )

    visited = [
        row for row in result["root_stats"] if int(row["visits"]) > 0
    ]
    assert len(visited) == 4
    assert result["progressive_widening"] == pytest.approx(1.0)
    assert result["progressive_widening_alpha"] == pytest.approx(0.5)


def test_one_ply_ismcts_matches_strategic_leaf_oracle() -> None:
    engine, deck, _priors = _force_fixture(
        GameRules.force_candidate("automatic")
    )
    state = engine.new_game(deck, deck, seed=9250, first_player=0)
    fast = FastEngine(engine)
    evaluator = NativeHeuristicEvaluator(fast)
    packed = fast.from_game_state(state)
    legal = fast.legal_actions(packed)

    scores: dict[int, float] = {}
    for action in legal:
        child = fast.next_state(packed, action)
        scores[action] = evaluator.strategic_evaluate(child, 0)

    best_score = max(scores.values())
    best_actions = {
        action
        for action, score in scores.items()
        if abs(score - best_score) <= 1e-12
    }

    result = ismcts_search(
        fast,
        evaluator,
        [packed],
        0,
        iterations=len(legal) + 80,
        rollout_depth=0,
        tree_depth_limit=1,
        exploration=0.0,
        rollout_epsilon=0.0,
        rollout_policy=2,
        leaf_scale=10_000.0,
        seed=9251,
    )

    assert result["action"] in best_actions


def test_rollout_stops_at_battle_boundary_and_uses_boundary_value() -> None:
    engine, state = _pass_only_standard_state()
    fast = FastEngine(engine)
    evaluator = NativeHeuristicEvaluator(fast)
    packed = fast.from_game_state(state)

    boundary = state.clone()
    engine.apply(boundary, Pass())
    engine.apply(boundary, Pass())
    assert boundary.battle == 2
    assert boundary.phase is Phase.CHOOSE_FIRST

    boundary_packed = fast.from_game_state(boundary)
    leaf_scale = 100.0
    expected = math.tanh(
        evaluator.battle_boundary_evaluate(boundary_packed, 0)
        / leaf_scale
    )
    iterations = 12
    result = ismcts_search(
        fast,
        evaluator,
        [packed],
        0,
        iterations=iterations,
        rollout_depth=5,
        tree_depth_limit=1,
        exploration=0.0,
        rollout_epsilon=0.0,
        rollout_policy=2,
        leaf_scale=leaf_scale,
        seed=9280,
    )

    assert result["rollouts_stopped_terminal"] == 0
    assert result["rollouts_stopped_battle_boundary"] == iterations
    assert result["rollouts_stopped_depth"] == 0
    assert result["rollout_actions"] == iterations
    assert result["mean_value"] == pytest.approx(expected)


def test_terminal_game_completion_keeps_exact_terminal_utility() -> None:
    engine, state = _pass_only_standard_state(victories=(1, 0))
    fast = FastEngine(engine)
    evaluator = NativeHeuristicEvaluator(fast)
    packed = fast.from_game_state(state)
    iterations = 8

    result = ismcts_search(
        fast,
        evaluator,
        [packed],
        0,
        iterations=iterations,
        rollout_depth=5,
        tree_depth_limit=1,
        exploration=0.0,
        rollout_epsilon=0.0,
        rollout_policy=2,
        seed=9281,
    )

    assert result["rollouts_stopped_terminal"] == iterations
    assert result["rollouts_stopped_battle_boundary"] == 0
    assert result["rollouts_stopped_depth"] == 0
    assert result["rollout_actions"] == iterations
    assert result["mean_value"] == pytest.approx(1.0)


def test_final_tree_step_boundary_does_not_start_next_battle_rollout() -> None:
    engine, state = _pass_only_standard_state()
    engine.apply(state, Pass())
    assert state.battle == 1
    assert state.phase is Phase.BATTLE
    assert state.active_player == 1
    assert engine.legal_actions(state) == [Pass()]

    fast = FastEngine(engine)
    evaluator = NativeHeuristicEvaluator(fast)
    packed = fast.from_game_state(state)
    iterations = 6
    result = ismcts_search(
        fast,
        evaluator,
        [packed],
        1,
        iterations=iterations,
        rollout_depth=5,
        tree_depth_limit=1,
        exploration=0.0,
        rollout_epsilon=0.0,
        rollout_policy=2,
        seed=9282,
    )

    assert result["rollouts_stopped_battle_boundary"] == iterations
    assert result["rollouts_stopped_terminal"] == 0
    assert result["rollouts_stopped_depth"] == 0
    assert result["rollout_actions"] == 0


def test_boundary_evaluator_projects_pending_cleanup() -> None:
    engine, deck, _priors = _force_fixture(
        GameRules.force_experiment("auto-discard7")
    )
    state = engine.new_game(deck, deck, seed=9283, first_player=0)
    state.battle = 2
    state.cleanup_pending = True
    state.players[0].hand[:] = ["the-fifty-men"] * 8
    state.players[1].hand[:] = ["the-fifty-men"] * 7

    projected = state.clone()
    projected.players[0].hand.pop()
    projected.players[0].discard.append("the-fifty-men")

    fast = FastEngine(engine)
    evaluator = NativeHeuristicEvaluator(fast)
    packed = fast.from_game_state(state)
    projected_packed = fast.from_game_state(projected)

    assert evaluator.battle_boundary_evaluate(
        packed,
        0,
    ) == pytest.approx(
        evaluator.strategic_evaluate(projected_packed, 0)
    )


def test_boundary_evaluator_rewards_next_battle_readiness() -> None:
    engine, state = _pass_only_standard_state()
    engine.apply(state, Pass())
    engine.apply(state, Pass())
    assert state.battle == 2

    ready = state.clone()
    poor = state.clone()
    ready.players[0].hand[:] = [
        "the-fifty-men",
        "followed",
        "namar",
    ]
    poor.players[0].hand[:] = [
        "the-story-is-false",
        "he-never-came",
        "they-chose-another",
    ]

    fast = FastEngine(engine)
    evaluator = NativeHeuristicEvaluator(fast)
    ready_packed = fast.from_game_state(ready)
    poor_packed = fast.from_game_state(poor)

    ready_value = evaluator.battle_boundary_evaluate(ready_packed, 0)
    poor_value = evaluator.battle_boundary_evaluate(poor_packed, 0)

    assert ready_value > poor_value
    assert ready_value == pytest.approx(
        evaluator.strategic_evaluate(ready_packed, 0)
    )
    assert poor_value == pytest.approx(
        evaluator.strategic_evaluate(poor_packed, 0)
    )


@pytest.mark.parametrize(
    "name,rules",
    (
        ("automatic", GameRules.force_candidate("automatic")),
        ("paid", GameRules.force_candidate("paid")),
        ("control", GameRules.force_experiment("control")),
        ("paid-free", GameRules.force_experiment("paid-free")),
        ("auto-discard9", GameRules.force_experiment("auto-discard9")),
        ("auto-discard7", GameRules.force_experiment("auto-discard7")),
        ("auto-cap10", GameRules.force_experiment("auto-cap10")),
    ),
)
def test_same_ismcts_agent_runs_across_force_rule_profiles(
    name: str,
    rules: GameRules,
) -> None:
    engine, deck, priors = _force_fixture(rules)
    state = engine.new_game(deck, deck, seed=9260, first_player=0)
    legal = engine.legal_actions(state)
    agent = ISMCTSAgent(
        engine,
        9261,
        priors=priors,
        belief_samples=2,
        iterations=32,
        rollout_depth=1,
        rollout_policy="cheap",
    )

    assert agent.choose(engine, state) in legal, name


def test_same_ismcts_agent_runs_under_standard_rules() -> None:
    engine, deck, priors = _standard_fixture()
    state = engine.new_game(deck, deck, seed=9270, first_player=0)
    legal = engine.legal_actions(state)
    agent = ISMCTSAgent(
        engine,
        9271,
        priors=priors,
        belief_samples=2,
        iterations=32,
        rollout_depth=1,
        rollout_policy="cheap",
    )

    assert agent.choose(engine, state) in legal


@pytest.mark.parametrize(
    "parameter,value",
    [
        ("exploration", float("nan")),
        ("exploration", -1.0),
        ("progressive_widening", float("inf")),
        ("rollout_epsilon", 1.1),
        ("rollout_policy", 3),
        ("leaf_scale", float("nan")),
    ],
)
def test_native_search_rejects_invalid_controls(parameter, value) -> None:
    engine, state = _pass_only_standard_state()
    fast = FastEngine(engine)
    with pytest.raises(ValueError):
        ismcts_search(
            fast, NativeHeuristicEvaluator(fast),
            [fast.from_game_state(state)], 0,
            iterations=1, **{parameter: value},
        )


def test_native_search_rejects_incompatible_root_samples() -> None:
    engine, state = _pass_only_standard_state()
    fast = FastEngine(engine)
    evaluator = NativeHeuristicEvaluator(fast)
    packed = fast.from_game_state(state)
    changed = state.clone()
    changed.players[0].victories += 1
    with pytest.raises(ValueError, match="share a root information set"):
        ismcts_search(fast, evaluator, [packed, fast.from_game_state(changed)], 0)
    with pytest.raises(ValueError, match="acting player"):
        ismcts_search(fast, evaluator, [packed], 1)
    with pytest.raises(TypeError, match="FastState"):
        ismcts_search(fast, evaluator, [packed, object()], 0)


def test_persistent_tree_invalidates_values_when_belief_context_changes() -> None:
    engine, state = _pass_only_standard_state()
    fast = FastEngine(engine)
    evaluator = NativeHeuristicEvaluator(fast)
    tree = ISMCTSTree(32)
    packed = fast.from_game_state(state)
    options = dict(tree=tree, iterations=8, rollout_depth=0, tree_depth_limit=4)
    first = ismcts_search(fast, evaluator, [packed], 0, reuse_context=(0,), **options)
    reused = ismcts_search(fast, evaluator, [packed], 0, reuse_context=(0,), **options)
    assert reused["root_reused"] is True
    assert reused["root_total_visits_before"] == first["root_total_visits"]
    assert sum(row["new_visits"] for row in reused["root_stats"]) == 8
    assert all(row["availability"] >= row["visits"] for row in reused["root_stats"])

    changed = ismcts_search(fast, evaluator, [packed], 0, reuse_context=(1,), **options)
    assert changed["root_reused"] is False
    assert changed["root_total_visits_before"] == 0
    assert changed["root_new_visits"] == 8
    assert changed["tree_nodes_discarded"] == reused["tree_nodes"]
    assert changed["tree_reset_reason"] == "context_changed"


def test_persistent_tree_capacity_uses_rollouts_and_resets_for_unseen_root() -> None:
    engine, state = _pass_only_standard_state()
    fast = FastEngine(engine)
    evaluator = NativeHeuristicEvaluator(fast)
    tree = ISMCTSTree(32, max_nodes=1)
    options = dict(tree=tree, iterations=8, rollout_depth=2, tree_depth_limit=4)
    first = ismcts_search(fast, evaluator, [fast.from_game_state(state)], 0, **options)
    assert tree.size() == first["tree_nodes"] == 1
    assert first["tree_capacity_cutoffs"] > 0
    assert first["root_new_visits"] == 8

    engine.apply(state, Pass())
    second = ismcts_search(fast, evaluator, [fast.from_game_state(state)], 1, **options)
    assert tree.size() == second["tree_nodes"] == 1
    assert second["root_new_visits"] == 8
    assert second["tree_reset_reason"] == "capacity_reroot"
    assert second["tree_nodes_discarded"] == 1
    assert second["root_reused"] is False


def test_belief_reuse_context_tracks_observed_evidence_only() -> None:
    engine, deck, priors = _standard_fixture()
    state = engine.new_game(deck, deck, seed=9381, first_player=0)
    belief = BeliefSampler(engine, priors=priors)
    baseline = belief.reuse_context(state, 0)
    for seed in range(6):
        assert belief.reuse_context(belief.sample(state, 0, random.Random(seed)), 0) == baseline

    # Spending a known card adds no hidden evidence for its owner.
    changed = state.clone()
    changed.players[0].discard.append(changed.players[0].hand.pop())
    assert belief.reuse_context(changed, 0) == baseline

    # Drawing a previously unknown card changes the owner's belief context.
    changed = state.clone()
    changed.players[0].hand.append(changed.players[0].deck.pop())
    assert belief.reuse_context(changed, 0) != baseline

    # A public opponent play changes hard evidence even at unchanged zone sizes.
    changed = state.clone()
    changed.players[1].discard.append(changed.players[1].hand.pop())
    assert belief.reuse_context(changed, 0) != baseline
