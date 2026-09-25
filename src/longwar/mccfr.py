from __future__ import annotations

import hashlib
import json
import math
import random
from collections import Counter
from dataclasses import dataclass
from typing import Any, Callable

from .agents.heuristic_agent import HeuristicAgent
from .game.actions import Action, action_key
from .game.engine import GameEngine, all_positions
from .game.model import Front, GameState, Phase
from .mccfr_core import (
    BACKEND,
    CFRNode,
    external_sampling_traverse,
)

try:
    from ._fast_search import (
        FastCFRNode as PrimitiveCFRNode,
        FastEngine as PrimitiveFastEngine,
        NativeHeuristicEvaluator as PrimitiveHeuristicEvaluator,
        make_scratch as make_primitive_scratch,
        packed_external_sampling_traverse,
        stable_information_id_from_fast_key,
    )
except ImportError:
    PrimitiveCFRNode = None
    PrimitiveFastEngine = None
    PrimitiveHeuristicEvaluator = None
    make_primitive_scratch = None
    packed_external_sampling_traverse = None
    stable_information_id_from_fast_key = None


def _counter_view(cards: list[str]) -> list[list[Any]]:
    return [[card_id, count] for card_id, count in sorted(Counter(cards).items())]


def information_set_key(state: GameState, player: int) -> dict[str, Any]:
    """Canonical public/private observation used by imperfect-information AI."""
    opponent = 1 - player

    board: list[list[Any]] = [[], []]
    for owner in range(2):
        for position in all_positions():
            slot = state.slot(owner, position)
            board[owner].append(
                [
                    int(position.front),
                    position.rank.value,
                    slot.force,
                    slot.bond,
                    slot.name,
                    slot.temporary_strength,
                ]
            )

    stories = [
        [story.card_id for story in state.stories[owner]]
        for owner in range(2)
    ]
    stratagems = [
        None if state.stratagems[owner] is None else state.stratagems[owner].card_id
        for owner in range(2)
    ]

    return {
        "viewer": player,
        "phase": state.phase.value,
        "battle": state.battle,
        "active_player": state.active_player,
        "passed": [
            state.players[0].passed,
            state.players[1].passed,
        ],
        "pass_order": list(state.pass_order),
        "discarded_this_battle": list(state.discarded_this_battle),
        "command": [
            state.players[0].command,
            state.players[1].command,
        ],
        "operations_this_battle": list(state.operations_this_battle),
        "pending_draw_discard_for": state.pending_draw_discard_for,
        "board": board,
        "stories": stories,
        "stratagems": stratagems,
        "stratagem_used": list(state.stratagem_used),
        "hero_used": list(state.hero_used),
        "own_hand": _counter_view(state.players[player].hand),
        "own_deck": _counter_view(state.players[player].deck),
        "own_discard": list(state.players[player].discard),
        "opponent_hand_count": len(state.players[opponent].hand),
        "known_opponent_hand": _counter_view(
            state.known_hidden_cards(player, opponent, "hand")
        ),
        "opponent_deck_count": len(state.players[opponent].deck),
        "opponent_discard": list(state.players[opponent].discard),
    }

def _information_set_id_from_key(key: dict[str, Any]) -> str:
    payload = json.dumps(
        key,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _search_information_set_key(state: GameState, player: int) -> str:
    return information_set_id(state, player)


def information_set_id(state: GameState, player: int) -> str:
    return _information_set_id_from_key(information_set_key(state, player))


@dataclass(frozen=True)
class TrainingSummary:
    iterations: int
    traversals: int
    information_sets: int
    max_depth: int
    mean_sampled_utility_p0: float
    mean_sampled_utility_p1: float


class MCCFRTrainer:
    """Depth-limited external-sampling Monte Carlo CFR.

    Chance is sampled by shuffling/drawing a fresh complete state at the root
    of every iteration. On the traversing player's nodes every legal action is
    expanded; on the opponent's nodes one action is sampled from regret
    matching. This is the external-sampling MCCFR update. The explicit
    approximation is the depth limit: frontier states are evaluated by the
    public-information heuristic evaluator rather than recursively solving the
    rest of the match.
    """

    def __init__(
        self,
        engine: GameEngine,
        deck_a: list[str] | None,
        deck_b: list[str] | None,
        *,
        seed: int = 1701,
        max_depth: int = 3,
        leaf_scale: float = 100.0,
        direct_traversal: bool = True,
    ):
        if not math.isfinite(leaf_scale) or leaf_scale <= 0:
            raise ValueError("leaf_scale must be finite and positive")
        if max_depth < 1:
            raise ValueError("max_depth must be at least 1")
        self.engine = engine
        self.deck_a = list(deck_a) if deck_a is not None else None
        self.deck_b = list(deck_b) if deck_b is not None else None
        if self.deck_a is not None:
            self.engine.validate_deck(self.deck_a)
        if self.deck_b is not None:
            self.engine.validate_deck(self.deck_b)
        self.rng = random.Random(seed)
        self.chance_rng = random.Random(seed ^ 0x5F3759DF)
        self.seed = seed
        self.max_depth = max_depth
        self.leaf_scale = leaf_scale
        self.direct_traversal = direct_traversal
        self.nodes: dict[str, CFRNode] = {}
        self._primitive_nodes: dict[bytes, Any] = {}
        self._primitive_engine = (
            PrimitiveFastEngine(engine)
            if (
                direct_traversal
                and PrimitiveFastEngine is not None
                and PrimitiveCFRNode is not None
                and packed_external_sampling_traverse is not None
            )
            else None
        )
        self._primitive_evaluator = (
            PrimitiveHeuristicEvaluator(self._primitive_engine)
            if (
                self._primitive_engine is not None
                and PrimitiveHeuristicEvaluator is not None
            )
            else None
        )
        self._primitive_scratch = (
            make_primitive_scratch(max_depth)
            if (
                self._primitive_engine is not None
                and make_primitive_scratch is not None
            )
            else None
        )
        self._used_primitive_training = False
        self.iterations = 0
        self._leaf_agent = HeuristicAgent(seed=seed, exploration=0.0)

    def train(self, iterations: int) -> TrainingSummary:
        if iterations <= 0:
            raise ValueError("iterations must be positive")
        if self.deck_a is None or self.deck_b is None:
            raise ValueError("Root-deal training requires both concrete decklists")

        utility_sum = [0.0, 0.0]
        for _ in range(iterations):
            root = self.engine._new_game_with_rng(
                self.deck_a,
                self.deck_b,
                rng=self.chance_rng,
                first_player=self.chance_rng.randrange(2),
            )
            if self._primitive_engine is not None:
                fast_root = self._primitive_engine.from_game_state(root)
                for traverser in (0, 1):
                    utility_sum[traverser] += packed_external_sampling_traverse(
                        self._primitive_engine,
                        fast_root,
                        traverser,
                        depth=0,
                        max_depth=self.max_depth,
                        nodes=self._primitive_nodes,
                        rng=self.rng,
                        leaf_scale=self.leaf_scale,
                        scratch=self._primitive_scratch,
                        evaluator=self._primitive_evaluator,
                    )
                self._used_primitive_training = True
            else:
                for traverser in (0, 1):
                    utility_sum[traverser] += self._traverse(
                        root,
                        traverser,
                        depth=0,
                    )
            self.iterations += 1

        return TrainingSummary(
            iterations=self.iterations,
            traversals=self.iterations * 2,
            information_sets=(
                len(self._primitive_nodes)
                if self._used_primitive_training
                else len(self.nodes)
            ),
            max_depth=self.max_depth,
            mean_sampled_utility_p0=utility_sum[0] / iterations,
            mean_sampled_utility_p1=utility_sum[1] / iterations,
        )

    def train_from_state(
        self,
        root: GameState,
        iterations: int,
    ) -> TrainingSummary:
        """Train repeatedly from one fully specified state.

        This is useful for deterministic algorithm tests and is also the
        primitive needed for future online re-solving. Both players are used
        as traverser on every iteration, exactly as in root-deal training.
        """
        if iterations <= 0:
            raise ValueError("iterations must be positive")
        if root.phase is Phase.COMPLETE:
            raise ValueError("Cannot train from a terminal state")

        utility_sum = [0.0, 0.0]
        for _ in range(iterations):
            for traverser in (0, 1):
                utility_sum[traverser] += self._traverse(
                    root,
                    traverser,
                    depth=0,
                )
            self.iterations += 1

        return TrainingSummary(
            iterations=self.iterations,
            traversals=self.iterations * 2,
            information_sets=len(self.nodes),
            max_depth=self.max_depth,
            mean_sampled_utility_p0=utility_sum[0] / iterations,
            mean_sampled_utility_p1=utility_sum[1] / iterations,
        )

    def train_from_sampler(
        self,
        root_sampler: Callable[[], GameState],
        iterations: int,
    ) -> TrainingSummary:
        """Train from a freshly sampled compatible root each iteration.

        This is the online re-solving primitive: all sampled determinizations
        may differ in hidden information while sharing the acting player's
        root information set.
        """
        if iterations <= 0:
            raise ValueError("iterations must be positive")

        utility_sum = [0.0, 0.0]
        for _ in range(iterations):
            root = root_sampler()
            if root.phase is Phase.COMPLETE:
                raise ValueError("Root sampler returned a terminal state")
            for traverser in (0, 1):
                utility_sum[traverser] += self._traverse(
                    root,
                    traverser,
                    depth=0,
                )
            self.iterations += 1

        return TrainingSummary(
            iterations=self.iterations,
            traversals=self.iterations * 2,
            information_sets=len(self.nodes),
            max_depth=self.max_depth,
            mean_sampled_utility_p0=utility_sum[0] / iterations,
            mean_sampled_utility_p1=utility_sum[1] / iterations,
        )

    def _search_child(
        self,
        current: GameState,
        action: Action,
        child_depth: int,
        scratch_by_depth: dict[int, GameState],
    ) -> GameState:
        child = scratch_by_depth.get(child_depth)
        if child is None:
            child = current.clone()
            scratch_by_depth[child_depth] = child
        else:
            child.copy_from(current)
        self.engine.apply(child, action, validate=False)
        return child

    def _traverse(
        self,
        state: GameState,
        traverser: int,
        *,
        depth: int,
    ) -> float:
        # The object-state traversal remains the correctness/reference path.
        # Offline deck training uses the primitive-array engine instead.
        # Keeping this path generic avoids maintaining two independent native
        # traversals over the mutable Python GameState representation.
        return self._traverse_generic(
            state,
            traverser,
            depth=depth,
            scratch_by_depth={},
        )

    def _traverse_generic(
        self,
        state: GameState,
        traverser: int,
        *,
        depth: int,
        scratch_by_depth: dict[int, GameState],
    ) -> float:
        depth_by_state_id = {id(state): depth}

        def next_state(current: GameState, action: Action) -> GameState:
            child_depth = depth_by_state_id[id(current)] + 1
            child = self._search_child(
                current,
                action,
                child_depth,
                scratch_by_depth,
            )
            depth_by_state_id[id(child)] = child_depth
            return child

        return external_sampling_traverse(
            state,
            traverser,
            depth=depth,
            max_depth=self.max_depth,
            nodes=self.nodes,
            rng=self.rng,
            is_terminal=lambda current: current.phase is Phase.COMPLETE,
            terminal_utility=lambda current, player: (
                1.0 if current.winner == player else -1.0
            ),
            current_player=lambda current: current.active_player,
            legal_actions=self.engine.legal_actions,
            action_key=action_key,
            information_set_id=_search_information_set_key,
            next_state=next_state,
            leaf_value=self._leaf_value,
        )

    def _leaf_value(self, state: GameState, traverser: int) -> float:
        raw = self._leaf_agent.evaluate(self.engine, state, traverser)
        return math.tanh(raw / self.leaf_scale)

    def policy_payload(self) -> dict[str, Any]:
        infosets: dict[str, Any] = {}
        if self._used_primitive_training:
            if (
                self._primitive_engine is None
                or stable_information_id_from_fast_key is None
            ):
                raise RuntimeError("Primitive MCCFR export backend is unavailable")
            for internal_key, node in self._primitive_nodes.items():
                info_id = stable_information_id_from_fast_key(
                    self._primitive_engine,
                    internal_key,
                )
                raw_keys = sorted(node.regret_sum)
                serialized = {
                    key: self._primitive_engine.action_key(key)
                    for key in raw_keys
                }
                average = node.average_strategy(raw_keys)
                current = node.strategy(raw_keys)
                infosets[info_id] = {
                    "visits": node.visits,
                    "average_visits": node.average_visits,
                    "average_strategy": {
                        serialized[key]: average[key]
                        for key in raw_keys
                    },
                    "current_strategy": {
                        serialized[key]: current[key]
                        for key in raw_keys
                    },
                    "regret_sum": {
                        serialized[key]: node.regret_sum[key]
                        for key in raw_keys
                    },
                    "strategy_sum": {
                        serialized[key]: node.strategy_sum.get(key, 0.0)
                        for key in raw_keys
                    },
                }
        else:
            for info_id, node in self.nodes.items():
                keys = sorted(node.regret_sum)
                infosets[info_id] = {
                    "visits": node.visits,
                    "average_visits": node.average_visits,
                    "average_strategy": node.average_strategy(keys),
                    "current_strategy": node.strategy(keys),
                    "regret_sum": {key: node.regret_sum[key] for key in keys},
                    "strategy_sum": {
                        key: node.strategy_sum.get(key, 0.0)
                        for key in keys
                    },
                }

        return {
            "schema_version": 1,
            "algorithm": "depth_limited_external_sampling_mccfr",
            "execution_backend": BACKEND,
            "traversal_backend": (
                "primitive_array_cython"
                if self._used_primitive_training
                else "generic_external_sampling"
            ),
            "iterations": self.iterations,
            "traversals": self.iterations * 2,
            "max_depth": self.max_depth,
            "leaf_evaluator": {
                "type": "heuristic_state_value",
                "transform": "tanh(value / leaf_scale)",
                "leaf_scale": self.leaf_scale,
            },
            "chance_sampling": "fresh root shuffle/draw and starting player per iteration",
            "mulligan_policy": "no mulligan during MCCFR root sampling",
            "information_abstraction": {
                "includes": [
                    "public battlefield and discard state",
                    "own hand identities",
                    "own remaining deck multiset",
                    "public hand/deck counts",
                    "own hidden Scheme identity",
                ],
                "excludes": [
                    "opponent hand identities",
                    "both deck orders",
                    "opponent unrevealed Scheme identity",
                    "full action history",
                ],
                "note": "This is an imperfect-recall state abstraction, not an exact perfect-recall game tree.",
            },
            "average_policy": "sampling-corrected external-sampling average strategy",
            "infosets": infosets,
        }
