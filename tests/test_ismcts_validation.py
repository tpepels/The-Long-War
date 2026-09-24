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
