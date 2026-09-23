from __future__ import annotations

from .game.actions import Action
from .game.engine import GameEngine
from .game.model import GameState


def opening_mulligan_indices(
    engine: GameEngine,
    hand: list[str],
    *,
    maximum: int = 2,
) -> tuple[int, ...]:
    """Opening-hand policy, separate from game rules and search algorithms."""
    if maximum <= 0 or not hand:
        return ()

    types = [engine.cards[card_id]["type"] for card_id in hand]
    stratagem_count = types.count("stratagem")

    scored: list[tuple[float, int]] = []
    seen_stratagems = 0
    for index, card_id in enumerate(hand):
        card = engine.cards[card_id]
        card_type = card["type"]

        if card_type == "subject":
            score = 5.0 + 0.08 * float(card.get("strength", 0))
        elif card_type == "link":
            score = 3.2
        elif card_type == "name":
            score = 3.0
        elif card_type == "plot":
            score = 3.7 if card.get("veiled", False) else 2.6
        elif card_type == "stratagem":
            seen_stratagems += 1
            score = 3.2 if seen_stratagems == 1 else 2.0
            if stratagem_count >= 3:
                score -= 0.35
        else:
            score = 2.5
        scored.append((score, index))

    scored.sort(key=lambda item: (item[0], item[1]))
    return tuple(sorted(index for _, index in scored[:maximum]))


class HeuristicEvaluator:
    """Thin adapter to the single compiled heuristic implementation.

    The evaluator contains no game rules and no search algorithm. It only
    assigns values to states/actions by delegating to the Cython heuristic
    layer that operates on canonical packed engine state.
    """

    @staticmethod
    def _packed(engine: GameEngine, state: GameState):
        native = engine._native_core()
        evaluator = engine._native_heuristic()
        return native, evaluator, native.from_game_state(state)

    def evaluate(
        self,
        engine: GameEngine,
        state: GameState,
        player: int,
    ) -> float:
        return self._state_value(engine, state, player)

    def _state_value(
        self,
        engine: GameEngine,
        state: GameState,
        player: int,
    ) -> float:
        _native, evaluator, packed = self._packed(engine, state)
        return float(evaluator.evaluate(packed, player))

    def _score_action(
        self,
        engine: GameEngine,
        state: GameState,
        player: int,
        action: Action,
    ) -> float:
        native, evaluator, packed = self._packed(engine, state)
        native_action = engine._native_action(packed, action)
        return float(
            evaluator.score_action(
                packed,
                player,
                native_action,
            )
        )

    def _hand_construction_value(
        self,
        engine: GameEngine,
        state: GameState,
        player: int,
    ) -> float:
        _native, evaluator, packed = self._packed(engine, state)
        return float(evaluator.hand_construction_value(packed, player))


class StrategicEvaluator(HeuristicEvaluator):
    """Long-horizon heuristic adapter used by search algorithms."""

    def _strategic_state_value(
        self,
        engine: GameEngine,
        state: GameState,
        player: int,
    ) -> float:
        _native, evaluator, packed = self._packed(engine, state)
        return float(evaluator.strategic_evaluate(packed, player))
