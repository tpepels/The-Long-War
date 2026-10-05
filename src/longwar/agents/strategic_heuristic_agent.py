from __future__ import annotations

from math import inf, isfinite
from time import perf_counter
from statistics import mean

from ..protocol import PolicySource, SearchBackend
from ..algorithms.alpha_beta import (
    AlphaBetaSearch,
    SearchBudget,
    SearchLimit,
    action_completed_turn,
)
from ..belief import BeliefSampler, DeckPrior
from ..game.actions import Action, action_key
from ..game.engine import GameEngine
from ..game.model import GameState
from ..heuristics import (
    DEFAULT_HEURISTIC_WEIGHTS,
    HeuristicWeights,
    StrategicEvaluator,
    command_preserving_actions,
)
from ..native_search import strategic_backend
from .heuristic_agent import HeuristicAgent, ScoredAction

DEFAULT_STRATEGIC_BELIEF_SAMPLES = 3
DEFAULT_STRATEGIC_ROLLOUT_PLIES = 5
DEFAULT_STRATEGIC_CANDIDATE_WIDTH = 6
DEFAULT_STRATEGIC_NODE_BUDGET = 20_000
DEFAULT_STRATEGIC_BACKEND = SearchBackend.AUTO.value
NATIVE_TT_TIMED_FLOOR = 1_048_576
NATIVE_TT_NODE_FLOOR = 131_072
NATIVE_TT_BUDGET_MULTIPLIER = 4


try:
    (
        _NativeFastEngine,
        _NativeHeuristicEvaluator,
        _NativeSearchBudget,
        _NativeSearchLimit,
        _NativeTranspositionTable,
        _native_search_value,
    ) = strategic_backend()
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
        belief_samples: int = DEFAULT_STRATEGIC_BELIEF_SAMPLES,
        rollout_plies: int = DEFAULT_STRATEGIC_ROLLOUT_PLIES,
        candidate_width: int = DEFAULT_STRATEGIC_CANDIDATE_WIDTH,
        node_budget: int = DEFAULT_STRATEGIC_NODE_BUDGET,
        time_budget_seconds: float | None = None,
        search_backend: str = DEFAULT_STRATEGIC_BACKEND,
        exploration: float = 0.0,
        heuristic_weights: HeuristicWeights | None = None,
    ):
        self.heuristic_weights = heuristic_weights or DEFAULT_HEURISTIC_WEIGHTS
        public_evaluator = StrategicEvaluator(
            self.heuristic_weights,
            sampled_opponent_resources=False,
        )
        evaluator = StrategicEvaluator(
            self.heuristic_weights,
            sampled_opponent_resources=True,
        )
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
        if (
            time_budget_seconds is not None
            and (not isfinite(time_budget_seconds) or time_budget_seconds <= 0.0)
        ):
            raise ValueError("time_budget_seconds must be finite and positive")
        try:
            parsed_backend = SearchBackend(search_backend)
        except ValueError as exc:
            allowed = ", ".join(backend.value for backend in SearchBackend)
            raise ValueError(
                f"search_backend must be one of: {allowed}"
            ) from exc

        native_supported = bool(
            _native_search_value is not None
            and _NativeFastEngine is not None
            and _NativeHeuristicEvaluator is not None
            and _NativeSearchBudget is not None
            and _NativeTranspositionTable is not None
        )
        if time_budget_seconds is not None and parsed_backend is SearchBackend.PYTHON:
            raise ValueError("wall-clock alpha-beta budgets require the Cython backend")
        if parsed_backend is SearchBackend.CYTHON and not native_supported:
            raise RuntimeError(
                "Packed Cython alpha-beta requested but the canonical "
                "extension is unavailable; run "
                "python -m pip install -e '.[dev]'"
            )

        self.search_backend = parsed_backend.value
        self._use_native = (
            native_supported
            and parsed_backend in {SearchBackend.AUTO, SearchBackend.CYTHON}
        )

        self.belief = BeliefSampler(engine, priors=priors)
        self.belief_samples = belief_samples
        self.rollout_plies = rollout_plies
        self.candidate_width = candidate_width
        self.node_budget = node_budget
        self.time_budget_seconds = time_budget_seconds

        # Root candidate ordering runs on the real observation state and must
        # therefore be public-information only. Deeper alpha-beta runs on
        # determinized belief samples and may use sampled hidden resources.
        self._public_evaluator = public_evaluator
        self._public_search = AlphaBetaSearch(
            engine,
            public_evaluator,
            candidate_width=candidate_width,
        )
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
            _NativeHeuristicEvaluator(
                self._fast_engine,
                self.heuristic_weights,
                sampled_opponent_resources=True,
            )
            if self._use_native
            else None
        )
        tt_floor = (
            NATIVE_TT_TIMED_FLOOR
            if time_budget_seconds is not None
            else NATIVE_TT_NODE_FLOOR
        )
        self._native_tt = (
            _NativeTranspositionTable(max(tt_floor, node_budget * NATIVE_TT_BUDGET_MULTIPLIER))
            if self._use_native
            else None
        )

    def release_search_memory(self) -> None:
        """Release persistent native search storage after a finished game."""
        if self._native_tt is not None:
            self._native_tt.clear()
        self._native_tt = None
        self._native_evaluator = None
        self._fast_engine = None
        self.last_decision = {}

    def evaluate(
        self,
        engine: GameEngine,
        state: GameState,
        player: int,
    ) -> float:
        """Evaluate a real observation state without reading hidden identities."""
        return self._public_evaluator._state_value(engine, state, player)

    def choose(self, engine: GameEngine, state: GameState) -> Action:
        decision_started = perf_counter()
        root_player = state.active_player
        actions = engine.legal_actions(state)
        preserving, guarded = command_preserving_actions(engine, state, actions)
        if len(actions) == 1:
            self.last_decision = {
                "candidate_count": 1,
                "selected_score": 0.0,
                "score_gap": 0.0,
                "selected_action": type(actions[0]).__name__,
                "policy_source": PolicySource.STRATEGIC_HEURISTIC.value,
                "belief_samples": 0,
                "rollout_plies": self.rollout_plies,
                "completed_depth": 0,
                "search_nodes": 0,
                "search_budget": self.node_budget,
                "search_time_budget_seconds": self.time_budget_seconds,
                "decision_seconds": perf_counter() - decision_started,
                "search_backend": (
                    "cython" if self._use_native else "python"
                ),
                "search_backend_detail": (
                    "packed-native" if self._use_native else "python"
                ),
                "evaluated_candidates": 1,
                "heuristic_weights_fingerprint": self.heuristic_weights.fingerprint(),
                "command_guard_applied": guarded > 0,
                "command_guard_filtered_actions": guarded,
            }
            return actions[0]

        candidates = self._public_search.ordered_actions(
            state,
            root_player,
            width=self.candidate_width,
        )

        if guarded and not any(action in preserving for action in candidates):
            candidates.append(
                max(
                    preserving,
                    key=lambda action: self._public_evaluator._score_action(
                        engine,
                        state,
                        root_player,
                        action,
                    ),
                )
            )

        scores = {
            action: self._public_evaluator._score_action(
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

        elapsed_setup = perf_counter() - decision_started
        remaining_time = (
            max(1.0e-6, self.time_budget_seconds - elapsed_setup)
            if self.time_budget_seconds is not None
            else 0.0
        )
        effective_node_limit = (
            max(self.node_budget, 2_000_000_000)
            if self.time_budget_seconds is not None
            else self.node_budget
        )
        budget = (
            _NativeSearchBudget(effective_node_limit, remaining_time)
            if self._use_native
            else SearchBudget(effective_node_limit)
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
                        remaining_depth = depth - int(
                            action_completed_turn(
                                engine,
                                sampled,
                                child,
                                action,
                            )
                        )
                        if self._use_native:
                            value = _native_search_value(
                                self._fast_engine,
                                child,
                                root_player,
                                remaining_depth,
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
                                depth=remaining_depth,
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
        guard_overrode_selection = selected.action not in preserving
        if guard_overrode_selection:
            safe_ranked = [
                item for item in ranked if item.action in preserving
            ]
            selected = safe_ranked[0]
            second = (
                safe_ranked[1].score
                if len(safe_ranked) > 1
                else selected.score
            )
        else:
            second = ranked[1].score if len(ranked) > 1 else selected.score

        self.last_decision = {
            "candidate_count": len(actions),
            "selected_score": selected.score,
            "score_gap": selected.score - second,
            "selected_action": type(selected.action).__name__,
            "policy_source": PolicySource.STRATEGIC_HEURISTIC.value,
            "belief_samples": self.belief_samples,
            "rollout_plies": self.rollout_plies,
            "completed_depth": completed_depth,
            "search_nodes": int(budget.nodes),
            "search_budget": self.node_budget,
            "search_node_limit_effective": effective_node_limit,
            "search_time_budget_seconds": self.time_budget_seconds,
            "search_timed_out": bool(
                getattr(budget, "timed_out", False)
            ),
            "decision_seconds": perf_counter() - decision_started,
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
            "heuristic_weights_fingerprint": self.heuristic_weights.fingerprint(),
            "command_guard_applied": guarded > 0,
            "command_guard_filtered_actions": guarded,
            "command_guard_overrode_selection": guard_overrode_selection,
        }
        return selected.action
