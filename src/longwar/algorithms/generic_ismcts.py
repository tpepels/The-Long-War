"""Game-independent information-set MCTS reference implementation.

The production Long War agent retains the inlined Cython backend. This
algorithm is a portable contract/reference implementation for other games and
for validating adapters without importing any particular rules engine.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Generic, Hashable, Sequence, TypeVar

from .game_interface import SearchGame

StateT = TypeVar("StateT")
ActionT = TypeVar("ActionT")


@dataclass(slots=True)
class MCTSEdge:
    visits: int = 0
    value_sum: float = 0.0


@dataclass(slots=True)
class MCTSNode:
    visits: int = 0
    edges: dict[str, MCTSEdge] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MCTSResult(Generic[ActionT]):
    action: ActionT
    iterations: int
    root_visits: int
    action_visits: dict[str, int]


class GenericISMCTS(Generic[StateT, ActionT]):
    """Information-set UCT; rules, observations and rewards are adapter-owned.

    Each sampled root is a fully specified compatible determinization. Node
    keys are observer-relative information sets, not perfect-information
    hashes. An action invisible in one sample never gets selected in that
    sample. Opponent tree choices optimize the opponent's utility.
    """

    def __init__(
        self,
        game: SearchGame[StateT, ActionT],
        *,
        seed: int = 0,
        exploration: float = 1.4,
        tree_turn_depth: int = 6,
        rollout_actions: int = 32,
    ) -> None:
        if not math.isfinite(exploration) or exploration < 0:
            raise ValueError("exploration must be finite and nonnegative")
        if tree_turn_depth < 1 or rollout_actions < 0:
            raise ValueError("invalid search horizon")
        self.game = game
        self.rng = random.Random(seed)
        self.exploration = exploration
        self.tree_turn_depth = tree_turn_depth
        self.rollout_actions = rollout_actions
        self.nodes: dict[tuple[int, Hashable], MCTSNode] = {}

    def search(
        self,
        root_states: Sequence[StateT],
        *,
        iterations: int,
    ) -> MCTSResult[ActionT]:
        if not root_states or iterations <= 0:
            raise ValueError("roots and iterations must be nonempty")
        game = self.game
        player = game.active_player(root_states[0])
        root_info = game.information_set_id(root_states[0], player)
        for root in root_states:
            if game.is_terminal(root) or game.active_player(root) != player:
                raise ValueError("sampled roots must share a nonterminal actor")
            if game.information_set_id(root, player) != root_info:
                raise ValueError("sampled roots must share an information set")

        root_legal = list(game.legal_actions(root_states[0]))
        if not root_legal:
            raise ValueError("nonterminal root has no legal actions")
        root_actions = {game.action_id(action) for action in root_legal}
        if len(root_actions) != len(root_legal):
            raise ValueError("duplicate root action identifiers")
        # A legal decision cannot depend on information the actor cannot see.
        # Reject bad game adapters before joining incompatible belief samples
        # in one information-set node.
        for sample in root_states[1:]:
            available = list(game.legal_actions(sample))
            keys = {game.action_id(action) for action in available}
            if keys != root_actions or len(keys) != len(available):
                raise ValueError(
                    "belief samples sharing an information set must agree "
                    "on legal root actions"
                )
        root_key = (player, root_info)

        for index in range(iterations):
            state = game.copy_state(
                root_states[index % len(root_states)], None
            )
            path: list[tuple[MCTSNode, MCTSEdge, int]] = []
            completed_turns = 0
            # Bound raw actions as well: pending and multi-action turns need
            # not complete a strategic turn on every transition.
            for _ in range(self.tree_turn_depth * 32):
                if game.is_terminal(state):
                    break
                if completed_turns >= self.tree_turn_depth and game.frontier_ready(state):
                    break
                actor = game.active_player(state)
                actions = list(game.legal_actions(state))
                if not actions:
                    raise RuntimeError("nonterminal search node has no actions")
                node_key = (actor, game.information_set_id(state, actor))
                node = self.nodes.setdefault(node_key, MCTSNode())
                available = [(game.action_id(action), action) for action in actions]
                if len({key for key, _ in available}) != len(available):
                    raise ValueError("duplicate action identifiers in information set")
                unexplored = [(key, action) for key, action in available if key not in node.edges]
                expand = bool(unexplored)
                if unexplored:
                    key, action = self.rng.choice(unexplored)
                    edge = node.edges.setdefault(key, MCTSEdge())
                else:
                    def uct(item: tuple[str, ActionT]) -> float:
                        edge = node.edges[item[0]]
                        if edge.visits == 0:
                            return math.inf
                        return (
                            edge.value_sum / edge.visits
                            + self.exploration
                            * math.sqrt(math.log(node.visits + 1) / edge.visits)
                        )
                    key, action = max(available, key=uct)
                    edge = node.edges[key]
                child = game.copy_state(state, None)
                game.apply(child, action)
                completed_turns += int(game.completed_turn(state, child, action))
                path.append((node, edge, actor))
                state = child
                if expand:
                    break

            for _ in range(self.rollout_actions):
                if game.is_terminal(state):
                    break
                if completed_turns >= self.tree_turn_depth and game.frontier_ready(state):
                    break
                actions = game.legal_actions(state)
                if not actions:
                    raise RuntimeError("nonterminal rollout has no legal actions")
                action = self.rng.choice(actions)
                child = game.copy_state(state, None)
                game.apply(child, action)
                completed_turns += int(game.completed_turn(state, child, action))
                state = child

            # Leaf evaluation is in the player-specific utility scale. The
            # adapter owns terminal rewards; arbitrary heuristic scale is okay
            # as long as it is consistent for the two players.
            for node, edge, actor in path:
                utility = (
                    game.terminal_utility(state, actor)
                    if game.is_terminal(state)
                    else game.evaluate(state, actor)
                )
                edge.visits += 1
                edge.value_sum += utility
                node.visits += 1

        root_node = self.nodes.get(root_key)
        if root_node is None:
            raise RuntimeError("root was never expanded")
        ranked = [
            (root_node.edges.get(game.action_id(action), MCTSEdge()).visits, action)
            for action in root_legal
        ]
        best_visits, action = max(ranked, key=lambda item: item[0])
        return MCTSResult(
            action=action,
            iterations=iterations,
            root_visits=root_node.visits,
            action_visits={key: edge.visits for key, edge in root_node.edges.items()},
        )
