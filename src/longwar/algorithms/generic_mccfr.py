"""Portable external-sampling MCCFR traversal over the shared game API.

The regret-matching math is in mccfr_core. This layer handles strategic
turn depth and reusable scratch states without interpreting game mechanics.
"""
from __future__ import annotations

import random
from collections.abc import Callable
from typing import Hashable, TypeVar

from .game_interface import SearchGame
from ..mccfr_core import external_sampling_traverse

StateT = TypeVar("StateT")
ActionT = TypeVar("ActionT")


def traverse_game(
    game: SearchGame[StateT, ActionT],
    state: StateT,
    traverser: int,
    *,
    depth: int,
    max_turn_depth: int,
    nodes: dict[Hashable, object],
    rng: random.Random,
    frontier_value: Callable[[StateT, int], float],
    scratch_by_depth: dict[int, StateT] | None = None,
) -> float:
    """One external-sampling traversal with depth measured in completed turns.

    Pending interactions never consume a strategic ply. The tree's information
    keys are entirely provided by the game adapter, including hidden-state
    redaction and policy namespace. No game-specific phase/card logic here.
    """
    if scratch_by_depth is None:
        scratch_by_depth = {}

    raw_depth_by_state_id = {id(state): 0}
    turn_depth_by_state_id = {id(state): depth}

    def next_state(current: StateT, action: ActionT) -> StateT:
        raw_level = raw_depth_by_state_id[id(current)] + 1
        child = game.copy_state(current, scratch_by_depth.get(raw_level))
        scratch_by_depth[raw_level] = child
        game.apply(child, action)
        turn_complete = game.completed_turn(current, child, action)
        raw_depth_by_state_id[id(child)] = raw_level
        turn_depth_by_state_id[id(child)] = (
            turn_depth_by_state_id[id(current)] + int(turn_complete)
        )
        return child

    def is_frontier(current: StateT) -> bool:
        return game.is_terminal(current) or (
            game.frontier_ready(current)
            and turn_depth_by_state_id[id(current)] >= max_turn_depth
        )

    def utility(current: StateT, player: int) -> float:
        if game.is_terminal(current):
            return game.terminal_utility(current, player)
        return frontier_value(current, player)

    # External-sampling traversal recursion depth is intentionally distinct
    # from strategic turn depth because multi-action turns and effect choices
    # may add several raw state transitions per turn.
    return external_sampling_traverse(
        state,
        traverser,
        depth=0,
        max_depth=None,
        nodes=nodes,
        rng=rng,
        is_terminal=is_frontier,
        terminal_utility=utility,
        current_player=game.active_player,
        legal_actions=game.legal_actions,
        action_key=game.action_id,
        information_set_id=game.information_set_id,
        next_state=next_state,
        leaf_value=None,
    )
