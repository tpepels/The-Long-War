from __future__ import annotations

from dataclasses import dataclass
from math import inf

from ..game.actions import Action, Draw, Pass, action_key
from ..game.engine import GameEngine
from ..game.model import GameState, Phase
from ..heuristics import StrategicEvaluator


class SearchLimit(RuntimeError):
    pass


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
        # Resource/tempo decisions must survive beam pruning.
        for action in ranked[width:]:
            if isinstance(action, (Pass, Draw)) and action not in selected:
                selected.append(action)
        return selected

    @staticmethod
    def state_key(state: GameState) -> tuple[object, ...]:
        """Cache key covering every GameState field that can change the
        legal-action set, the recursive search value, or move ordering.

        Deliberately excludes write-only telemetry/UI fields that are never
        read back by legality, `StrategicEvaluator`, or action ordering
        (`command_spent_this_battle` and its siblings, `opening_hands`,
        `last_battle_snapshot`, `observations`, `known_hidden_hand`) -
        including them would only fragment the cache without changing
        correctness. `test_python_state_key_tracks_every_game_state_field`
        enforces that every field is either represented here or explicitly
        exempted, so a newly added field cannot silently repeat the
        cleanup-state cache-key bug.
        """
        players = tuple(
            (
                tuple(player.deck),
                tuple(sorted(player.hand)),
                tuple(player.discard),
                player.victories,
                player.passed,
                player.command,
                player.free_cycle,
            )
            for player in state.players
        )
        board = tuple(
            (
                slot.subject,
                slot.link,
                slot.name,
                slot.temporary_strength,
            )
            for side in state.board
            for front in side
            for slot in front
        )
        schemes = tuple(
            None if scheme is None else (scheme.card_id, scheme.revealed)
            for side in state.schemes
            for scheme in side
        )
        stratagems = tuple(
            None if stratagem is None else (stratagem.card_id, stratagem.revealed)
            for stratagem in state.stratagems
        )
        return (
            state.phase.value,
            state.active_player,
            state.battle,
            state.chooser,
            state.winner,
            state.shuffle_seed,
            players,
            board,
            schemes,
            stratagems,
            tuple(state.stratagem_used),
            tuple(state.hero_used),
            tuple(state.draw_used),
            tuple(state.discarded_this_battle),
            tuple(state.pass_order),
            tuple(state.operations_this_battle),
            state.cleanup_pending,
            state.cleanup_next_starter,
            state.cleanup_next_chooser,
            state.turn_number,
        )
