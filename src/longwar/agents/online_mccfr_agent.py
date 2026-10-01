from __future__ import annotations

import random

from ..protocol import PolicySource
from ..belief import DeckPrior
from ..game.actions import Action
from ..game.engine import GameEngine
from ..game.model import GameState
from ..mccfr import action_key
from ..online_mccfr import OnlineMCCFRResolver
from .heuristic_agent import opening_mulligan_indices
from ..heuristics import command_preserving_actions


class OnlineMCCFRAgent:
    """Re-solves the current information set before every decision."""

    def __init__(
        self,
        engine: GameEngine,
        seed: int,
        *,
        priors: tuple[DeckPrior, DeckPrior] | None = None,
        iterations: int = 16,
        max_depth: int = 2,
        deterministic: bool = False,
    ):
        self.rng = random.Random(seed)
        self.deterministic = deterministic
        self.resolver = OnlineMCCFRResolver(
            engine,
            priors=priors,
            seed=seed,
            iterations=iterations,
            max_depth=max_depth,
        )
        self.last_decision: dict[str, float | int | str] = {}

    def choose_mulligan(
        self,
        engine: GameEngine,
        hand: list[str],
    ) -> tuple[int, ...]:
        return opening_mulligan_indices(engine, hand)

    def choose(self, engine: GameEngine, state: GameState) -> Action:
        actions = engine.legal_actions(state)
        preserving, guarded = command_preserving_actions(engine, state, actions)
        if len(actions) == 1:
            self.last_decision = {
                "candidate_count": 1,
                "selected_score": 1.0,
                "score_gap": 1.0,
                "selected_action": type(actions[0]).__name__,
                "policy_source": PolicySource.FORCED.value,
                "root_coverage": 1.0,
                "resolver_iterations": 0,
                "belief_samples": 0,
                "resolver_information_sets": 0,
                "known_hidden_cards": 0,
                "belief_prior": "none",
                "command_guard_applied": guarded > 0,
                "command_guard_filtered_actions": guarded,
            }
            return actions[0]

        result = self.resolver.solve(state)
        action_map = {action_key(action): action for action in actions}
        probabilities = {
            key: max(0.0, float(result.strategy.get(key, 0.0)))
            for key in action_map
        }
        total = sum(probabilities.values())
        if total <= 0:
            probability = 1.0 / len(probabilities)
            probabilities = {key: probability for key in probabilities}
        else:
            probabilities = {
                key: value / total
                for key, value in probabilities.items()
            }

        ranked = sorted(
            probabilities.items(),
            key=lambda item: (item[1], item[0]),
            reverse=True,
        )
        selected_key = ranked[0][0] if self.deterministic else self._sample(probabilities)
        guard_overrode_selection = action_map[selected_key] not in preserving
        if guard_overrode_selection:
            safe_keys = {action_key(action) for action in preserving}
            safe_probabilities = {
                key: value
                for key, value in probabilities.items()
                if key in safe_keys
            }
            safe_total = sum(safe_probabilities.values())
            if safe_total <= 0:
                probability = 1.0 / len(safe_probabilities)
                safe_probabilities = {
                    key: probability for key in safe_probabilities
                }
            else:
                safe_probabilities = {
                    key: value / safe_total
                    for key, value in safe_probabilities.items()
                }
            selected_key = (
                max(
                    safe_probabilities,
                    key=lambda key: (safe_probabilities[key], key),
                )
                if self.deterministic
                else self._sample(safe_probabilities)
            )

        best = ranked[0][1]
        second = ranked[1][1] if len(ranked) > 1 else 0.0

        self.last_decision = {
            "candidate_count": len(actions),
            "selected_score": probabilities[selected_key],
            "score_gap": best - second,
            "selected_action": type(action_map[selected_key]).__name__,
            "policy_source": PolicySource.ONLINE_MCCFR.value,
            "root_coverage": result.root_coverage,
            "resolver_iterations": result.iterations,
            "belief_samples": result.belief_samples,
            "resolver_information_sets": result.information_sets,
            "known_hidden_cards": result.known_hidden_cards,
            "belief_prior": result.belief_prior,
            "command_guard_applied": guarded > 0,
            "command_guard_filtered_actions": guarded,
            "command_guard_overrode_selection": guard_overrode_selection,
        }
        return action_map[selected_key]

    def _sample(self, probabilities: dict[str, float]) -> str:
        threshold = self.rng.random()
        cumulative = 0.0
        last = next(iter(probabilities))
        for key, probability in probabilities.items():
            last = key
            cumulative += probability
            if threshold <= cumulative:
                return key
        return last
