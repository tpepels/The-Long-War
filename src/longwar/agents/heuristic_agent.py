from __future__ import annotations

import random
from dataclasses import dataclass

from ..game.actions import Action
from ..game.engine import GameEngine
from ..game.model import GameState
from ..heuristics import HeuristicEvaluator, opening_mulligan_indices



@dataclass(frozen=True)
class ScoredAction:
    action: Action
    score: float


class HeuristicAgent:
    """One-ply, public-information agent.

    The agent may inspect its own hand, all public battlefield information,
    public hand sizes, decks/discards sizes, Victory markers, and revealed
    state. It never evaluates the identities of cards in the opponent's hand.
    """

    def __init__(
        self,
        seed: int,
        *,
        exploration: float = 0.0,
        evaluator: HeuristicEvaluator | None = None,
    ):
        if not 0.0 <= exploration <= 1.0:
            raise ValueError("exploration must be between 0 and 1")
        self.rng = random.Random(seed)
        self.exploration = exploration
        self.evaluator = evaluator or HeuristicEvaluator()
        self.last_decision: dict[str, float | int | str] = {}

    def choose_mulligan(
        self,
        engine: GameEngine,
        hand: list[str],
    ) -> tuple[int, ...]:
        return opening_mulligan_indices(engine, hand)

    def choose(self, engine: GameEngine, state: GameState) -> Action:
        player = state.active_player
        actions = engine.legal_actions(state)

        if len(actions) == 1:
            self.last_decision = {
                "candidate_count": 1,
                "selected_score": 0.0,
                "score_gap": 0.0,
                "selected_action": type(actions[0]).__name__,
            }
            return actions[0]

        scored = [
            ScoredAction(action, self.evaluator._score_action(engine, state, player, action))
            for action in actions
        ]
        # Randomize exact score ties with the agent's seeded RNG before
        # sorting. Otherwise semantically identical choices (notably hidden
        # Stratagem sets) are selected by card-id/repr ordering, which creates
        # fake play-rate differences in simulation telemetry.
        self.rng.shuffle(scored)
        scored.sort(key=lambda item: item.score, reverse=True)

        if self.exploration > 0 and self.rng.random() < self.exploration:
            # Explore among the best quarter rather than selecting nonsense.
            width = max(1, len(scored) // 4)
            selected = self.rng.choice(scored[:width])
        else:
            selected = scored[0]

        second = scored[1].score if len(scored) > 1 else selected.score
        self.last_decision = {
            "candidate_count": len(scored),
            "selected_score": selected.score,
            "score_gap": selected.score - second,
            "selected_action": type(selected.action).__name__,
        }
        return selected.action

    def evaluate(
        self,
        engine: GameEngine,
        state: GameState,
        player: int,
    ) -> float:
        return self.evaluator._state_value(engine, state, player)

    def _score_action(
        self,
        engine: GameEngine,
        state: GameState,
        player: int,
        action: Action,
    ) -> float:
        """Compatibility hook for search code; valuation lives in evaluator."""
        return self.evaluator._score_action(engine, state, player, action)

    def _state_value(
        self,
        engine: GameEngine,
        state: GameState,
        player: int,
    ) -> float:
        return self.evaluator._state_value(engine, state, player)

    def _hand_construction_value(
        self,
        engine: GameEngine,
        state: GameState,
        player: int,
    ) -> float:
        return self.evaluator._hand_construction_value(engine, state, player)

