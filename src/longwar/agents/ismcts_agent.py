from __future__ import annotations

from ..belief import BeliefSampler, DeckPrior
from ..game.actions import Action, action_key
from ..game.engine import GameEngine
from ..game.model import GameState
from ..heuristics import opening_mulligan_indices

try:
    from .._fast_search import (
        FastEngine,
        NativeHeuristicEvaluator,
        ismcts_search,
    )
except ImportError as exc:  # canonical extension is required by normal install
    raise RuntimeError(
        "Cython ISMCTS requires the canonical _fast_search extension; "
        "run python -m pip install -e '.[dev]'"
    ) from exc


class ISMCTSAgent:
    """Root-belief-sampled information-set MCTS.

    Belief construction is deliberately outside the search algorithm. The
    packed Cython implementation owns tree selection, expansion, rollout and
    backpropagation; GameEngine remains the sole rules implementation.
    """

    def __init__(
        self,
        engine: GameEngine,
        seed: int,
        *,
        priors: tuple[DeckPrior, DeckPrior] | None = None,
        belief_samples: int = 16,
        iterations: int = 100_000,
        rollout_depth: int = 5,
        tree_depth_limit: int = 96,
        exploration: float = 2 ** 0.5,
        rollout_epsilon: float = 0.12,
        rollout_policy: str = "cheap",
        leaf_scale: float = 100.0,
    ):
        if belief_samples <= 0:
            raise ValueError("belief_samples must be positive")
        if iterations <= 0:
            raise ValueError("iterations must be positive")
        if rollout_depth < 0:
            raise ValueError("rollout_depth must be non-negative")
        if tree_depth_limit <= 0:
            raise ValueError("tree_depth_limit must be positive")
        if exploration < 0:
            raise ValueError("exploration must be non-negative")
        if not 0.0 <= rollout_epsilon <= 1.0:
            raise ValueError("rollout_epsilon must be between 0 and 1")
        if rollout_policy not in {"greedy", "cheap", "random"}:
            raise ValueError(
                "rollout_policy must be greedy, cheap, or random"
            )
        if leaf_scale <= 0:
            raise ValueError("leaf_scale must be positive")

        import random

        self.rng = random.Random(seed)
        self.seed = seed
        self.belief = BeliefSampler(engine, priors=priors)
        self.belief_samples = belief_samples
        self.iterations = iterations
        self.rollout_depth = rollout_depth
        self.tree_depth_limit = tree_depth_limit
        self.exploration = exploration
        self.rollout_epsilon = rollout_epsilon
        self.rollout_policy = rollout_policy
        self._rollout_policy_code = {
            "greedy": 0,
            "cheap": 1,
            "random": 2,
        }[rollout_policy]
        self.leaf_scale = leaf_scale
        self.fast_engine = FastEngine(engine)
        self.evaluator = NativeHeuristicEvaluator(self.fast_engine)
        self.last_decision: dict[str, float | int | str] = {}

    def choose_mulligan(
        self,
        engine: GameEngine,
        hand: list[str],
    ) -> tuple[int, ...]:
        return opening_mulligan_indices(engine, hand)

    def choose(self, engine: GameEngine, state: GameState) -> Action:
        root_player = state.active_player
        legal = engine.legal_actions(state)
        if len(legal) == 1:
            self.last_decision = {
                "candidate_count": 1,
                "selected_score": 0.0,
                "score_gap": 0.0,
                "selected_action": type(legal[0]).__name__,
                "policy_source": "ismcts",
                "belief_samples": 0,
                "search_nodes": 0,
                "search_budget": self.iterations,
                "completed_depth": 0,
                "search_backend": "cython",
                "search_backend_detail": "packed-ismcts",
                "evaluated_candidates": 1,
                "ismcts_iterations": 0,
                "ismcts_tree_nodes": 0,
                "ismcts_root_total_visits": 0,
                "ismcts_selected_action_visits": 0,
                "ismcts_rollout_policy": self.rollout_policy,
            }
            return legal[0]

        sampled_states = [
            self.belief.sample(state, root_player, self.rng)
            for _ in range(self.belief_samples)
        ]
        packed_states = [
            self.fast_engine.from_game_state(sampled)
            for sampled in sampled_states
        ]

        result = ismcts_search(
            self.fast_engine,
            self.evaluator,
            packed_states,
            root_player,
            iterations=self.iterations,
            rollout_depth=self.rollout_depth,
            tree_depth_limit=self.tree_depth_limit,
            exploration=self.exploration,
            rollout_epsilon=self.rollout_epsilon,
            rollout_policy=self._rollout_policy_code,
            leaf_scale=self.leaf_scale,
            seed=self.rng.getrandbits(64),
        )
        selected_key = self.fast_engine.action_key(result["action"])
        selected = next(
            action
            for action in legal
            if action_key(action) == selected_key
        )

        score = float(result["mean_value"])
        second = float(result["second_mean_value"])
        self.last_decision = {
            "candidate_count": len(legal),
            "selected_score": score,
            "score_gap": score - second,
            "selected_action": type(selected).__name__,
            "policy_source": "ismcts",
            "belief_samples": self.belief_samples,
            "rollout_plies": self.rollout_depth,
            "completed_depth": int(result["max_tree_depth"]),
            "search_nodes": self.iterations,
            "search_budget": self.iterations,
            "search_backend": "cython",
            "search_backend_detail": "packed-ismcts",
            "evaluated_candidates": len(legal),
            "ismcts_iterations": self.iterations,
            "ismcts_tree_nodes": int(result["tree_nodes"]),
            "ismcts_root_total_visits": int(result["root_total_visits"]),
            "ismcts_selected_action_visits": int(
                result["selected_action_visits"]
            ),
            "ismcts_root_value": score,
            "ismcts_rollout_policy": self.rollout_policy,
            "ismcts_tree_storage": str(result["tree_storage"]),
        }
        return selected
