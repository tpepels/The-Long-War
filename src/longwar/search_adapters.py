"""The Long War implementation of the generic search-game contract.

Only this adapter is allowed to interpret the current GameState, Action and
engine interfaces for portable algorithms. Native packed search is separately
adapted at the Cython boundary for performance.
"""
from __future__ import annotations

from typing import Any

from .game.actions import Action, EndTurn, Pass, action_key
from .game.engine import GameEngine
from .game.model import GameState, Phase
from .heuristics import StrategicEvaluator


def _freeze_state_value(value: object) -> object:
    """Convert nested mutable engine state into a deterministic hashable value."""
    if isinstance(value, dict):
        return tuple(
            (key, _freeze_state_value(item))
            for key, item in sorted(value.items())
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_state_value(item) for item in value)
    return value



class LongWarSearchGame:
    def __init__(self, engine: GameEngine, evaluator: Any):
        self.engine = engine
        self.evaluator = evaluator

    def active_player(self, state: GameState) -> int:
        return state.active_player

    def is_terminal(self, state: GameState) -> bool:
        return state.phase is Phase.COMPLETE

    def frontier_ready(self, state: GameState) -> bool:
        return (
            not state.pending_effects
            and state.pending_draw_discard_for is None
        )

    def legal_actions(self, state: GameState) -> list[Action]:
        return self.engine.legal_actions(state)

    def copy_state(
        self, source: GameState, reusable: GameState | None
    ) -> GameState:
        if reusable is None:
            return source.clone()
        reusable.copy_from(source)
        return reusable

    def apply(self, state: GameState, action: Action) -> None:
        self.engine.apply(state, action, validate=False)

    def completed_turn(
        self, before: GameState, after: GameState, action: Action
    ) -> bool:
        return self.engine.transition_completed_turn(before, after, action)

    def action_id(self, action: Action) -> str:
        return action_key(action)

    def is_priority_action(self, action: Action) -> bool:
        return isinstance(action, (Pass, EndTurn))

    def action_score(
        self, state: GameState, player: int, action: Action
    ) -> float:
        scorer = getattr(self.evaluator, "_score_action", None)
        return float(scorer(self.engine, state, player, action)) if scorer else 0.0

    def evaluate(self, state: GameState, player: int) -> float:
        scorer = getattr(self.evaluator, "_strategic_state_value", None)
        if scorer is not None:
            return float(scorer(self.engine, state, player))
        return float(self.evaluator.evaluate(self.engine, state, player))

    def terminal_utility(self, state: GameState, player: int) -> float:
        if state.winner is None:
            return 0.0
        return 1.0 if state.winner == player else -1.0

    def information_set_id(self, state: GameState, player: int) -> str:
        native = self.engine._native_core()
        return str(native.information_id(native.from_game_state(state), player))

    @staticmethod
    def state_key(state: GameState) -> tuple[object, ...]:
        """Cache key for every canonical state component that can affect search."""
        players = tuple(
            (
                tuple(player.deck),
                tuple(sorted(player.hand)),
                tuple(player.discard),
                player.passed,
                player.command,
            )
            for player in state.players
        )
        board = tuple(
            (
                slot.force,
                slot.bond,
                slot.name,
                slot.exhausted,
                slot.temporary_strength,
                slot.maneuvers_this_battle,
                slot.maneuver_direction,
                slot.maneuvered_in_operation,
            )
            for side in state.board
            for front in side
            for slot in front
        )
        narratives = tuple(
            tuple(
                (
                    narrative.card_id,
                    narrative.ongoing,
                    tuple(narrative.fronts),
                    narrative.target_player,
                    narrative.target_position,
                    narrative.triggered_this_battle,
                    narrative.direction,
                    narrative.triggered_players_mask,
                )
                for narrative in side
            )
            for side in state.narratives
        )
        stratagems = tuple(
            (
                None
                if stratagem is None
                else (
                    stratagem.card_id,
                    tuple(stratagem.fronts),
                    stratagem.direction,
                    tuple(stratagem.targets),
                    stratagem.revealed,
                )
            )
            for stratagem in state.stratagems
        )
        return (
            state.phase.value,
            state.active_player,
            state.battle,
            state.winner,
            state.shuffle_seed,
            players,
            board,
            narratives,
            stratagems,
            tuple(state.stratagem_used),
            tuple(state.hero_used),
            tuple(state.discarded_this_battle),
            tuple(state.pass_order),
            state.actions_this_turn,
            state.closing_turns_remaining,
            tuple(state.operations_this_battle),
            tuple(state.maneuvers_this_battle),
            tuple(state.cards_played_this_turn_front_mask),
            tuple(state.cards_played_this_battle_front_mask),
            tuple(state.narratives_played_this_battle),
            state.pending_draw_discard_for,
            state.pending_draw_count,
            state.pending_draw_finish_operation,
            _freeze_state_value(state.pending_effects),
            state.pending_resume,
            state.pending_resume_player,
            tuple(state.free_maneuver_available),
            tuple(
                (
                    constraint.source_card,
                    constraint.player,
                    constraint.kind.value,
                    constraint.source_owner,
                    constraint.front,
                    constraint.direction,
                    constraint.source_position,
                    constraint.activate_turn,
                    constraint.expires_after_operation,
                    constraint.persists_between_battles,
                    constraint.zero_cost,
                    constraint.draw_after_satisfied,
                    constraint.discard_source_narrative,
                    constraint.expires_end_of_activated_turn,
                )
                for constraint in state.constraints
            ),
            _freeze_state_value(state.battle_resolution),
            state.turn_number,
        )


