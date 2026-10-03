from __future__ import annotations

from dataclasses import dataclass
from math import inf

from ..game.actions import Action, EndTurn, Pass, action_key
from ..game.engine import GameEngine
from ..game.model import GameState, Phase
from ..heuristics import StrategicEvaluator


class SearchLimit(RuntimeError):
    pass


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


@dataclass
class SearchBudget:
    limit: int
    nodes: int = 0

    def visit(self) -> None:
        self.nodes += 1
        if self.nodes > self.limit:
            raise SearchLimit


class AlphaBetaSearch:
    """Reference alpha-beta algorithm over canonical engine/evaluator APIs."""

    def __init__(
        self,
        engine: GameEngine,
        evaluator: StrategicEvaluator,
        *,
        candidate_width: int,
    ):
        self.engine = engine
        self.evaluator = evaluator
        self.candidate_width = candidate_width

    def search(
        self,
        state: GameState,
        *,
        root_player: int,
        depth: int,
        alpha: float,
        beta: float,
        budget: SearchBudget,
        transposition: dict[tuple[object, ...], float],
        scratch: list[GameState],
        level: int = 0,
    ) -> float:
        budget.visit()

        if state.phase is Phase.COMPLETE or depth <= 0:
            return self.evaluator._strategic_state_value(
                self.engine,
                state,
                root_player,
            )

        cache_key = (
            depth,
            root_player,
            self.state_key(state),
        )
        cached = transposition.get(cache_key)
        if cached is not None:
            return cached

        actor = state.active_player
        actions = self.ordered_actions(
            state,
            actor,
            width=self.candidate_width,
        )
        if not actions:
            return self.evaluator._strategic_state_value(
                self.engine,
                state,
                root_player,
            )

        maximizing = actor == root_player
        value = -inf if maximizing else inf
        alpha_start, beta_start = alpha, beta

        for action in actions:
            if level < len(scratch):
                child = scratch[level]
                child.copy_from(state)
            else:
                child = state.clone()
                scratch.append(child)

            self.engine.apply(child, action, validate=False)
            child_value = self.search(
                child,
                root_player=root_player,
                depth=depth - 1,
                alpha=alpha,
                beta=beta,
                budget=budget,
                transposition=transposition,
                scratch=scratch,
                level=level + 1,
            )

            if maximizing:
                value = max(value, child_value)
                alpha = max(alpha, value)
            else:
                value = min(value, child_value)
                beta = min(beta, value)

            if beta <= alpha:
                break

        # Descendant cutoffs can also make a fully searched node a bound.
        # Only results strictly inside the original window are exact.
        if alpha_start < value < beta_start:
            transposition[cache_key] = value
        return value

    def ordered_actions(
        self,
        state: GameState,
        actor: int,
        *,
        width: int,
    ) -> list[Action]:
        actions = self.engine.legal_actions(state)
        ranked = sorted(
            actions,
            key=lambda action: (
                -self.evaluator._score_action(
                    self.engine,
                    state,
                    actor,
                    action,
                ),
                action_key(action),
            ),
        )
        if len(ranked) <= width:
            return ranked

        selected = list(ranked[:width])
        # Turn-control decisions must survive beam pruning.
        for action in ranked[width:]:
            if isinstance(action, (Pass, EndTurn)) and action not in selected:
                selected.append(action)
        return selected

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
                )
                for constraint in state.constraints
            ),
            _freeze_state_value(state.battle_resolution),
            state.turn_number,
        )

