from __future__ import annotations

from .game.actions import Action
from .game.engine import GameEngine
from .game.model import GameState, Phase, other_player
from .protocol import CardField, CardType


def command_preserving_actions(
    engine: GameEngine,
    state: GameState,
    actions: list[Action] | None = None,
) -> tuple[list[Action], int]:
    """Remove avoidable unilateral Command-exhaustion blunders.

    This is deliberately a final-action safety guard, not a rules restriction.
    If every legal action leaves the acting side exhausted, nothing is removed.
    Exact child states are inspected so an action that immediately restores
    Command or produces a terminal win is not falsely rejected.
    """
    legal = list(engine.legal_actions(state) if actions is None else actions)
    if len(legal) <= 1:
        return legal, 0

    actor = state.active_player
    opponent = other_player(actor)
    threshold = int(engine.rules.command_collapse_threshold)
    actor_command = state.players[actor].command
    preserving: list[Action] = []
    exhausting: list[Action] = []

    for action in legal:
        # Most legal actions cannot possibly reach the Collapse boundary.
        # Match the native guard's cheap path and reserve exact child-state
        # simulation for actions that can spend the remaining Command margin.
        cost = engine.command_cost_for_action(state, action)
        if actor_command - cost > threshold:
            preserving.append(action)
            continue

        child = state.clone()
        engine.apply(child, action, validate=False)
        unilateral_exhaustion = (
            child.players[actor].command <= threshold
            and child.players[opponent].command > threshold
            and not (
                child.phase is Phase.COMPLETE
                and child.winner == actor
            )
        )
        if unilateral_exhaustion:
            exhausting.append(action)
        else:
            preserving.append(action)

    if not preserving:
        return legal, 0
    return preserving, len(exhausting)


def opening_mulligan_indices(
    engine: GameEngine,
    hand: list[str],
    *,
    maximum: int | None = None,
) -> tuple[int, ...]:
    """Opening-hand policy, separate from game rules and search algorithms."""
    if maximum is None:
        maximum = engine.rules.mulligan_max_cards
    if maximum <= 0 or not hand:
        return ()

    types = [
        engine.cards[card_id][CardField.TYPE]
        for card_id in hand
    ]
    stratagem_count = types.count(CardType.STRATAGEM)

    scored: list[tuple[float, int]] = []
    seen_stratagems = 0
    for index, card_id in enumerate(hand):
        card = engine.cards[card_id]
        card_type = card[CardField.TYPE]

        if card_type == CardType.FORCE:
            score = 5.0 + 0.08 * float(card.get(CardField.STRENGTH, 0))
        elif card_type == CardType.BOND:
            score = 3.2
        elif card_type == CardType.NAME:
            score = 3.0
        elif card_type == CardType.NARRATIVE:
            score = 3.7 if card.get(CardField.ONGOING, False) else 2.6
        elif card_type == CardType.STRATAGEM:
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
