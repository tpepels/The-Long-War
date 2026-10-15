"""Compatibility facade for The Long War alpha-beta search.

The reusable search loop lives in generic_alpha_beta; game-specific semantics
live in LongWarSearchGame. Existing agents and tests may keep constructing
AlphaBetaSearch(engine, evaluator, candidate_width=...).
"""
from __future__ import annotations

from ..game.engine import GameEngine
from ..game.model import GameState
from ..heuristics import StrategicEvaluator
from ..search_adapters import LongWarSearchGame, _freeze_state_value
from .generic_alpha_beta import (
    GenericAlphaBetaSearch,
    SearchBudget,
    SearchLimit,
)


def action_completed_turn(engine, state, child, action) -> bool:
    """Backward-compatible turn transition helper."""
    return engine.transition_completed_turn(state, child, action)


class AlphaBetaSearch(GenericAlphaBetaSearch):
    def __init__(
        self,
        engine: GameEngine,
        evaluator: StrategicEvaluator,
        *,
        candidate_width: int,
    ):
        self.engine = engine
        self.evaluator = evaluator
        super().__init__(
            LongWarSearchGame(engine, evaluator),
            candidate_width=candidate_width,
        )

    @staticmethod
    def state_key(state: GameState) -> tuple[object, ...]:
        return LongWarSearchGame.state_key(state)
