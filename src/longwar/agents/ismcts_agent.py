from __future__ import annotations

from math import isfinite
from time import perf_counter

from ..belief import BeliefSampler, DeckPrior
from ..game.actions import Action, action_key
from ..game.engine import GameEngine
from ..game.model import GameState
from ..heuristics import opening_mulligan_indices

DEFAULT_ISMCTS_EXPLORATION = 0.3


try:
    from .._fast_search import (
        FastEngine,
        ISMCTSTree,
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
        time_budget_seconds: float | None = None,
        rollout_depth: int = 5,
        tree_depth_limit: int = 96,
        exploration: float = DEFAULT_ISMCTS_EXPLORATION,
        progressive_widening: float = 0.0,
        reuse_tree: bool = True,
        max_tree_nodes: int | None = None,
        rollout_epsilon: float = 0.12,
        rollout_policy: str = "cheap",
        leaf_scale: float = 100.0,
    ):
        if belief_samples <= 0:
            raise ValueError("belief_samples must be positive")
        if iterations <= 0:
            raise ValueError("iterations must be positive")
        if (
            time_budget_seconds is not None
            and (not isfinite(time_budget_seconds) or time_budget_seconds <= 0.0)
        ):
            raise ValueError("time_budget_seconds must be finite and positive")
        if rollout_depth < 0:
            raise ValueError("rollout_depth must be non-negative")
        if not 1 <= tree_depth_limit <= 256:
            raise ValueError("tree_depth_limit must be between 1 and 256")
        if not isfinite(exploration) or exploration < 0:
            raise ValueError("exploration must be non-negative")
        if not isfinite(progressive_widening) or progressive_widening < 0:
            raise ValueError("progressive_widening must be non-negative")
        if not 0.0 <= rollout_epsilon <= 1.0:
            raise ValueError("rollout_epsilon must be between 0 and 1")
        if rollout_policy not in {"greedy", "cheap", "random"}:
            raise ValueError(
                "rollout_policy must be greedy, cheap, or random"
            )
        if not isfinite(leaf_scale) or leaf_scale <= 0:
            raise ValueError("leaf_scale must be positive")

        import random

        self.rng = random.Random(seed)
        self.seed = seed
        self.belief = BeliefSampler(engine, priors=priors)
        self.belief_samples = belief_samples
        self.iterations = iterations
        self.time_budget_seconds = time_budget_seconds
        self.rollout_depth = rollout_depth
        self.tree_depth_limit = tree_depth_limit
        self.exploration = exploration
        self.progressive_widening = progressive_widening
        self.reuse_tree = reuse_tree
        self.max_tree_nodes = max_tree_nodes
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
        self._tree = ISMCTSTree(iterations, max_nodes=max_tree_nodes) if reuse_tree else None
        self.last_decision: dict[str, float | int | str | bool] = {}

    def reset_tree(self) -> None:
        """Discard accumulated search statistics before starting a new game."""
        self._tree = (
            ISMCTSTree(self.iterations, max_nodes=self.max_tree_nodes)
            if self.reuse_tree else None
        )

    def choose_mulligan(
        self,
        engine: GameEngine,
        hand: list[str],
    ) -> tuple[int, ...]:
        self.reset_tree()
        return opening_mulligan_indices(engine, hand)

    def choose(self, engine: GameEngine, state: GameState) -> Action:
        decision_started = perf_counter()
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
                "search_time_budget_seconds": self.time_budget_seconds,
                "decision_seconds": perf_counter() - decision_started,
                "completed_depth": 0,
                "search_backend": "cython",
                "search_backend_detail": "packed-ismcts",
                "evaluated_candidates": 1,
                "ismcts_iterations": 0,
                "ismcts_tree_nodes": (
                    self._tree.size() if self._tree is not None else 0
                ),
                "ismcts_tree_nodes_before": (
                    self._tree.size() if self._tree is not None else 0
                ),
                "ismcts_tree_nodes_added": 0,
                "ismcts_tree_nodes_discarded": 0,
                "ismcts_tree_reset_reason": "none",
                "ismcts_tree_capacity_cutoffs": 0,
                "ismcts_root_total_visits": 0,
                "ismcts_root_total_visits_lifetime": 0,
                "ismcts_root_prior_visits": 0,
                "ismcts_root_reused": False,
                "ismcts_selected_action_visits": 0,
                "ismcts_selected_action_visits_lifetime": 0,
                "ismcts_selected_action_prior_visits": 0,
                "ismcts_rollouts_stopped_terminal": 0,
                "ismcts_rollouts_stopped_battle_boundary": 0,
                "ismcts_rollouts_stopped_depth": 0,
                "ismcts_rollout_actions": 0,
                "ismcts_rollout_policy": self.rollout_policy,
                "ismcts_progressive_widening": self.progressive_widening,
                "ismcts_tree_reuse_enabled": self.reuse_tree,
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

        elapsed_setup = perf_counter() - decision_started
        remaining_time = (
            max(1.0e-6, self.time_budget_seconds - elapsed_setup)
            if self.time_budget_seconds is not None
            else 0.0
        )
        effective_iteration_limit = (
            max(self.iterations, 100_000_000)
            if self.time_budget_seconds is not None
            else self.iterations
        )
        search_tree = self._tree
        if search_tree is None:
            search_tree = ISMCTSTree(
                self.iterations,
                max_nodes=self.max_tree_nodes,
            )

        result = ismcts_search(
            self.fast_engine,
            self.evaluator,
            packed_states,
            root_player,
            tree=search_tree,
            reuse_context=self.belief.reuse_context(state, root_player),
            iterations=effective_iteration_limit,
            rollout_depth=self.rollout_depth,
            tree_depth_limit=self.tree_depth_limit,
            exploration=self.exploration,
            progressive_widening=self.progressive_widening,
            rollout_epsilon=self.rollout_epsilon,
            rollout_policy=self._rollout_policy_code,
            leaf_scale=self.leaf_scale,
            time_limit_seconds=remaining_time,
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
            "search_nodes": int(result["iterations"]),
            "search_budget": self.iterations,
            "search_iteration_limit_effective": effective_iteration_limit,
            "search_time_budget_seconds": self.time_budget_seconds,
            "search_timed_out": bool(result["timed_out"]),
            "decision_seconds": perf_counter() - decision_started,
            "search_backend": "cython",
            "search_backend_detail": "packed-ismcts",
            "evaluated_candidates": len(legal),
            "ismcts_iterations": int(result["iterations"]),
            "ismcts_tree_nodes": int(result["tree_nodes"]),
            "ismcts_tree_nodes_before": int(result["tree_nodes_before"]),
            "ismcts_tree_nodes_added": int(result["tree_nodes_added"]),
            "ismcts_tree_nodes_discarded": int(result["tree_nodes_discarded"]),
            "ismcts_tree_reset_reason": str(result["tree_reset_reason"]),
            "ismcts_tree_capacity_cutoffs": int(result["tree_capacity_cutoffs"]),
            "ismcts_tree_max_nodes": int(result["tree_max_nodes"]),
            "ismcts_root_total_visits": int(result["root_new_visits"]),
            "ismcts_root_total_visits_lifetime": int(
                result["root_total_visits"]
            ),
            "ismcts_root_prior_visits": int(
                result["root_total_visits_before"]
            ),
            "ismcts_root_reused": bool(result["root_reused"]),
            "ismcts_selected_action_visits": int(
                result["selected_action_new_visits"]
            ),
            "ismcts_selected_action_visits_lifetime": int(
                result["selected_action_visits"]
            ),
            "ismcts_selected_action_prior_visits": int(
                result["selected_action_visits_before"]
            ),
            "ismcts_rollouts_stopped_terminal": int(
                result["rollouts_stopped_terminal"]
            ),
            "ismcts_rollouts_stopped_battle_boundary": int(
                result["rollouts_stopped_battle_boundary"]
            ),
            "ismcts_rollouts_stopped_depth": int(
                result["rollouts_stopped_depth"]
            ),
            "ismcts_rollout_actions": int(result["rollout_actions"]),
            "ismcts_root_value": score,
            "ismcts_rollout_policy": self.rollout_policy,
            "ismcts_progressive_widening": self.progressive_widening,
            "ismcts_tree_reuse_enabled": self.reuse_tree,
            "ismcts_progressive_widening_alpha": float(
                result["progressive_widening_alpha"]
            ),
            "ismcts_tree_storage": str(result["tree_storage"]),
        }
        return selected
