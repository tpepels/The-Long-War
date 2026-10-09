"""Game-independent reference alpha-beta with turn-based depth and beam ordering."""
from __future__ import annotations

from dataclasses import dataclass
from math import inf
from typing import Generic, Hashable, TypeVar

from .game_interface import SearchGame

StateT = TypeVar("StateT")
ActionT = TypeVar("ActionT")


class SearchLimit(RuntimeError):
    pass


@dataclass
class SearchBudget:
    limit: int
    nodes: int = 0

    def visit(self) -> None:
        if self.nodes >= self.limit:
            raise SearchLimit
        self.nodes += 1


class GenericAlphaBetaSearch(Generic[StateT, ActionT]):
    """Portable alpha-beta; all game semantics live behind SearchGame.

    Terminal utility, continuation choices, turn depth, action prioritization
    and transposition identity are provided by the adapter. Evaluations are
    root-player relative, so maximizing is based on the current actor.
    """

    def __init__(self, game: SearchGame[StateT, ActionT], *, candidate_width: int):
        if candidate_width <= 0:
            raise ValueError("candidate_width must be positive")
        self.game = game
        self.candidate_width = candidate_width

    def search(
        self,
        state: StateT,
        *,
        root_player: int,
        depth: int,
        alpha: float,
        beta: float,
        budget: SearchBudget,
        transposition: dict[tuple[object, ...], float],
        scratch: list[StateT],
        level: int = 0,
    ) -> float:
        budget.visit()

        if self.game.is_terminal(state) or (
            depth <= 0 and self.game.frontier_ready(state)
        ):
            return self.game.evaluate(state, root_player)

        cache_key = (
            depth,
            root_player,
            self.state_key(state),
        )
        cached = transposition.get(cache_key)
        if cached is not None:
            return cached

        actor = self.game.active_player(state)
        actions = self.ordered_actions(
            state,
            actor,
            width=self.candidate_width,
        )
        if not actions:
            return self.game.evaluate(state, root_player)

        maximizing = actor == root_player
        value = -inf if maximizing else inf
        alpha_start, beta_start = alpha, beta

        for action in actions:
            if level < len(scratch):
                child = scratch[level]
                self.game.copy_state(state, child)
            else:
                child = self.game.copy_state(state, None)
                scratch.append(child)

            self.game.apply(child, action)
            turn_completed = self.game.completed_turn(state, child, action)
            child_depth = depth - int(turn_completed)
            child_value = self.search(
                child,
                root_player=root_player,
                depth=child_depth,
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
        state: StateT,
        actor: int,
        *,
        width: int,
    ) -> list[ActionT]:
        actions = self.game.legal_actions(state)
        ranked = sorted(
            actions,
            key=lambda action: (
                -self.game.action_score(state, actor, action),
                self.game.action_id(action),
            ),
        )
        if len(ranked) <= width:
            return ranked

        selected = list(ranked[:width])
        # Turn-control decisions must survive beam pruning.
        for action in ranked[width:]:
            if self.game.is_priority_action(action) and action not in selected:
                selected.append(action)
        return selected


    def state_key(self, state: StateT) -> Hashable:
        return self.game.state_key(state)
