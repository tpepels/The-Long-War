from __future__ import annotations

from math import inf
from statistics import mean

from ..algorithms.alpha_beta import AlphaBetaSearch, SearchBudget, SearchLimit
from ..belief import BeliefSampler, DeckPrior
from ..game.actions import Action, Draw, Pass, action_key
from ..game.engine import GameEngine
from ..game.model import GameState
from ..heuristics import StrategicEvaluator
from .heuristic_agent import HeuristicAgent, ScoredAction

try:
    from .._fast_search import (
        FastEngine as _NativeFastEngine,
        NativeHeuristicEvaluator as _NativeHeuristicEvaluator,
        NativeSearchBudget as _NativeSearchBudget,
        NativeSearchLimit as _NativeSearchLimit,
        NativeTranspositionTable as _NativeTranspositionTable,
        native_search_value as _native_search_value,
    )
except ImportError:  # canonical extension is built by normal package install
    _NativeFastEngine = None
    _NativeHeuristicEvaluator = None
    _NativeSearchBudget = None
    _NativeSearchLimit = None
    _NativeTranspositionTable = None
    _native_search_value = None


class StrategicHeuristicAgent(HeuristicAgent):
    """Belief-sampled adversarial policy.

    This class orchestrates beliefs, iterative deepening and final move
    selection. Game transitions belong to GameEngine, evaluation belongs to
    StrategicEvaluator, and alpha-beta recursion belongs to the algorithm
    implementations.
    """

    def __init__(
        self,
        engine: GameEngine,
        seed: int,
        *,
        priors: tuple[DeckPrior, DeckPrior] | None = None,
        belief_samples: int = 3,
        rollout_plies: int = 5,
        candidate_width: int = 6,
        node_budget: int = 20_000,
        search_backend: str = "auto",
        exploration: float = 0.0,
    ):
        evaluator = StrategicEvaluator()
        super().__init__(
            seed=seed,
            exploration=exploration,
            evaluator=evaluator,
        )
        if belief_samples <= 0:
            raise ValueError("belief_samples must be positive")
        if rollout_plies <= 0:
            raise ValueError("rollout_plies must be positive")
        if candidate_width <= 0:
            raise ValueError("candidate_width must be positive")
        if node_budget <= 0:
            raise ValueError("node_budget must be positive")
        if search_backend not in {"auto", "cython", "python"}:
            raise ValueError("search_backend must be auto, cython, or python")

        native_supported = bool(
            _native_search_value is not None
            and _NativeFastEngine is not None
            and _NativeHeuristicEvaluator is not None
            and _NativeSearchBudget is not None
            and _NativeTranspositionTable is not None
        )
        if search_backend == "cython" and not native_supported:
            raise RuntimeError(
                "Packed Cython alpha-beta requested but the canonical "
                "extension is unavailable; run "
                "python -m pip install -e '.[dev]'"
            )

        self.search_backend = search_backend
        self._use_native = (
            native_supported
            and search_backend in {"auto", "cython"}
        )

        self.belief = BeliefSampler(engine, priors=priors)
        self.belief_samples = belief_samples
        self.rollout_plies = rollout_plies
        self.candidate_width = candidate_width
        self.node_budget = node_budget

        self._python_search = AlphaBetaSearch(
            engine,
            evaluator,
            candidate_width=candidate_width,
        )
        self._fast_engine = (
            _NativeFastEngine(engine)
            if self._use_native
            else None
        )
        self._native_evaluator = (
            _NativeHeuristicEvaluator(self._fast_engine)
            if self._use_native
            else None
        )
        self._native_tt = (
            _NativeTranspositionTable(max(131_072, node_budget * 4))
            if self._use_native
            else None
        )

    def choose(self, engine: GameEngine, state: GameState) -> Action:
        root_player = state.active_player
        actions = engine.legal_actions(state)
        if len(actions) == 1:
            self.last_decision = {
                "candidate_count": 1,
                "selected_score": 0.0,
                "score_gap": 0.0,
                "selected_action": type(actions[0]).__name__,
                "policy_source": "strategic_heuristic",
                "belief_samples": 0,
                "rollout_plies": self.rollout_plies,
                "completed_depth": 0,
                "search_nodes": 0,
                "search_budget": self.node_budget,
                "search_backend": (
                    "cython" if self._use_native else "python"
                ),
                "search_backend_detail": (
                    "packed-native" if self._use_native else "python"
                ),
                "evaluated_candidates": 1,
            }
            return actions[0]

        candidates = self._python_search.ordered_actions(
            state,
            root_player,
            width=self.candidate_width,
        )

        # Pass and Draw are strategically unusual. Preserve them even when
        # candidate pruning is active.
        for action in actions:
            if isinstance(action, (Pass, Draw)) and action not in candidates:
                candidates.append(action)

        scores = {
            action: self.evaluator._score_action(
                engine,
                state,
                root_player,
                action,
            )
            for action in candidates
        }
        samples = [
            self.belief.sample(state, root_player, self.rng)
            for _ in range(self.belief_samples)
        ]

        budget = (
            _NativeSearchBudget(self.node_budget)
            if self._use_native
            else SearchBudget(self.node_budget)
        )
        if self._use_native:
            self._native_tt.clear()
        completed_depth = 0
        transposition: dict[tuple[object, ...], float] = {}
        scratch: list[GameState] = []

        for depth in range(1, self.rollout_plies + 1):
            depth_scores: dict[Action, list[float]] = {
                action: [] for action in candidates
            }
            root_order = sorted(
                candidates,
                key=lambda action: (
                    -scores[action],
                    action_key(action),
                ),
            )

            try:
                for sampled in samples:
                    for action in root_order:
                        child = sampled.clone()
                        engine.apply(child, action, validate=False)
                        if self._use_native:
                            value = _native_search_value(
                                self._fast_engine,
                                child,
                                root_player,
                                depth - 1,
                                -inf,
                                inf,
                                budget,
                                self.candidate_width,
                                self._native_evaluator,
                                self._native_tt,
                            )
                        else:
                            value = self._python_search.search(
                                child,
                                root_player=root_player,
                                depth=depth - 1,
                                alpha=-inf,
                                beta=inf,
                                budget=budget,
                                transposition=transposition,
                                scratch=scratch,
                            )
                        depth_scores[action].append(value)
            except SearchLimit:
                break
            except Exception as exc:
                if (
                    self._use_native
                    and _NativeSearchLimit is not None
                    and isinstance(exc, _NativeSearchLimit)
                ):
                    break
                raise

            scores = {
                action: mean(values)
                for action, values in depth_scores.items()
            }
            completed_depth = depth

        ranked = [
            ScoredAction(action, scores[action])
            for action in candidates
        ]
        ranked.sort(
            key=lambda item: (
                -item.score,
                action_key(item.action),
            )
        )
        selected = ranked[0]
        second = ranked[1].score if len(ranked) > 1 else selected.score

        self.last_decision = {
            "candidate_count": len(actions),
            "selected_score": selected.score,
            "score_gap": selected.score - second,
            "selected_action": type(selected.action).__name__,
            "policy_source": "strategic_heuristic",
            "belief_samples": self.belief_samples,
            "rollout_plies": self.rollout_plies,
            "completed_depth": completed_depth,
            "search_nodes": min(budget.nodes, self.node_budget),
            "search_budget": self.node_budget,
            "search_backend": (
                "cython" if self._use_native else "python"
            ),
            "search_backend_detail": (
                "packed-native" if self._use_native else "python"
            ),
            "evaluated_candidates": len(candidates),
            "transposition_hits": (
                int(self._native_tt.hits) if self._use_native else 0
            ),
            "transposition_stores": (
                int(self._native_tt.stores) if self._use_native else 0
            ),
        }
        return selected.action
